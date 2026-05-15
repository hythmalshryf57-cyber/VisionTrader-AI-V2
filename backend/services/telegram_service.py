import os
import requests
from config import settings

class TelegramService:
    def __init__(self, bot_token=None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}/"

    def send_message(self, chat_id, text):
        if not self.bot_token or not chat_id:
            return
        url = self.base_url + "sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
        except Exception as e:
            print(f"Telegram Error: {e}")

    def send_alert(self, chat_id, market, rec, conf, top_3):
        emoji = "🚀" if rec == "شراء" else "🔻"
        message = f"""
{emoji} *VisionTrader Alert: {market}*
---
*Recommendation:* {rec}
*Confidence:* {conf}%
*Key Strategies:* {', '.join(top_3)}
---
Check the dashboard for full details.
        """
        self.send_message(chat_id, message)

telegram_service = TelegramService()
