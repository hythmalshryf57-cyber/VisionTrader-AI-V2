import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'backend'))
from backend.services.voting_engine import strategy_loader

report_path = root / 'health_report_xauusd.json'
if not report_path.exists():
    print('NO_REPORT')
    sys.exit(1)

with open(report_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# map strategy_key -> (signal, confidence)
strategy_results = {}
for item in data.get('report', []):
    key = item['strategy_name']
    sig = item.get('signal')
    conf = item.get('confidence')
    strategy_results[key] = (sig, conf)

clusters = strategy_loader.get_cluster_assignments()
output = {}
for cluster_name, assignments in clusters.items():
    total = {'buy':0,'sell':0,'hold':0,'unknown':0}
    confs = []
    for entry in assignments:
        key = f"{entry['module']}.{entry['class_name']}"
        sig, conf = strategy_results.get(key, (None, None))
        if sig in ('شراء','buy'):
            total['buy'] += 1
        elif sig in ('بيع','sell'):
            total['sell'] += 1
        elif sig in ('محايد','hold','neutral'):
            total['hold'] += 1
        else:
            total['unknown'] += 1
        if isinstance(conf,(int,float)):
            confs.append(conf)
    avg_conf = sum(confs)/len(confs) if confs else 0
    # judge: buy if buy>sell*1.2, sell if sell>buy*1.2 else neutral
    judge = 'محايد'
    if total['buy'] > total['sell'] * 1.2 and total['buy']>total['sell']:
        judge = 'شراء'
    elif total['sell'] > total['buy'] * 1.2 and total['sell']>total['buy']:
        judge = 'بيع'
    output[cluster_name] = {
        'counts': total,
        'avg_confidence': round(avg_conf,1),
        'judge': judge,
    }

print(json.dumps(output, ensure_ascii=False, indent=2))
