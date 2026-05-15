from datetime import datetime, timedelta
from models import PsychologyLog
from database import SessionLocal

class PsychologyEngine:
    def __init__(self, user_id=None):
        self.user_id = user_id
        self.db = SessionLocal()

    def analyze_behavior(self, recent_trades):
        """
        recent_trades: list of objects with {result: 'Win'/'Loss', timestamp: datetime, volume: float}
        """
        issues = []
        
        # 1. Excessive Trading (3+ trades in an hour)
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        trades_this_hour = [t for t in recent_trades if t['timestamp'] > hour_ago]
        if len(trades_this_hour) >= 3:
            issues.append("Excessive Trading: 3+ trades in the last hour.")

        # 2. Revenge Trading (Trade immediately after loss)
        if len(recent_trades) >= 2:
            last_trade = recent_trades[-1]
            prev_trade = recent_trades[-2]
            if prev_trade['result'] == 'Loss' and (last_trade['timestamp'] - prev_trade['timestamp']).total_seconds() < 300:
                issues.append("Revenge Trading: Rapid trade after a loss.")

        # 3. 3 Consecutive Losses
        if len(recent_trades) >= 3:
            last_3 = [t['result'] for t in recent_trades[-3:]]
            if last_3 == ['Loss', 'Loss', 'Loss']:
                issues.append("Risk Warning: 3 consecutive losses detected.")

        if issues:
            self._log_event("emotional_trading", "; ".join(issues))
            return {
                "alert": "You are trading emotionally. Take a break!",
                "lock_ui": True,
                "lock_duration": 7200, # 2 hours
                "reason": issues
            }
        
        return {"alert": None, "lock_ui": False}

    def _log_event(self, event_type, description):
        log = PsychologyLog(
            user_id=self.user_id,
            event_type=event_type,
            description=description
        )
        self.db.add(log)
        self.db.commit()
        self.db.close()
