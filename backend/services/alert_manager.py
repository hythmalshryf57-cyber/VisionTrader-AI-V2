from database import SessionLocal
import models

def create_alert(user_id, market, recommendation, confidence, entry, sl, tp, top_strategies=""):
    db = SessionLocal()
    try:
        new_alert = models.Alert(
            user_id=user_id,
            market=market,
            recommendation=recommendation,
            confidence=confidence,
            entry=entry,
            sl=sl,
            tp=tp,
            top_strategies=top_strategies
        )
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        return new_alert
    finally:
        db.close()

def get_alerts(user_id, limit=20):
    db = SessionLocal()
    try:
        return db.query(models.Alert).filter(models.Alert.user_id == user_id).order_by(models.Alert.created_at.desc()).limit(limit).all()
    finally:
        db.close()
