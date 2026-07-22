import importlib
import inspect
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / 'backend'
STRATEGIES_DIR = BACKEND_ROOT / 'strategies'

sys.path.insert(0, str(ROOT))

DUMMY_CHART_DATA = {
    'opens': [1.0, 1.1, 1.05, 1.08, 1.12],
    'highs': [1.12, 1.15, 1.1, 1.11, 1.13],
    'lows': [0.98, 1.0, 1.02, 1.01, 1.05],
    'closes': [1.05, 1.12, 1.08, 1.1, 1.11],
    'volumes': [100, 120, 110, 90, 105],
    'timestamps': ['2026-01-01T00:00:00Z'] * 5,
    'support_levels': [1.0, 1.02],
    'resistance_levels': [1.1, 1.12],
    'liquidity_levels': [1.1, 1.12, 1.14],
}

DUMMY_NUMERIC_DATA = {
    'opens': [1.0, 1.1, 1.05, 1.08, 1.12],
    'highs': [1.12, 1.15, 1.1, 1.11, 1.13],
    'lows': [0.98, 1.0, 1.02, 1.01, 1.05],
    'closes': [1.05, 1.12, 1.08, 1.1, 1.11],
    'volumes': [100, 120, 110, 90, 105],
}

DEFAULT_KWARGS = {
    'chart_data': DUMMY_CHART_DATA,
    'closes': DUMMY_NUMERIC_DATA['closes'],
    'highs': DUMMY_NUMERIC_DATA['highs'],
    'lows': DUMMY_NUMERIC_DATA['lows'],
    'opens': DUMMY_NUMERIC_DATA['opens'],
    'volumes': DUMMY_NUMERIC_DATA['volumes'],
    'times': [None] * 5,
    'timeseries': [None] * 5,
    'price_history': [
        {'open': o, 'high': h, 'low': l, 'close': c}
        for o, h, l, c in zip(DUMMY_NUMERIC_DATA['opens'], DUMMY_NUMERIC_DATA['highs'], DUMMY_NUMERIC_DATA['lows'], DUMMY_NUMERIC_DATA['closes'])
    ],
    'market': 'XAUUSD',
    'symbol': 'XAUUSD',
    'current_price': 1.11,
    'intermarket_data': {},
    'pair_data': {},
    'order_blocks': [],
    'bars': [],
    'swings': [],
    'feature_vector': None,
    'cot_data_list': [],
    'regime_history': [],
    'transitions': [],
    'chart_data_dict': DUMMY_CHART_DATA,
}

REPORT = []


def safe_instantiate(cls):
    try:
        sig = inspect.signature(cls)
        kwargs = {}
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if name in DEFAULT_KWARGS:
                kwargs[name] = DEFAULT_KWARGS[name]
            elif param.default is not inspect.Parameter.empty:
                kwargs[name] = param.default
            else:
                # try sensible numeric/default value
                kwargs[name] = 0 if param.annotation in (int, float) else None
        return cls(**kwargs)
    except Exception:
        try:
            return cls()
        except Exception:
            raise


def attempt_analyze(instance):
    if not hasattr(instance, 'analyze'):
        return 'no_analyze'

    anal = getattr(instance, 'analyze')
    if not callable(anal):
        return 'no_analyze'

    sig = inspect.signature(anal)
    kwargs = {}
    args = []
    for name, param in sig.parameters.items():
        if name == 'self':
            continue
        if name in DEFAULT_KWARGS:
            kwargs[name] = DEFAULT_KWARGS[name]
        elif param.kind == inspect.Parameter.VAR_POSITIONAL:
            continue
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        elif param.default is not inspect.Parameter.empty:
            kwargs[name] = param.default
        else:
            # safe fallback values for common names
            if name in ('length', 'period', 'window', 'indicator_period'):  # heuristic
                kwargs[name] = 5
            elif name in ('direction', 'recommendation', 'trend'):
                kwargs[name] = 'شراء'
            elif name in ('price', 'entry_price', 'current_price'):
                kwargs[name] = 1.11
            elif name in ('market', 'symbol'):
                kwargs[name] = 'XAUUSD'
            else:
                kwargs[name] = None

    try:
        anal(**kwargs)
        return 'ok'
    except TypeError:
        try:
            anal(*args)
            return 'ok'
        except Exception as exc:
            return f'analysis_failed: {type(exc).__name__}: {exc}'
    except Exception as exc:
        return f'analysis_failed: {type(exc).__name__}: {exc}'


def main():
    strategy_files = sorted([p for p in STRATEGIES_DIR.glob('*.py') if p.name != '__init__.py'])
    for path in strategy_files:
        module_name = f'backend.strategies.{path.stem}'
        result = {'module': module_name, 'import': None, 'classes': []}
        try:
            module = importlib.import_module(module_name)
            result['import'] = 'ok'
        except Exception as exc:
            result['import'] = f'failed: {type(exc).__name__}: {exc}'
            result['traceback'] = traceback.format_exc()
            REPORT.append(result)
            continue

        classes = []
        for name, member in inspect.getmembers(module, inspect.isclass):
            if member.__module__ != module.__name__:
                continue
            if name.endswith('Strategy'):
                classes.append((name, member))
        if not classes:
            classes = []

        for class_name, cls in classes:
            class_result = {'class': class_name, 'instantiate': None, 'analyze': None}
            try:
                instance = safe_instantiate(cls)
                class_result['instantiate'] = 'ok'
            except Exception as exc:
                class_result['instantiate'] = f'failed: {type(exc).__name__}: {exc}'
                class_result['traceback'] = traceback.format_exc()
                result['classes'].append(class_result)
                continue

            analyze_result = attempt_analyze(instance)
            class_result['analyze'] = analyze_result
            result['classes'].append(class_result)

        REPORT.append(result)

    failures = [r for r in REPORT if r['import'] != 'ok' or any(c['instantiate'] != 'ok' or c['analyze'] not in ('ok', 'no_analyze') for c in r['classes'])]

    print('STRATEGY IMPORT & RUN REPORT')
    print('====================================')
    print(f'Total strategy files scanned: {len(strategy_files)}')
    print(f'Failures found: {len(failures)}')
    print()

    for r in REPORT:
        if r['import'] != 'ok' or any(c['instantiate'] != 'ok' or c['analyze'] not in ('ok', 'no_analyze') for c in r['classes']):
            print(f"MODULE: {r['module']}")
            print(f"  import: {r['import']}")
            if 'traceback' in r:
                print(f"  traceback:\n{r['traceback']}")
            for c in r['classes']:
                if c['instantiate'] != 'ok' or c['analyze'] not in ('ok', 'no_analyze'):
                    print(f"  CLASS: {c['class']}")
                    print(f"    instantiate: {c['instantiate']}")
                    print(f"    analyze: {c['analyze']}")
                    if 'traceback' in c:
                        print(f"    traceback:\n{c['traceback']}")
            print()

    if not failures:
        print('RESULT: All strategy files imported and runnable with the quick validation flow.')
        sys.exit(0)
    else:
        print('RESULT: Some strategies failed import/run. See details above.')
        sys.exit(1)


if __name__ == '__main__':
    main()
