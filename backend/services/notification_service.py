from typing import List, Dict
from database import SessionLocal
import models
from .telegram_service import telegram_service


class NotificationService:
    def send_smart_notification(self, user_id: int, message: str, market: str):
        db = SessionLocal()
        try:
            prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == user_id).first()
            if not prefs or not prefs.enable_smart_notifications:
                return

            notification_markets = prefs.notification_markets or []
            if market not in notification_markets:
                return

            # Send to dashboard (could be websocket or stored)
            # For now, send to telegram if configured
            if prefs.telegram_chat_id:
                telegram_service.send_message(prefs.telegram_chat_id, message)
        finally:
            db.close()

    def notify_pattern(self, user_id: int, market: str, pattern: str):
        message = f"ال{market} كون نموذج {pattern}"
        self.send_smart_notification(user_id, message, market)

    def notify_entry_zone(self, user_id: int, market: str):
        message = f"{market} وصل منطقة دخول قوية"
        self.send_smart_notification(user_id, message, market)

    def notify_strategy_agreement(self, user_id: int, market: str, count: int):
        message = f"{count} استراتيجيات توافقوا على شراء {market}"
        self.send_smart_notification(user_id, message, market)


notification_service = NotificationService()