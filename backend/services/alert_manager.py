import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import threading

# Fallback imports for DB
try:
    from database import SessionLocal
    import models
except ImportError:
    SessionLocal = None
    models = None

# InternalBrain integration
try:
    from .internal_brain import InternalBrain
    _brain = InternalBrain()
except Exception:
    _brain = None

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
        self.created_at = datetime.now(timezone.utc)
        self.last_triggered = self.created_at
        self.acknowledged = False
        self.channels_notified = set()

class AlertManager:
    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Dict] = []  # تاريخ التنبيهات للتعلم
        self.lock = threading.Lock()
        
        # عتبات ديناميكية قابلة للتعلم
        self._base_repetition_threshold = 3    # عدد التكرارات قبل الترقية
        self._base_escalation_timeout = 5      # ثوانٍ (30 دقيقة في الإنتاج)
        self._learn_thresholds_from_brain()
        
        # Start escalation monitor
        self.monitor_thread = threading.Thread(target=self._escalation_monitor, daemon=True)
        self.monitor_thread.start()
    
    def _learn_thresholds_from_brain(self):
        """تعلم العتبات الديناميكية من العقل المركزي"""
        if not _brain:
            return
        try:
            mem = _brain.get_component_memory("alert_manager")
            stats = mem.get("acknowledge_stats", {})
            
            total_sent = stats.get("total_sent", 0)
            total_acked = stats.get("total_acknowledged", 0)
            
            if total_sent < 5:
                return  # لم يتعلم بعد
            
            ack_rate = total_acked / total_sent
            
            # إذا المستخدم يعترف بسرعة -> تأخير التصعيد أكثر
            # إذا المستخدم يتجاهل -> تصعيد أسرع
            if ack_rate > 0.7:
                self._base_escalation_timeout = 8  # المستخدم منتبه، نعطيه وقت
                self._base_repetition_threshold = 4
            elif ack_rate < 0.3:
                self._base_escalation_timeout = 3  # المستخدم متجاهل، نصعّد بسرعة
                self._base_repetition_threshold = 2
            
            logger.info(
                f"🧠 [AlertManager] تعلم من العقل المركزي: "
                f"ack_rate={ack_rate:.1%}, "
                f"repetition_threshold={self._base_repetition_threshold}, "
                f"escalation_timeout={self._base_escalation_timeout}s"
            )
        except Exception as e:
            logger.warning(f"فشل تعلم عتبات التنبيهات: {e}")

    def send_alert(self, message: str, priority: str = AlertPriority.MEDIUM, category: str = "general", user_id: int = 1):
        """Sends a smart alert, handling deduplication, routing, and learning."""
        alert_id = f"{category}_{message}"
        
        # تعديل الأولوية بناءً على تعلم العقل المركزي
        adjusted_priority = self._adjust_priority_from_brain(priority, category, user_id)
        
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                if not alert.acknowledged:
                    alert.count += 1
                    alert.last_triggered = datetime.now(timezone.utc)
                    
                    # الترقية بناءً على العتبة الديناميكية (بدل 3 ثابتة)
                    if alert.count >= self._base_repetition_threshold and alert.priority != AlertPriority.CRITICAL:
                        old_prio = alert.priority
                        alert.priority = AlertPriority.upgrade(alert.priority)
                        alert.count = 1  # Reset count for next upgrade
                        logger.info(f"Alert '{message}' upgraded from {old_prio} to {alert.priority} (threshold={self._base_repetition_threshold}).")
                        self._route_alert(alert, user_id)
                    return alert
            else:
                alert = Alert(alert_id, message, adjusted_priority, category)
                self.active_alerts[alert_id] = alert
        
        # تسجيل التنبيه في العقل المركزي
        self._log_alert_to_brain(alert, user_id)
        
        self._route_alert(alert, user_id)
        return alert
    
    def _adjust_priority_from_brain(self, priority: str, category: str, user_id: int) -> str:
        """تعديل الأولوية بناءً على تفضيلات المستخدم المتعلّمة"""
        if not _brain:
            return priority
        try:
            adjustment = _brain.get_alert_priority_adjustment(user_id, category)
            current_level = AlertPriority.get_level(priority)
            
            if adjustment <= -2.0 and current_level > 1:
                # المستخدم لا يقرأ هذا النوع -> خفض الأولوية
                levels = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
                new_level = max(1, current_level - 1)
                new_priority = levels.get(new_level, priority)
                logger.info(f"🧠 خفض أولوية [{category}] من {priority} إلى {new_priority} (المستخدم يتجاهل)")
                return new_priority
            elif adjustment >= 1.0 and current_level < 4:
                levels = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}
                new_level = min(4, current_level + 1)
                new_priority = levels.get(new_level, priority)
                logger.info(f"🧠 رفع أولوية [{category}] من {priority} إلى {new_priority} (المستخدم يهتم)")
                return new_priority
        except Exception as e:
            logger.warning(f"فشل تعديل الأولوية من العقل: {e}")
        return priority
    
    def _log_alert_to_brain(self, alert: Alert, user_id: int):
        """تسجيل التنبيه في العقل المركزي والذاكرة"""
        if not _brain:
            return
        try:
            _brain.log_event_experience(
                component="alert_manager",
                event_type="alert_sent",
                event_key=alert.category,
                event_value=AlertPriority.get_level(alert.priority),
                metadata={"message": alert.message[:100], "priority": alert.priority},
                context=f"user_{user_id}",
                success=True,
            )
            # تحديث إحصائيات الإرسال
            mem = _brain.get_component_memory("alert_manager")
            stats = mem.setdefault("acknowledge_stats", {"total_sent": 0, "total_acknowledged": 0})
            stats["total_sent"] += 1
            _brain._save_component_memory("alert_manager", mem)
        except Exception as e:
            logger.warning(f"فشل تسجيل التنبيه في العقل: {e}")

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

    def acknowledge_alert(self, category: str, message: str, user_id: int = 1):
        alert_id = f"{category}_{message}"
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.acknowledged = True
                ack_time = (datetime.now(timezone.utc) - alert.created_at).total_seconds()
                logger.info(f"Alert '{message}' acknowledged in {ack_time:.1f}s.")
                
                # تسجيل الاعتراف في العقل المركزي
                if _brain:
                    try:
                        _brain.track_alert_response(
                            user_id=user_id,
                            alert_type=alert.category,
                            was_read=True,
                            was_acted_upon=True,
                        )
                        # تحديث إحصائيات الاعتراف
                        mem = _brain.get_component_memory("alert_manager")
                        stats = mem.setdefault("acknowledge_stats", {"total_sent": 0, "total_acknowledged": 0})
                        stats["total_acknowledged"] += 1
                        
                        # تسجيل سرعة الاعتراف
                        speeds = mem.setdefault("ack_speeds", [])
                        speeds.append({"category": category, "seconds": round(ack_time, 1), "ts": datetime.now(timezone.utc).isoformat()})
                        if len(speeds) > 100:
                            speeds[:] = speeds[-100:]
                        
                        _brain._save_component_memory("alert_manager", mem)
                        logger.info(f"🧠 تم تسجيل اعتراف التنبيه في العقل المركزي")
                    except Exception as e:
                        logger.warning(f"فشل تسجيل اعتراف التنبيه: {e}")

    def _escalation_monitor(self):
        """Background thread to escalate unacknowledged HIGH alerts - timeout learned from brain."""
        while True:
            time.sleep(2)  # Check frequently for testing purposes
            now = datetime.now(timezone.utc)
            with self.lock:
                for alert in self.active_alerts.values():
                    if not alert.acknowledged and alert.priority == AlertPriority.HIGH:
                        # العتبة الديناميكية بدل الثابتة
                        if (now - alert.last_triggered).total_seconds() > self._base_escalation_timeout:
                            alert.priority = AlertPriority.CRITICAL
                            alert.last_triggered = now
                            logger.warning(
                                f"⏰ Escalating '{alert.message}' to CRITICAL "
                                f"(timeout={self._base_escalation_timeout}s, learned from brain)"
                            )
                            # Route again to trigger critical channels
                            self._route_alert(alert, user_id=1)
    
    def get_learning_stats(self) -> Dict:
        """إحصائيات التعلم الحالية لمدير التنبيهات"""
        stats = {
            "repetition_threshold": self._base_repetition_threshold,
            "escalation_timeout_sec": self._base_escalation_timeout,
            "active_alerts": len(self.active_alerts),
            "brain_connected": _brain is not None,
        }
        if _brain:
            try:
                mem = _brain.get_component_memory("alert_manager")
                ack_stats = mem.get("acknowledge_stats", {})
                stats["total_sent"] = ack_stats.get("total_sent", 0)
                stats["total_acknowledged"] = ack_stats.get("total_acknowledged", 0)
                total = stats["total_sent"]
                if total > 0:
                    stats["acknowledge_rate"] = round(stats["total_acknowledged"] / total * 100, 1)
                speeds = mem.get("ack_speeds", [])
                if speeds:
                    avg_speed = sum(s["seconds"] for s in speeds[-10:]) / min(len(speeds), 10)
                    stats["avg_ack_speed_sec"] = round(avg_speed, 1)
            except Exception:
                pass
        return stats


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
    print("═" * 55)
    print("   🧠 Smart Adaptive Alert Manager Tests")
    print("═" * 55)
    
    # Mock brain for standalone testing
    class MockBrain:
        def __init__(self):
            self._mem = {}
        def get_component_memory(self, c):
            return self._mem.setdefault(c, {})
        def _save_component_memory(self, c, d):
            self._mem[c] = d
        def log_event_experience(self, **kw):
            pass
        def get_alert_priority_adjustment(self, uid, atype):
            # محاكاة: المستخدم يتجاهل تنبيهات "system"
            if atype == "system":
                return -2.0
            # محاكاة: المستخدم يهتم بتنبيهات "trading"
            if atype == "trading":
                return 1.0
            return 0.0
        def track_alert_response(self, **kw):
            pass
    
    import services.alert_manager as _self_mod
    _self_mod._brain = MockBrain()
    
    am = AlertManager()
    
    print("\n📊 Learning Stats (Initial):")
    for k, v in am.get_learning_stats().items():
        print(f"   {k}: {v}")
    
    print("\n─" * 30)
    print("\n1. 🔽 Testing Brain-Adjusted Priority (system category -> lowered)")
    a1 = am.send_alert("System boot OK", AlertPriority.MEDIUM, category="system")
    print(f"   Requested: MEDIUM -> Got: {a1.priority}")
    
    print("\n2. 🔼 Testing Brain-Adjusted Priority (trading category -> raised)")
    a2 = am.send_alert("New EURUSD setup", AlertPriority.MEDIUM, category="trading")
    print(f"   Requested: MEDIUM -> Got: {a2.priority}")
    
    print("\n3. 🔁 Testing Dynamic Repetition Upgrade")
    print(f"   (threshold = {am._base_repetition_threshold} repetitions)")
    for i in range(am._base_repetition_threshold + 1):
        a3 = am.send_alert("Repeated signal", AlertPriority.MEDIUM, category="signal")
        print(f"   Rep #{i+1}: priority={a3.priority}, count={a3.count}")
    
    print("\n4. ✅ Testing Acknowledge + Brain Logging")
    am.acknowledge_alert("trading", "New EURUSD setup")
    
    print("\n5. ⏰ Testing Dynamic Escalation Timeout")
    print(f"   (timeout = {am._base_escalation_timeout}s, learned from brain)")
    am.send_alert("Unattended high alert", AlertPriority.HIGH, category="risk")
    wait_time = am._base_escalation_timeout + 2
    print(f"   Waiting {wait_time} seconds for escalation...")
    time.sleep(wait_time)
    
    print("\n6. 🚨 Testing Critical Priority (All Channels)")
    am.send_alert("MASSIVE LOSS DETECTED!", AlertPriority.CRITICAL, category="emergency")
    
    print("\n" + "─" * 55)
    print("\n📊 Learning Stats (After Tests):")
    for k, v in am.get_learning_stats().items():
        print(f"   {k}: {v}")
    
    print("\n" + "═" * 55)
    print("   ✅ Smart Adaptive Alert Manager tests finished!")
    print("═" * 55)
