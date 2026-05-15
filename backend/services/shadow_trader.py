from models import ShadowTrade
from database import SessionLocal
from datetime import datetime

class ShadowTrader:
    def __init__(self, user_id):
        self.user_id = user_id
        self.db = SessionLocal()

    def open_trade(self, market, entry_price, sl=None, tp=None):
        trade = ShadowTrade(
            user_id=self.user_id,
            market=market,
            entry_price=entry_price,
            stop_loss=sl,
            take_profit=tp,
            status="open"
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def close_trade(self, trade_id, exit_price):
        trade = self.db.query(ShadowTrade).filter(ShadowTrade.id == trade_id).first()
        if trade:
            trade.exit_price = exit_price
            trade.status = "closed"
            # Simple PnL calculation (assuming Buy for simplicity in mock)
            trade.pnl = (exit_price - trade.entry_price) * 100 # Mock multiplier
            self.db.commit()
            return trade
        return None

    def get_history(self):
        return self.db.query(ShadowTrade).filter(ShadowTrade.user_id == self.user_id).all()
