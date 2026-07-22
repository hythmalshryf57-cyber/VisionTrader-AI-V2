import sys
import traceback
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'backend'))
from backend.services.data_adapter import DataAdapter
from backend.strategies.wyckoff import WyckoffStrategy

try:
    da = DataAdapter()
    unified = da.normalize_input([], 'XAUUSD')
    chart_data = unified['chart_data']
    s = WyckoffStrategy()
    res = s.analyze(chart_data)
    print('RESULT:', res)
except Exception:
    traceback.print_exc()
