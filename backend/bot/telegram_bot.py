import os
import logging

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

class TelegramNotifier:
    def __init__(self):
        self.bot = None
        if TELEGRAM_BOT_TOKEN:
            try:
                from aiogram import Bot
                # Support both aiogram 2.x and 3.x syntax gracefully if possible
                try:
                    from aiogram.client.default import DefaultBotProperties
                    from aiogram.enums import ParseMode
                    self.bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                except ImportError:
                    self.bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode="HTML")
                    
                logger.info("TelegramNotifier initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram Bot: {e}")

    async def send_sniper_alert(self, symbol: str, trade_type: str, recommendation: str, confidence: int, reason: str):
        if not self.bot or not TELEGRAM_CHAT_ID:
            logger.warning(f"Telegram Bot not configured. Auto-Sniper Alert for {symbol} printed to console instead.")
            print(f"\n{'='*50}\n🚨 AUTO-SNIPER ALERT: {symbol} 🚨\nAction: {recommendation} | Confidence: {confidence}%\n{reason}\n{'='*50}\n")
            return
        
        icon = "🟢" if "Buy" in recommendation or "شراء" in recommendation else "🔴"
        message = (
            f"<b>🚨 VisionTrader Auto-Sniper 🚨</b>\n\n"
            f"<b>Symbol:</b> {symbol}\n"
            f"<b>Type:</b> {trade_type}\n"
            f"<b>Action:</b> {icon} <b>{recommendation}</b>\n"
            f"<b>Confidence:</b> {confidence}%\n\n"
            f"<b>Details:</b>\n{reason[:800]}..."
        )
        try:
            await self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            logger.info(f"Telegram alert sent for {symbol}.")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            
    async def close(self):
        if self.bot:
            await self.bot.session.close()

telegram_notifier = TelegramNotifier()
