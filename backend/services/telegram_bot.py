import requests
from config import settings
import datetime


class TelegramBot:
    def __init__(self, token: str = None):
        self.token = token or getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or ''
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_alert(self, chat_id, message):
        if not self.token or not chat_id:
            return {"error": "Telegram not configured"}
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            response = requests.post(url, json=payload, timeout=5)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def alert_vpn_attempt(self, user_id, ip, isp, org, action=None):
        chat = getattr(settings, 'ADMIN_CHAT_ID', None)
        if not chat:
            return
        msg = f"⚠️ <b>VPN/Proxy Attempt Detected</b>\nUser: {user_id}\nIP: {ip}\nISP: {isp}\nORG: {org}\nAction: {action or 'unknown'}\nTime: {datetime.datetime.now(datetime.timezone.utc).isoformat()}"
        return self.send_alert(chat, msg)

    def alert_unknown_device(self, user_id, device_id, ip):
        chat = getattr(settings, 'ADMIN_CHAT_ID', None)
        if not chat:
            return
        msg = f"🔔 <b>Unknown Device</b>\nUser: {user_id}\nDevice: {device_id}\nIP: {ip}\nTime: {datetime.datetime.now(datetime.timezone.utc).isoformat()}"
        return self.send_alert(chat, msg)

    def alert_multiple_locations(self, user_id, ip1, ip2):
        chat = getattr(settings, 'ADMIN_CHAT_ID', None)
        if not chat:
            return
        msg = f"⚠️ <b>Rapid Location Change</b>\nUser: {user_id}\nFrom: {ip1}\nTo: {ip2}\nTime: {datetime.datetime.now(datetime.timezone.utc).isoformat()}"
        return self.send_alert(chat, msg)

    def alert_spam_attempt(self, user_id, ip, count):
        chat = getattr(settings, 'ADMIN_CHAT_ID', None)
        if not chat:
            return
        msg = f"🚨 <b>Possible Spam</b>\nUser: {user_id}\nIP: {ip}\nRequests: {count}\nTime: {datetime.datetime.now(datetime.timezone.utc).isoformat()}"
        return self.send_alert(chat, msg)

    def alert_password_change(self, user_id, ip):
        chat = getattr(settings, 'ADMIN_CHAT_ID', None)
        if not chat:
            return
        msg = f"🔐 <b>Password Changed</b>\nUser: {user_id}\nIP: {ip}\nTime: {datetime.datetime.now(datetime.timezone.utc).isoformat()}"
        return self.send_alert(chat, msg)

    def alert_risk_limit(self, user_id, details):
        chat = getattr(settings, 'ADMIN_CHAT_ID', None)
        if not chat:
            return
        msg = f"⚠️ <b>Risk Limit Exceeded</b>\nUser: {user_id}\nDetails: {details}\nTime: {datetime.datetime.now(datetime.timezone.utc).isoformat()}"
        return self.send_alert(chat, msg)
