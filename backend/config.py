from pydantic_settings import BaseSettings
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'visiontrader.db'}")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 Hours
    MASTER_ENCRYPTION_KEY: str = os.getenv("MASTER_ENCRYPTION_KEY", "your-master-encryption-key-here")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "your-gemini-api-key-here")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "your-deepseek-api-key-here")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "your-openrouter-api-key-here")
    CALENDAR_API_KEY: str = os.getenv("CALENDAR_API_KEY", "your-calendar-api-key-here")
    
    # Telegram Bot config
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "your-telegram-bot-token-here")
    ADMIN_CHAT_ID: str = os.getenv("ADMIN_CHAT_ID", "your-admin-chat-id-here")
    
    # MetaTrader 5 config
    MT5_LOGIN: int = 0
    MT5_PASSWORD: str = ""
    MT5_SERVER: str = ""

settings = Settings()
