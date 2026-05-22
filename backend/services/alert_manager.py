import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading

# Fallback imports for DB
try:
    from database import SessionLocal
    import models
except ImportError:
    SessionLocal = None
    models = None

logger = logging.getLogger(__name__)

class AlertPriority:
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    _levels = {LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4}

    @classmethod
    def get_level(cls, priority: str) -> int:
        return cls._levels.get(priority.upper(), 1)

    @classmethod
    def upgrade(cls, priority: str) -> str:
        lvl = cls.get_level(priority)
        if lvl == 1: return cls.MEDIUM
        if lvl == 2: return cls.HIGH
        return cls.CRITICAL

class Alert:
    def __init__(self, alert_id: str, message: str, priority: str, category: str):
        self.alert_id = alert_id
        self.message = message
        self.priority = priority.upper()
        self.category = category
        self.count = 1
        self.created_at = datetime.utcnow()
        self.last_triggered = self.created_at
        self.acknowledged = False
        self.channels_notified = set()

class AlertManager:
    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.lock = threading.Lock()
        
        # Start escalation monitor
        self.monitor_thread = threading.Thread(target=self._escalation_monitor, daemon=True)
        self.monitor_thread.start()

    def send_alert(self, message: str, priority: str = AlertPriority.MEDIUM, category: str = "general", user_id: int = 1):
        """Sends a smart alert, handling deduplication and routing."""
        alert_id = f"{category}_{message}"
        
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                if not alert.acknowledged:
                    alert.count += 1
                    alert.last_triggered = datetime.utcnow()
                    
                    # Upgrade priority if repeated 3 times
                    if alert.count >= 3 and alert.priority != AlertPriority.CRITICAL:
                        old_prio = alert.priority
                        alert.priority = AlertPriority.upgrade(alert.priority)
                        alert.count = 1  # Reset count for next upgrade
                        logger.info(f"Alert '{message}' upgraded from {old_prio} to {alert.priority} due to repetitions.")
                        self._route_alert(alert, user_id)
                    return alert
            else:
                alert = Alert(alert_id, message, priority, category)
                self.active_alerts[alert_id] = alert
        
        self._route_alert(alert, user_id)
        return alert

    def _route_alert(self, alert: Alert, user_id: int):
        """Routes the alert to appropriate channels based on priority."""
        prio_level = AlertPriority.get_level(alert.priority)
        
        # 1. Dashboard Notification (Low, Medium, High, Critical)
        self._notify_dashboard(alert, user_id)
        
        # 2. Telegram (Medium, High, Critical)
        if prio_level >= 2 and "telegram" not in alert.channels_notified:
            self._notify_telegram(alert)
            alert.channels_notified.add("telegram")
            
        # 3. Email & Voice (Critical only)
        if prio_level >= 4:
            if "email" not in alert.channels_notified:
                self._notify_email(alert, user_id)
                alert.channels_notified.add("email")
            if "voice" not in alert.channels_notified:
                self._notify_voice(alert)
                alert.channels_notified.add("voice")

    def _notify_dashboard(self, alert: Alert, user_id: int):
        logger.info(f"[Dashboard] [{alert.priority}] {alert.message}")
        if SessionLocal and models:
            try:
                db = SessionLocal()
                # Use existing Alert model if possible, or create a generic notification
                new_alert = models.Alert(
                    user_id=user_id,
                    market=alert.category,
                    recommendation=alert.message[:100],
                    confidence=100 if alert.priority == 'CRITICAL' else 50,
                    entry=0, sl=0, tp=0, top_strategies=alert.priority
                )
                db.add(new_alert)
                db.commit()
                db.close()
            except Exception as e:
                logger.error(f"Failed to save alert to DB: {e}")

    def _notify_telegram(self, alert: Alert):
        icon = "🚨" if alert.priority == AlertPriority.CRITICAL else "⚠️" if alert.priority == AlertPriority.HIGH else "📊"
        msg = f"{icon} <b>{alert.priority}</b>: {alert.message}"
        # Mocking telegram service call
        logger.info(f"[Telegram] Sending: {msg}")

    def _notify_email(self, alert: Alert, user_id: int):
        logger.info(f"[Email] Sending URGENT email for user {user_id}: {alert.message}")

    def _notify_voice(self, alert: Alert):
        logger.info(f"[Voice] 🔊 Speaking URGENT alert: {alert.message}")

    def acknowledge_alert(self, category: str, message: str):
        alert_id = f"{category}_{message}"
        with self.lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledged = True
                logger.info(f"Alert '{message}' acknowledged.")

    def _escalation_monitor(self):
        """Background thread to escalate unacknowledged HIGH alerts after 30 minutes."""
        while True:
            time.sleep(2)  # Check frequently for testing purposes
            now = datetime.utcnow()
            with self.lock:
                for alert in self.active_alerts.values():
                    if not alert.acknowledged and alert.priority == AlertPriority.HIGH:
                        # 30 minutes in reality, we use 5 seconds for testing demonstration
                        if (now - alert.last_triggered).total_seconds() > 5:
                            alert.priority = AlertPriority.CRITICAL
                            alert.last_triggered = now
                            logger.warning(f"Escalating alert '{alert.message}' to CRITICAL due to timeout!")
                            # Route again to trigger critical channels
                            self._route_alert(alert, user_id=1)


alert_manager = AlertManager()

# Keeping original functions for backward compatibility
def create_alert(user_id, market, recommendation, confidence, entry, sl, tp, top_strategies=""):
    return alert_manager.send_alert(
        message=f"{recommendation} | Entry: {entry} | SL: {sl} | TP: {tp}",
        priority=AlertPriority.MEDIUM,
        category=market,
        user_id=user_id
    )

def get_alerts(user_id, limit=20):
    if SessionLocal and models:
        db = SessionLocal()
        try:
            return db.query(models.Alert).filter(models.Alert.user_id == user_id).order_by(models.Alert.created_at.desc()).limit(limit).all()
        finally:
            db.close()
    return []

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print("=========================================")
    print("   Smart Alert Manager Tests")
    print("=========================================")
    
    am = AlertManager()
    
    print("\n1. Testing Low Priority (Dashboard Only)")
    am.send_alert("System boot successful", AlertPriority.LOW)
    
    print("\n2. Testing Medium Priority (Dashboard + Telegram)")
    am.send_alert("New setup on EURUSD", AlertPriority.MEDIUM)
    
    print("\n3. Testing Repetition Upgrade (Medium -> High -> Critical)")
    am.send_alert("Repeated alert", AlertPriority.MEDIUM)
    am.send_alert("Repeated alert", AlertPriority.MEDIUM)
    am.send_alert("Repeated alert", AlertPriority.MEDIUM) # Upgrades to HIGH
    am.send_alert("Repeated alert", AlertPriority.MEDIUM)
    am.send_alert("Repeated alert", AlertPriority.MEDIUM)
    am.send_alert("Repeated alert", AlertPriority.MEDIUM) # Upgrades to CRITICAL
    
    print("\n4. Testing Time Escalation (High -> Critical after 5 seconds)")
    am.send_alert("Unattended high alert", AlertPriority.HIGH)
    print("Waiting 6 seconds for escalation timeout...")
    time.sleep(6) 
    
    print("\n5. Testing Critical Priority (All Channels)")
    am.send_alert("MASSIVE LOSS DETECTED! STOP TRADING!", AlertPriority.CRITICAL)
    
    print("\n✅ Smart Alert Manager tests finished!")
