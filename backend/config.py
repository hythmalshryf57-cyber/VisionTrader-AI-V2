from pydantic_settings import BaseSettings
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

class Settings(BaseSettings):
    # By default, expect DATABASE_URL to be provided (PostgreSQL for production).
    # For local development, set DATABASE_URL to a sqlite URL explicitly.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    # SECRET_KEY and MASTER_ENCRYPTION_KEY MUST be provided via environment variables.
    # Do NOT provide default values here to avoid accidental use of insecure defaults.
    SECRET_KEY: str
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    MASTER_ENCRYPTION_KEY: str
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    # TwelveData API key (optional). If not provided, code should prefer TradingView/Yahoo fallbacks.
    TWELVEDATA_API_KEY: str = os.getenv("TWELVEDATA_API_KEY", "")
    # Gemini / Google Generative Language API
    GEMINI_API_URL: str = os.getenv(
        "GEMINI_API_URL",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
    )
    CALENDAR_API_KEY: str = os.getenv("CALENDAR_API_KEY", "")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    GOOGLE_OAUTH_CLIENT_ID: str = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    GOOGLE_OAUTH_CLIENT_SECRET: str = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    RENDER_EXTERNAL_URL: str = os.getenv("RENDER_EXTERNAL_URL", "")
    GOOGLE_OAUTH_REDIRECT_URI: str = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")
    
    # Telegram Bot config
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ADMIN_CHAT_ID: str = os.getenv("ADMIN_CHAT_ID", "")
    
    # MetaTrader 5 config
    MT5_LOGIN: int = int(os.getenv("MT5_LOGIN", "0"))
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "")
    MT5_SIGNAL_MODE: bool = os.getenv("MT5_SIGNAL_MODE", "true").strip().lower() in ("1", "true", "yes", "y")

def _is_insecure_value(value: str) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    insecure = {
        "secret",
        "changeme",
        "default",
        "yoursecretkey1234567890",
        "masterencryptionkey1234567890123",
    }
    return normalized in insecure or len(value.strip()) < 32


def _validate_settings(settings: Settings):
    if _is_insecure_value(settings.SECRET_KEY):
        raise RuntimeError(
            "SECRET_KEY must be set to a strong random value with at least 32 characters."
        )
    if _is_insecure_value(settings.MASTER_ENCRYPTION_KEY):
        raise RuntimeError(
            "MASTER_ENCRYPTION_KEY must be set to a strong random value with at least 32 characters."
        )
    if not settings.ADMIN_EMAIL.strip() or not settings.ADMIN_PASSWORD.strip():
        raise RuntimeError(
            "ADMIN_EMAIL and ADMIN_PASSWORD must be configured for secure admin access."
        )
    if not settings.TELEGRAM_BOT_TOKEN.strip():
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN must be configured for Telegram integration."
        )
    if settings.GOOGLE_OAUTH_CLIENT_ID.strip() and not settings.GOOGLE_OAUTH_CLIENT_SECRET.strip():
        raise RuntimeError(
            "GOOGLE_OAUTH_CLIENT_SECRET must be configured when GOOGLE_OAUTH_CLIENT_ID is set."
        )


try:
    settings = Settings()
    if not settings.GOOGLE_OAUTH_REDIRECT_URI.strip():
        if settings.RENDER_EXTERNAL_URL.strip():
            settings.GOOGLE_OAUTH_REDIRECT_URI = settings.RENDER_EXTERNAL_URL.rstrip('/') + '/api/auth/google/callback'
        elif settings.GOOGLE_OAUTH_CLIENT_ID.strip() and settings.GOOGLE_OAUTH_CLIENT_SECRET.strip():
            settings.GOOGLE_OAUTH_REDIRECT_URI = 'https://visiontrader-ai-v2.onrender.com/api/auth/google/callback'
        else:
            settings.GOOGLE_OAUTH_REDIRECT_URI = 'http://localhost:8000/api/auth/google/callback'
    _validate_settings(settings)
except Exception as exc:
    # Fail loudly with a clear message about required secrets
    raise RuntimeError(
        f"Failed to initialize application settings: {exc}. \n"
        "Ensure environment variables are set: SECRET_KEY, MASTER_ENCRYPTION_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, and TELEGRAM_BOT_TOKEN are provided and secure."
    ) from exc
