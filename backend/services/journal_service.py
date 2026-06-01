from database import SessionLocal
import models
import datetime

class JournalService:
    def add_entry(self, user_id, market, recommendation, result, profit_loss, notes=None, mood_before=None, mood_after=None, confidence=None):
        db = SessionLocal()
        try:
            entry = models.JournalEntry(
                user_id=user_id,
                market=market,
                recommendation=recommendation,
                result=result,
                profit_loss=profit_loss,
                confidence=confidence,
                notes=notes,
                mood=f"{mood_before} -> {mood_after}" # Combined for now
            )
            db.add(entry)
            db.commit()
            db.refresh(entry)
            try:
                from services.internal_brain import InternalBrain
                InternalBrain().log_event_experience(
                    component="journal",
                    event_type="journal_entry",
                    event_key=market,
                    event_value=float(profit_loss or 0.0),
                    metadata={"result": result},
                    success=(str(result or "").lower() == "win")
                )
            except Exception:
                pass
            return entry
        finally:
            db.close()

    def generate_psych_report(self, user_id):
        db = SessionLocal()
        try:
            entries = db.query(models.JournalEntry).filter(models.JournalEntry.user_id == user_id).all()
            if not entries:
                return "No data for analysis."
            
            # Simplified analysis
            fear_trades = [e for e in entries if "خائف" in (e.mood or "")]
            if fear_trades:
                fear_losses = len([e for e in fear_trades if e.result.lower() == "loss"])
                fear_rate = (fear_losses / len(fear_trades)) * 100
                if fear_rate > 50:
                    return f"You lose {fear_rate:.0f}% of your trades when you feel afraid. I recommend taking a break when feeling this way."
            
            return "Your psychology seems balanced. Keep following your plan."
        finally:
            db.close()
    def get_entries(self, user_id):
        db = SessionLocal()
        try:
            return db.query(models.JournalEntry).filter(models.JournalEntry.user_id == user_id).order_by(models.JournalEntry.date.desc()).all()
        finally:
            db.close()

    def get_performance_stats(self, user_id):
        db = SessionLocal()
        try:
            entries = db.query(models.JournalEntry).filter(models.JournalEntry.user_id == user_id).all()
            if not entries:
                return {"win_rate": 0, "total_pnl": 0}
            
            wins = len([e for e in entries if e.result.lower() == "win"])
            total = len(entries)
            total_pnl = sum([e.profit_loss for e in entries])
            
            return {
                "win_rate": (wins / total) * 100,
                "total_pnl": total_pnl,
                "total_trades": total
            }
        finally:
            db.close()

journal_service = JournalService()
