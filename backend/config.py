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
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    MASTER_ENCRYPTION_KEY: str = os.getenv("MASTER_ENCRYPTION_KEY", "your-master-encryption-key-here")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "your-deepseek-api-key-here")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "your-openrouter-api-key-here")
    # Gemini / Google Generative Language API
    GEMINI_API_URL: str = os.getenv(
        "GEMINI_API_URL",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
    )
    CALENDAR_API_KEY: str = os.getenv("CALENDAR_API_KEY", "your-calendar-api-key-here")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    
    # Telegram Bot config
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "your-telegram-bot-token-here")
    ADMIN_CHAT_ID: str = os.getenv("ADMIN_CHAT_ID", "6380833552")
    
    # MetaTrader 5 config
    MT5_LOGIN: int = int(os.getenv("MT5_LOGIN", "0"))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "")

settings = Settings()
