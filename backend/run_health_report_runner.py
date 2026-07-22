import json
from pathlib import Path
from tmp_strategy_health_report import create_strategy_report

root = Path(__file__).resolve().parent.parent
out_path = root / 'health_report_xauusd.json'

report = create_strategy_report('XAUUSD')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(out_path)
