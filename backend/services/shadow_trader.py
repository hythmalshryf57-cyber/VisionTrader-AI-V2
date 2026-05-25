from models import ShadowTrade
from database import SessionLocal
from datetime import datetime
import json
from pathlib import Path

# optional payload store for full recommendation data keyed by shadow trade id
_PAYLOAD_FILE = Path(__file__).resolve().parent.parent / 'shadow_recommendation_payloads.json'

def _load_payloads():
    try:
        if _PAYLOAD_FILE.exists():
            with open(_PAYLOAD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_payloads(payloads: dict):
    try:
        with open(_PAYLOAD_FILE, 'w', encoding='utf-8') as f:
            json.dump(payloads, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass

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

    def create_shadow_recommendation(self, recommendation: dict):
        # create a DB row marked as 'shadow' in status, then store full payload in file
        trade = ShadowTrade(
            user_id=self.user_id,
            market=recommendation.get('market'),
            entry_price=float(recommendation.get('entry_price') or recommendation.get('price') or 0.0),
            stop_loss=recommendation.get('stop_loss'),
            take_profit=recommendation.get('take_profit'),
            status='shadow',
            created_at=datetime.utcnow()
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        # persist full payload keyed by trade id
        payloads = _load_payloads()
        payloads[str(trade.id)] = recommendation
        _save_payloads(payloads)
        return trade

    def track_shadow_performance(self):
        # compute simple performance using stored payloads if available
        payloads = _load_payloads()
        shadows = self.db.query(ShadowTrade).filter(ShadowTrade.user_id == self.user_id, ShadowTrade.status == 'shadow').all()
        updated = []
        for s in shadows:
            rec = payloads.get(str(s.id))
            if not rec:
                continue
            price_history = rec.get('price_history') or []
            direction = str(rec.get('direction','')).lower()
            entry = s.entry_price or (price_history[0] if price_history else None)
            if entry is None:
                continue
            if price_history and len(price_history) > 1:
                last = float(price_history[-1])
                pnl = (entry - last) if direction in ('sell','short') else (last - entry)
                s.pnl = float(pnl)
                s.exit_price = last
                s.status = 'closed'
                self.db.commit()
                updated.append(s.id)
        return updated

    def get_shadow_stats(self):
        rows = self.db.query(ShadowTrade).filter(ShadowTrade.user_id == self.user_id).all()
        total = len(rows)
        closed = [r for r in rows if r.status == 'closed']
        wins = [r for r in closed if r.pnl and r.pnl > 0]
        losses = [r for r in closed if r.pnl and r.pnl <= 0]
        return {
            'total': total,
            'closed': len(closed),
            'wins_count': len(wins),
            'wins_avg': round(sum(r.pnl for r in wins)/max(1,len(wins)),6) if wins else 0.0,
            'losses_count': len(losses),
            'losses_avg': round(sum(r.pnl for r in losses)/max(1,len(losses)),6) if losses else 0.0,
            'examples': [
                {'id': r.id, 'market': r.market, 'entry_price': r.entry_price, 'exit_price': r.exit_price, 'status': r.status, 'pnl': r.pnl, 'created_at': r.created_at}
                for r in rows[-10:]
            ]
        }
