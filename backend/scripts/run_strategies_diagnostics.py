import sys, os, importlib, inspect, traceback, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.data_adapter import DataAdapter

market = 'XAUUSD'
da = DataAdapter()
unified = da.normalize_input([], market)
chart = unified['chart_data']
strategies_pkg = os.path.join(os.path.dirname(__file__), '..', 'strategies')
strategies_pkg = os.path.abspath(strategies_pkg)
modules = []
for root, dirs, files in os.walk(strategies_pkg):
    for fn in files:
        if not fn.endswith('.py') or fn == '__init__.py':
            continue
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, strategies_pkg)
        mod = rel.replace(os.path.sep, '.')[:-3]
        modules.append(mod)

summary = {'discovered': len(modules), 'executed':0, 'failed':0, 'excluded':0, 'buy':0, 'sell':0, 'hold':0}
details = {'per_cluster': {}, 'entries': []}

for mod in modules:
    module_obj = None
    for base in ('strategies.'+mod, 'backend.strategies.'+mod):
        try:
            module_obj = importlib.import_module(base)
            break
        except Exception as e:
            module_obj = None
            continue
    if not module_obj:
        details['entries'].append({'module': mod, 'status': 'import_failed'})
        summary['failed'] += 1
        continue
    classes = [c for name,c in inspect.getmembers(module_obj, inspect.isclass) if c.__module__==module_obj.__name__]
    if not classes:
        details['entries'].append({'module': mod, 'status': 'no_classes'})
        continue
    for cls in classes:
        name = cls.__name__
        if not name.lower().endswith('strategy'):
            continue
        entry = {'module': mod, 'strategy': name}
        try:
            strat = cls()
        except Exception as e:
            entry.update({'status':'instantiate_failed','error': str(e)})
            details['entries'].append(entry)
            summary['failed'] += 1
            continue
        # applicability
        m = market.upper()
        is_crypto = any(suf in m for suf in ('USDT','BTC','ETH','BNB','SOL','ADA'))
        is_forex = any(sym in m for sym in ('USD','EUR','GBP','JPY','AUD','CAD','CHF')) and not is_crypto
        applicable = True
        try:
            if getattr(strat, 'crypto_only', False) and not is_crypto:
                applicable = False
            if getattr(strat, 'forex_only', False) and not is_forex:
                applicable = False
        except Exception:
            applicable = True
        if not applicable:
            entry.update({'status':'excluded','reason':'market_mismatch'})
            details['entries'].append(entry)
            summary['excluded'] += 1
            continue
        # execute
        try:
            sig = inspect.signature(strat.analyze)
            if len(sig.parameters) == 1:
                res = strat.analyze(chart)
            else:
                try:
                    res = strat.analyze(**chart)
                except Exception:
                    res = strat.analyze(chart)
            vote = res.get('recommendation') or res.get('direction') or res.get('signal') or res.get('vote')
            conf = res.get('confidence', res.get('score', 0))
            try:
                conf = int(conf)
            except Exception:
                conf = 0
            entry.update({'status':'executed','vote':vote,'confidence':conf})
            if vote in ('شراء','buy'):
                summary['buy'] += 1
            elif vote in ('بيع','sell'):
                summary['sell'] += 1
            else:
                summary['hold'] += 1
            summary['executed'] += 1
            details['entries'].append(entry)
        except Exception as e:
            entry.update({'status':'failed','error': traceback.format_exc()})
            details['entries'].append(entry)
            summary['failed'] += 1

# rudimentary cluster grouping by keywords in strategy name
clusters = {'power':[], 'geometric':[], 'momentum':[]}
for e in details['entries']:
    nm = e.get('strategy') or e.get('module')
    if not nm:
        continue
    n = nm.lower()
    if any(k in n for k in ('smc','whale','order_flow','vpin','liquidation','order','tape')):
        clusters['power'].append(nm)
    elif any(k in n for k in ('fibonacci','fib','harmonic','elliott','profile','support','resistance','market_profile')):
        clusters['geometric'].append(nm)
    else:
        clusters['momentum'].append(nm)

output = {'summary': summary, 'clusters_estimate': {k: len(v) for k,v in clusters.items()}, 'details_sample': details['entries'][:200]}
print(json.dumps(output, ensure_ascii=False, indent=2))
