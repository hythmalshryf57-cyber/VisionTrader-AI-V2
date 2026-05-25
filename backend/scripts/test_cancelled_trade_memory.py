import sys, os
from datetime import datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.cancelled_trade_memory import CancelledTradeMemory, cancelled_trade_memory
from services.internal_brain import InternalBrain

def make_rec(market, direction, entry, price_hist=None):
    return {
        'market': market,
        'direction': direction,
        'entry_price': entry,
        'price_history': price_hist
    }

if __name__ == '__main__':
    mem = CancelledTradeMemory()

    # Record a few cancellations
    mem.record_cancellation(make_rec('EURUSD','buy',1.1000,[1.1000,1.1010,1.1025,1.1030]), 'user_rejected')
    mem.record_cancellation(make_rec('EURUSD','buy',1.2000,[1.2000,1.1980,1.1970,1.1950]), 'news_surprise')
    mem.record_cancellation(make_rec('GBPUSD','sell',1.3000,[1.3000,1.2990,1.2950,1.2900]), 'liquidity_change')

    print('Learning summary:')
    print(mem.get_learning_summary())

    print('\nMissed opportunities:')
    print(mem.analyze_missed_opportunities())

    print('\nNarrow escapes:')
    print(mem.analyze_narrow_escapes(loss_threshold=0.002))

    # Test adjust
    new_rec = make_rec('EURUSD','buy',1.1500,[1.1500,1.1510,1.1520])
    adjusted = mem.adjust_future_recommendation(new_rec)
    print('\nAdjusted recommendation:')
    print(adjusted)

    # test via InternalBrain attribute
    ib = InternalBrain()
    print('\nInternalBrain has cancelled memory:', hasattr(ib, 'cancelled_trade_memory'))
    if hasattr(ib, 'cancelled_trade_memory') and ib.cancelled_trade_memory:
        print('IB summary via attribute:', ib.cancelled_trade_memory.get_learning_summary())
