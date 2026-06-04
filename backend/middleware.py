import time
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import logging
from services.monitor_service import monitor_service
from services.telegram_bot import TelegramBot
from config import settings
from database import get_db
from models import User
from datetime import date, datetime, timezone
from jose import JWTError, jwt
from config import settings

# Configure Logging
logging.basicConfig(
    filename='VisionTrader_security.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.rate_limit_records = defaultdict(list)
        self.limit = 1000 # raised for dev/testing
        self.window = 3600 # per hour
        self.telegram = TelegramBot(token=getattr(settings, 'TELEGRAM_BOT_TOKEN', None))

    async def dispatch(self, request, call_next):
        client_ip = request.client.host
        current_time = time.time()

        # Rate Limiting Logic
        self.rate_limit_records[client_ip] = [t for t in self.rate_limit_records[client_ip] if current_time - t < self.window]
        
        if len(self.rate_limit_records[client_ip]) >= self.limit:
            logging.warning(f"Rate limit exceeded for IP: {client_ip} on {request.url.path}")
            raise HTTPException(status_code=429, detail="لقد تجاوزت حد الطلبات المسموح به (10 طلبات في الساعة)")

        self.rate_limit_records[client_ip].append(current_time)

        # Log unauthorized attempts (placeholder logic)
        if "admin" in request.url.path and not request.headers.get("Authorization"):
            logging.error(f"Unauthorized access attempt to admin area from IP: {client_ip}")

        # Run MonitorService to inspect request, detect VPN/proxy and record activity
        try:
            monitor_result = monitor_service.inspect_request(request, action=None, current_user=None)
            if monitor_result.get('block'):
                logging.warning(f"Monitor blocked request from {client_ip}: {monitor_result.get('reason')}")
                raise HTTPException(status_code=403, detail="تم حظر الجلسة لأمن الشبكة (VPN/Proxy)")
        except HTTPException:
            raise
        except Exception as e:
            # Monitor failure should not take down the app; log and continue
            logging.exception(f"Monitor failure: {e}")

        response = await call_next(request)
        return response


class TrialMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        # Skip for auth endpoints and admin
        if request.url.path.startswith("/api/auth/") or request.url.path.startswith("/admin"):
            return await call_next(request)

        # Get user from token
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return await call_next(request)

        token = token[7:]  # Remove "Bearer "
        user_id = None
        legacy_email = None
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            sub = payload.get("sub")
            if isinstance(sub, int):
                user_id = sub
            elif isinstance(sub, str) and sub.isdigit():
                user_id = int(sub)
            elif isinstance(sub, str):
                legacy_email = sub.strip().lower()
        except (JWTError, ValueError):
            return await call_next(request)

        if user_id or legacy_email:
            db = next(get_db())
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
            else:
                user = db.query(User).filter(User.email == legacy_email).first()

            if user:
                today = date.today()
                if user.last_analysis_date != today:
                    user.daily_analyses_count = 0
                    user.last_analysis_date = today
                    db.commit()

                if user.trial_end and datetime.now(timezone.utc) > user.trial_end:
                    # Trial expired
                    if request.url.path.startswith("/api/analysis/"):
                        raise HTTPException(status_code=403, detail="انتهت فترة التجربة المجانية")

                if user.daily_analyses_count >= 10:
                    if request.url.path.startswith("/api/analysis/"):
                        raise HTTPException(status_code=429, detail="لقد تجاوزت حد التحليلات اليومية (10)")

            db.close()

        response = await call_next(request)
        return response
