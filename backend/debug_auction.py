import traceback
import sys
from pathlib import Path
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parent))
sys.path.insert(0, str(root))

from backend.services.data_adapter import DataAdapter
from backend.strategies.auction_market_theory import AuctionMarketStrategy

if __name__ == '__main__':
    da = DataAdapter()
    unified = da.normalize_input([], 'XAUUSD')
    chart_data = unified['chart_data']
    strat = AuctionMarketStrategy()
    try:
        res = strat.analyze(chart_data)
        print('RESULT:', res)
    except Exception as e:
        print('EXC:', type(e).__name__, e)
        traceback.print_exc()
