import logging
import os
import json
import base64
import time
import hashlib
import io
import csv
import re
import requests
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from database import get_db, engine, SessionLocal, create_tables
from supabase_client import supabase_client, SUPABASE_CONFIGURED
from config import settings
import models
import auth
from auth import router as auth_router
from admin import router as admin_router
from routers.analysis import router as analysis_router
from services.journal_service import journal_service
from services.smart_journal import smart_journal
from services.voting_engine import voting_engine
from services.ai_core import ai_core_service
from middleware import SecurityMiddleware, TrialMiddleware
from services.auto_scanner import auto_scanner
from services.cache_service import cache_service
from services.vector_memory import vector_memory
from services.voice_service import VoiceService
from services.broker_auditor import BrokerAuditor
from services.smart_orders import SmartOrdersService
from services.shadow_trader import ShadowTrader
from services.trade_mover import trade_mover_service
from services.trade_manager import trade_manager_service
from services.trade_protection import trade_protection_service
from services.market_protection import market_protection_service
from services.deep_market import deep_market_scanner
from services.calendar_service import calendar_service
from services.binance_service import BinanceService
from services.internal_brain import InternalBrain
from services.tradingview_service import TradingViewService
from services.telegram_service import telegram_service
from services.alert_manager import create_alert
from services.agent_manager import AgentManager
from services.backtest_engine import backtest_engine

# Temporarily disable social sentiment service due to recursion error
# from services.social_sentiment import social_sentiment_service
social_sentiment_service = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

SYSTEM_METRICS = {
    "start_time": datetime.now(timezone.utc),
    "request_count": 0,
    "gemini_calls": 0,
    "deepseek_calls": 0,
    "daily_requests": {},
    "last_error": "No errors yet"
}

FREE_ANALYSIS_LIMIT = 3
USER_SESSIONS = {}

logger = logging.getLogger(__name__)

from fastapi.staticfiles import StaticFiles

# Optional Telegram bot import
try:
    from services.telegram_payment_bot import bot, dp
    TELEGRAM_BOT_AVAILABLE = True
except Exception as e:
    print(f"Telegram bot not available: {e}")
    TELEGRAM_BOT_AVAILABLE = False
    bot, dp = None, None

import asyncio
import threading

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_base64_image(image_data: str, filename: str) -> str:
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    try:
        decoded = base64.b64decode(image_data)
    except Exception:
        return ""
    safe_name = filename.replace(" ", "_")
    file_path = os.path.join(UPLOAD_DIR, f"{int(time.time())}_{safe_name}")
    with open(file_path, "wb") as f:
        f.write(decoded)
    return file_path

voice_service = VoiceService()
broker_auditor = BrokerAuditor()
smart_orders_service = SmartOrdersService()
binance_service = BinanceService()
tradingview_service = TradingViewService()
internal_brain_service = InternalBrain()
agent_manager = AgentManager()

# Create or verify tables on startup
create_tables(models.Base)

# Ensure admin user exists by environment variables
def ensure_admin_user():
    admin_email = settings.ADMIN_EMAIL.strip().lower()
    admin_password = settings.ADMIN_PASSWORD
    if not admin_email or not admin_password:
        return

    db = SessionLocal()
    try:
        admin_user = db.query(models.User).filter(models.User.email == admin_email).first()
        if admin_user:
            updated = False
            if not admin_user.is_admin:
                admin_user.is_admin = True
                updated = True
            if not auth.verify_password(admin_password, admin_user.hashed_password):
                admin_user.hashed_password = auth.get_password_hash(admin_password)
                updated = True
            if updated:
                db.add(admin_user)
                db.commit()
        else:
            trial_start = datetime.now(timezone.utc)
            trial_end = trial_start + timedelta(days=3650)
            new_admin = models.User(
                email=admin_email,
                hashed_password=auth.get_password_hash(admin_password),
                invite_code=None,
                ip_address=None,
                is_active=True,
                is_admin=True,
                trial_start=trial_start,
                trial_end=trial_end,
                daily_analyses_count=0,
                has_used_trial=True
            )
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            default_prefs = models.UserPreferences(
                user_id=new_admin.id,
                theme='dark',
                language='ar',
                demo_mode=False,
                demo_balance=1000000.0,
                trading_mode='day',
                capital=10000.0,
                account_balance=10000.0,
                risk_percentage=1.0,
                favorite_strategies='[]',
                watchlist='[]'
            )
            db.add(default_prefs)
            db.commit()
            print(f"Created admin user: {admin_email}")
    except Exception as exc:
        print(f"Admin user setup failed: {exc}")
    finally:
        db.close()

ensure_admin_user()

# Ensure SQLite migrations for known schema additions
if engine.url.drivername.startswith("sqlite"):
    try:
        inspector = inspect(engine)
        with engine.connect() as conn:
            tables = inspector.get_table_names()
            if "strategy_performance" in tables:
                columns = [col["name"] for col in inspector.get_columns("strategy_performance")]
                if "last_updated" not in columns:
                    conn.execute(text("ALTER TABLE strategy_performance ADD COLUMN last_updated DATETIME"))
            if "trade_experience" in tables:
                columns = [col["name"] for col in inspector.get_columns("trade_experience")]
                if "analysis_id" not in columns:
                    conn.execute(text("ALTER TABLE trade_experience ADD COLUMN analysis_id INTEGER"))
            if "user_preferences" in tables:
                columns = [col["name"] for col in inspector.get_columns("user_preferences")]
                sqlite_migrations = {
                    "trading_mode": "ALTER TABLE user_preferences ADD COLUMN trading_mode TEXT DEFAULT 'day'",
                    "capital": "ALTER TABLE user_preferences ADD COLUMN capital FLOAT DEFAULT 10000.0",
                    "account_balance": "ALTER TABLE user_preferences ADD COLUMN account_balance FLOAT DEFAULT 10000.0",
                    "risk_percentage": "ALTER TABLE user_preferences ADD COLUMN risk_percentage FLOAT DEFAULT 1.0",
                    "favorite_strategies": "ALTER TABLE user_preferences ADD COLUMN favorite_strategies TEXT DEFAULT '[]'",
                    "watchlist": "ALTER TABLE user_preferences ADD COLUMN watchlist TEXT DEFAULT '[]'",
                    "analysis_locked_until": "ALTER TABLE user_preferences ADD COLUMN analysis_locked_until DATETIME",
                    "trading_locked_until": "ALTER TABLE user_preferences ADD COLUMN trading_locked_until DATETIME",
                    "daily_profit_target_percent": "ALTER TABLE user_preferences ADD COLUMN daily_profit_target_percent FLOAT DEFAULT 30.0",
                    "daily_loss_limit_percent": "ALTER TABLE user_preferences ADD COLUMN daily_loss_limit_percent FLOAT DEFAULT 5.0",
                    "daily_loss_limit_amount": "ALTER TABLE user_preferences ADD COLUMN daily_loss_limit_amount FLOAT",
                    "trading_locked_today": "ALTER TABLE user_preferences ADD COLUMN trading_locked_today BOOLEAN DEFAULT 0",
                    "lock_reason": "ALTER TABLE user_preferences ADD COLUMN lock_reason TEXT",
                    "notification_markets": "ALTER TABLE user_preferences ADD COLUMN notification_markets TEXT DEFAULT '[\"XAUUSD\", \"EURUSD\", \"GBPUSD\"]'",
                    "enable_smart_notifications": "ALTER TABLE user_preferences ADD COLUMN enable_smart_notifications BOOLEAN DEFAULT 1",
                    "custom_indicators": "ALTER TABLE user_preferences ADD COLUMN custom_indicators TEXT DEFAULT '[]'"
                }
                for column_name, alter_sql in sqlite_migrations.items():
                    if column_name not in columns:
                        conn.execute(text(alter_sql))
            conn.commit()
    except Exception as exc:
        print(f"SQLite schema migration skipped: {exc}")

tags_metadata = [
    {
        "name": "auth",
        "description": "Authentication and user management (المصادقة وإدارة المستخدمين).",
    },
    {
        "name": "admin",
        "description": "Admin operations and platform control (عمليات المشرف والتحكم بالمنصة).",
    },
    {
        "name": "analysis",
        "description": "AI-powered market analysis and scanning (تحليل السوق الذكي والمسح).",
    },
    {
        "name": "trading",
        "description": "Live trading execution and MT5 integration (تنفيذ الصفقات والربط مع منصات التداول).",
    },
    {
        "name": "system",
        "description": "System health, settings, and metrics (حالة النظام والإعدادات).",
    }
]

app = FastAPI(
    title="VisionTrader AI Pro API",
    description="""
# VisionTrader AI - Automated AI Trading Platform
مرحباً بك في التوثيق الرسمي لواجهة برمجة تطبيقات VisionTrader AI. يوفر هذا النظام أتمتة كاملة لعمليات التداول، إدارة المخاطر، وتحليلات السوق الذكية باستخدام تقنيات الذكاء الاصطناعي.

## Features (الميزات الأساسية)
* **Real-time Analysis:** مسح وتحليل حي للأسواق.
* **Auto Trading:** تنفيذ صفقات تلقائي (MT5 / Binance).
* **Smart Risk Management:** حماية ديناميكية وإدارة رأس المال.
* **Self-Healing Agents:** وكلاء ذكاء اصطناعي لإصلاح الأخطاء وتحديث النظام بشكل مستمر.

[Visit our GitHub](https://github.com/visiontrader) | [Visit Website](https://visiontrader.ai)
    """,
    version="2.0.0",
    terms_of_service="https://visiontrader.ai/terms/",
    contact={
        "name": "VisionTrader Support",
        "url": "https://visiontrader.ai/support",
        "email": "support@visiontrader.ai",
    },
    license_info={
        "name": "Pro License",
        "url": "https://visiontrader.ai/license",
    },
    openapi_tags=tags_metadata
)

app.add_middleware(SecurityMiddleware)
app.add_middleware(TrialMiddleware)

if SUPABASE_CONFIGURED:
    print("Supabase client initialized and ready.")
else:
    print("Supabase client not configured or unavailable; using local database fallback if needed.")

# CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(analysis_router, prefix="/api", tags=["analysis"])

@app.middleware("http")
async def track_request_metrics(request: Request, call_next):
    SYSTEM_METRICS["request_count"] += 1
    today = datetime.now(timezone.utc).date().isoformat()
    SYSTEM_METRICS["daily_requests"][today] = SYSTEM_METRICS["daily_requests"].get(today, 0) + 1
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        SYSTEM_METRICS["last_error"] = f"{datetime.now(timezone.utc).isoformat()} - {type(exc).__name__}: {str(exc)}"
        raise


# Start a shared BinanceWebSocketService at app startup and attach it to module-level binance_service
shared_ws = None

@app.on_event("startup")
async def start_shared_ws():
    global shared_ws, binance_service
    try:
        from services.websocket_service import BinanceWebSocketService
        import services.binance_service as bin_mod

        symbols_env = os.getenv("WS_SYMBOLS", "BTCUSDT,ETHUSDT,BNBUSDT")
        symbols = [s.strip().upper() for s in symbols_env.split(",") if s.strip()]
        if not symbols:
            logger.info("No WS_SYMBOLS configured; skipping shared websocket startup")
            return

        shared_ws = BinanceWebSocketService(symbols)
        try:
            bin_mod.binance_service.ws_service = shared_ws
        except Exception:
            logger.exception("Failed to attach ws_service to module-level binance_service")
        try:
            # Prefer module-level instance for main module usage
            binance_service = bin_mod.binance_service
        except Exception:
            pass

        asyncio.create_task(shared_ws.start())
        logger.info("Started shared BinanceWebSocketService for symbols: %s", symbols)
    except Exception as e:
        logger.exception("Failed to initialize shared websocket: %s", e)

    # Start DegradationWatcher if available
    try:
        from services.degradation_watcher import DegradationWatcher
        degr = DegradationWatcher()
        degr.start()
        logger.info("DegradationWatcher started")
    except Exception:
        logger.exception("Failed to start DegradationWatcher (optional)")


@app.on_event("shutdown")
async def stop_shared_ws():
    global shared_ws
    try:
        if shared_ws:
            await shared_ws.stop()
            logger.info("Shared BinanceWebSocketService stopped")
    except Exception as e:
        logger.exception("Error stopping shared websocket: %s", e)

# Mount Frontend later so API routes are registered before the static catch-all
candidate_frontend_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend")),
    os.path.abspath(os.path.join(os.getcwd(), "frontend")),
    os.path.abspath(os.path.join(os.sep, "frontend")),
]
frontend_path = next((path for path in candidate_frontend_paths if os.path.isdir(path)), None)
if frontend_path:
    print(f"Frontend found at: {frontend_path}")
else:
    print("WARNING: Frontend directory not found. /frontend static route disabled.")


def _generate_report_for_user(db, user):
    today = datetime.now().date()
    entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.user_id == user.id,
        models.JournalEntry.date >= datetime(today.year, today.month, today.day)
    ).all()
    total_trades = len(entries)
    wins = len([e for e in entries if _normalize_result(e.result) == "win"])
    losses = len([e for e in entries if _normalize_result(e.result) == "loss"])
    pnl = sum((e.profit_loss or 0) for e in entries)
    summary = f"اليوم: {total_trades} صفقات، دخلت {total_trades}، ربحت {wins}، خسرت {losses}. الربح: {pnl:+.2f}$"
    report = db.query(models.DailyReport).filter(
        models.DailyReport.user_id == user.id,
        models.DailyReport.report_date == today
    ).first()
    if not report:
        report = models.DailyReport(
            user_id=user.id,
            report_date=today,
            summary=summary,
            total_trades=total_trades,
            entered_trades=total_trades,
            wins=wins,
            losses=losses,
            profit_loss=pnl,
        )
        db.add(report)
    else:
        report.summary = summary
        report.total_trades = total_trades
        report.entered_trades = total_trades
        report.wins = wins
        report.losses = losses
        report.profit_loss = pnl
        report.created_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report


def _close_shadow_trade(db, trade, exit_price: float, reason: str):
    if trade.status != "open":
        return None

    is_buy = trade.stop_loss is None or (trade.entry_price is not None and trade.stop_loss < trade.entry_price)
    trade.exit_price = exit_price
    trade.status = "closed"
    trade.pnl = round((exit_price - trade.entry_price) * 100, 2) if is_buy else round((trade.entry_price - exit_price) * 100, 2)
    db.commit()

    result_text = "win" if trade.pnl >= 0 else "loss"
    recommendation_text = "شراء" if is_buy else "بيع"
    summary = f"صفقة {trade.market} {'ربحت' if trade.pnl >= 0 else 'خسرت'} {abs(trade.pnl):.2f}$. السبب: {reason}"

    journal = models.JournalEntry(
        user_id=trade.user_id,
        date=datetime.now(timezone.utc),
        market=trade.market,
        recommendation=recommendation_text,
        result=result_text,
        profit_loss=trade.pnl,
        confidence=None,
        notes=summary,
    )
    db.add(journal)

    experience = models.TradeExperience(
        user_id=trade.user_id,
        market=trade.market,
        recommendation=recommendation_text,
        result=result_text,
        profit_loss=trade.pnl,
        notes=summary,
    )
    db.add(experience)
    db.commit()
    return summary


def _infer_shadow_direction(trade):
    if trade.stop_loss is None:
        if trade.take_profit is not None and trade.take_profit < trade.entry_price:
            return "sell"
        return "buy"
    return "buy" if trade.stop_loss < trade.entry_price else "sell"


def _monitor_shadow_trades():
    while True:
        db = SessionLocal()
        try:
            open_trades = db.query(models.ShadowTrade).filter(models.ShadowTrade.status == "open").all()
            for trade in open_trades:
                market_symbol = ''.join(ch for ch in str(trade.market) if ch.isalnum()).upper()
                if not market_symbol:
                    continue

                try:
                    current_price = binance_service.get_ticker_price(market_symbol)
                except Exception:
                    continue

                if current_price <= 0:
                    continue

                direction = _infer_shadow_direction(trade)
                if direction == "buy":
                    if trade.take_profit is not None and current_price >= trade.take_profit:
                        _close_shadow_trade(db, trade, current_price, "ارتد من الدعم")
                    elif trade.stop_loss is not None and current_price <= trade.stop_loss:
                        _close_shadow_trade(db, trade, current_price, "خبر مفاجئ")
                else:
                    if trade.take_profit is not None and current_price <= trade.take_profit:
                        _close_shadow_trade(db, trade, current_price, "ارتد من المقاومة")
                    elif trade.stop_loss is not None and current_price >= trade.stop_loss:
                        _close_shadow_trade(db, trade, current_price, "خبر مفاجئ")
        except Exception as e:
            logger.exception(f"Shadow trade monitor failed: {e}")
        finally:
            db.close()
        time.sleep(30)


def _daily_report_scheduler():
    while True:
        now = datetime.now()
        target = now.replace(hour=21, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        time.sleep(wait_seconds)
        db = SessionLocal()
        try:
            users = db.query(models.User).filter(models.User.is_active == True).all()
            for user in users:
                try:
                    _generate_report_for_user(db, user)
                except Exception as e:
                    logger.exception(f"Daily report generation failed for user {user.id}: {e}")
        finally:
            db.close()


def _weekly_strategy_refresh_scheduler():
    # Run a weekly refresh of strategy performance based on recent trade experience
    time.sleep(60)
    while True:
        try:
            internal_brain_service.auto_update_strategy_performance()
        except Exception as e:
            logger.exception(f"Weekly strategy refresh failed: {e}")
        time.sleep(7 * 24 * 60 * 60)


def _daily_reset_scheduler():
    # Reset daily trading locks and generate challenges
    while True:
        now = datetime.now()
        target = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        time.sleep(wait_seconds)
        db = SessionLocal()
        try:
            # Reset trading_locked_today for all users
            db.query(models.UserPreferences).update({"trading_locked_today": False, "lock_reason": None})
            db.commit()
            # Generate new weekly challenge
            _generate_weekly_challenge(db)
        except Exception as e:
            logger.exception(f"Daily reset failed: {e}")
        finally:
            db.close()


def _generate_weekly_challenge(db):
    week_start = datetime.now(timezone.utc).date() - timedelta(days=datetime.now(timezone.utc).weekday())
    existing = db.query(models.WeeklyChallenge).filter(models.WeeklyChallenge.week_start == week_start).first()
    if existing:
        return
    # Random challenge types
    import random
    challenge_types = [
        {"type": "trades_on_market", "market": "XAUUSD", "target": 5, "desc": "حقق 5 صفقات ناجحة على الذهب"},
        {"type": "success_rate", "target": 70.0, "desc": "حقق نسبة نجاح 70% هذا الأسبوع"},
        {"type": "profit_target", "target": 500.0, "desc": "حقق ربح 500$ هذا الأسبوع"}
    ]
    chosen = random.choice(challenge_types)
    challenge = models.WeeklyChallenge(
        week_start=week_start,
        challenge_type=chosen["type"],
        target_value=chosen["target"],
        market=chosen.get("market"),
        description=chosen["desc"],
        reward_type="free_analysis" if random.random() > 0.5 else "badge",
        reward_description="🎉 تحليل مجاني إضافي" if chosen["reward_type"] == "free_analysis" else "⭐ وسام المتداول المتميز"
    )
    db.add(challenge)
    db.commit()


@app.on_event("startup")
def start_background_workers():
    report_thread = threading.Thread(target=_daily_report_scheduler, daemon=True)
    report_thread.start()
    monitor_thread = threading.Thread(target=_monitor_shadow_trades, daemon=True)
    monitor_thread.start()
    market_monitor_thread = threading.Thread(target=market_protection_service.run, daemon=True)
    market_monitor_thread.start()
    strategy_refresh_thread = threading.Thread(target=_weekly_strategy_refresh_scheduler, daemon=True)
    strategy_refresh_thread.start()
    reset_thread = threading.Thread(target=_daily_reset_scheduler, daemon=True)
    reset_thread.start()

@app.get("/api/health")
async def health():
    return {"status": "online", "version": "Professional 2.0"}

# --- WebSocket Live Dashboard ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

ws_manager = ConnectionManager()

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

async def broadcast_live_data():
    import random
    from datetime import datetime
    while True:
        await asyncio.sleep(1)
        if not ws_manager.active_connections:
            continue
        try:
            data = {
                "type": "update",
                "prices": {
                    "BTC/USD": round(random.uniform(60000, 65000), 2),
                    "ETH/USD": round(random.uniform(3000, 3500), 2),
                    "XAU/USD": round(random.uniform(2300, 2400), 2)
                },
                "live_trades": random.randint(10, 50),
                "pnl": round(random.uniform(-1000, 5000), 2),
                "status": "Active",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await ws_manager.broadcast(json.dumps(data))
            
            if random.random() < 0.10: # 10% chance for an alert
                alert = {
                    "type": "alert",
                    "message": "High volatility detected on XAU/USD!" if random.random() > 0.5 else "New sniper entry on BTC/USD!"
                }
                await ws_manager.broadcast(json.dumps(alert))
        except Exception as e:
            logger.error(f"WebSocket broadcast error: {e}")

@app.on_event("startup")
async def start_ws_broadcaster():
    asyncio.create_task(broadcast_live_data())


# --- Analysis & Chat ---
@app.post("/api/analysis/process")
async def process_analysis(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user), request: Request = None):
    protection = trade_protection_service.check_protection(current_user.id)
    if protection.get("analysis_locked"):
        raise HTTPException(status_code=403, detail=protection.get("analysis_message") or "تحليل مغلق مؤقتاً.")

    if current_user.daily_analyses_count >= FREE_ANALYSIS_LIMIT:
        invite_code = (payload.get("invite_code") or "").strip() or (current_user.invite_code or "").strip()
        if not invite_code:
            raise HTTPException(
                status_code=403,
                detail="لقد تجاوزت الحد المجاني البالغ 3 تحليلات. الرجاء إدخال رمز دعوة صالح للمتابعة."
            )
        try:
            auth._apply_invite_code_to_user(current_user, invite_code, db=db, client_ip=request.client.host if request else None)
        except HTTPException as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    market = payload.get("market", "Unknown")
    images = payload.get("images", [])
    saved_path = ""
    if images:
        first_image = images[0]
        if isinstance(first_image, dict):
            saved_path = save_base64_image(first_image.get("data", ""), first_image.get("name", "chart.png"))

    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    cached_result = cache_service.get_analysis(market, payload_hash)
    if cached_result is not None:
        cached_result["from_cache"] = True
        return cached_result

    visual_description = payload.get("visual_description") or f"Analysis for {market} based on uploaded charts."
    visual_context = [{
        "description": visual_description,
        "images": images,
        "image_path": saved_path
    }]

    if payload.get("chart_data"):
        visual_context.append({
            "chart_data": payload.get("chart_data")
        })

    if binance_service.ws_service:
        symbol = market.upper().replace("/", "").replace("-", "")
        live_data = binance_service.ws_service.get_live_data(symbol)
        if live_data:
            visual_context.append({
                "order_book": {
                    "bids": live_data.get("bids", []),
                    "asks": live_data.get("asks", [])
                },
                "recent_trades": live_data.get("recent_trades", [])
            })

    memory_matches = vector_memory.find_similar(visual_description, top_k=3, db=db)
    memory_insight = vector_memory.get_insight(visual_description, db=db)

    # Run AgentManager first and use orchestrator weights for VotingEngine
    orchestrator_weights = None
    try:
        unified_data = voting_engine.data_adapter.normalize_input(visual_context, market)
        agent_payload = agent_manager.run(unified_data)
        orchestrator_weights = agent_payload.get("orchestrator", {}).get("weights")
    except Exception:
        logger.exception("AgentManager pre-analysis failed")

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(voting_engine.analyze, visual_context, market, current_user.id, orchestrator_weights=orchestrator_weights),
            timeout=12
        )

        # If AI reported insufficient data, fall back to strategy-only voting (no external AI)
        if isinstance(result, dict) and result.get("recommendation") == "بيانات غير كافية":
            try:
                ud = unified_data if 'unified_data' in locals() else voting_engine.data_adapter.normalize_input(visual_context, market)
                strategy_weights = voting_engine.internal_brain.get_strategy_weights(user_id=current_user.id)
                cluster_results = voting_engine.cluster_voting.vote_clusters(ud.get("chart_data", {}), market, strategy_weights, orchestrator_weights=orchestrator_weights)
                judge_result = voting_engine.brain_judge._internal_judge(cluster_results)
                final_decision = voting_engine.decision_matrix.calculate_final_score(cluster_results, judge_result)
                result = {
                    "recommendation": final_decision["recommendation"],
                    "strength": final_decision.get("strength"),
                    "confidence": final_decision["confidence"],
                    "final_score": final_decision.get("final_score"),
                    "reason": "Fallback to strategy-only Voting Engine (no external AI available)",
                    "cluster_breakdown": {
                        "power": cluster_results["power"],
                        "geometric": cluster_results["geometric"],
                        "momentum": cluster_results["momentum"]
                    },
                    "judge_result": judge_result,
                    "ai_analysis": None,
                    "environment_status": "fallback",
                    "data_quality": ud.get("quality_score", 0),
                    "issues": ud.get("issues", []),
                    "market": market,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except Exception:
                logger.exception("Strategy-only fallback failed after AI reported insufficient data")

    except asyncio.TimeoutError:
        # Try strategy-only fallback before returning suspended
        try:
            ud = unified_data if 'unified_data' in locals() else voting_engine.data_adapter.normalize_input(visual_context, market)
            strategy_weights = voting_engine.internal_brain.get_strategy_weights(user_id=current_user.id)
            cluster_results = voting_engine.cluster_voting.vote_clusters(ud.get("chart_data", {}), market, strategy_weights, orchestrator_weights=orchestrator_weights)
            judge_result = voting_engine.brain_judge._internal_judge(cluster_results)
            final_decision = voting_engine.decision_matrix.calculate_final_score(cluster_results, judge_result)
            result = {
                "recommendation": final_decision["recommendation"],
                "strength": final_decision.get("strength"),
                "confidence": final_decision["confidence"],
                "final_score": final_decision.get("final_score"),
                "reason": "Timeout — fallback to strategy-only Voting Engine",
                "cluster_breakdown": {
                    "power": cluster_results["power"],
                    "geometric": cluster_results["geometric"],
                    "momentum": cluster_results["momentum"]
                },
                "judge_result": judge_result,
                "ai_analysis": None,
                "environment_status": "fallback",
                "data_quality": ud.get("quality_score", 0),
                "issues": ud.get("issues", []),
                "market": market,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception:
            logger.exception("Strategy-only fallback failed after timeout")
            result = {
                "recommendation": "تعليق",
                "confidence": 0,
                "reason": "انتهت المهلة أثناء تحليل البيانات.",
                "market": market,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        # Try strategy-only fallback when AI raises unexpected exception
        try:
            ud = unified_data if 'unified_data' in locals() else voting_engine.data_adapter.normalize_input(visual_context, market)
            strategy_weights = voting_engine.internal_brain.get_strategy_weights(user_id=current_user.id)
            cluster_results = voting_engine.cluster_voting.vote_clusters(ud.get("chart_data", {}), market, strategy_weights, orchestrator_weights=orchestrator_weights)
            judge_result = voting_engine.brain_judge._internal_judge(cluster_results)
            final_decision = voting_engine.decision_matrix.calculate_final_score(cluster_results, judge_result)
            result = {
                "recommendation": final_decision["recommendation"],
                "strength": final_decision.get("strength"),
                "confidence": final_decision["confidence"],
                "final_score": final_decision.get("final_score"),
                "reason": f"AI failed: {str(e)} — fallback to strategy-only Voting Engine",
                "cluster_breakdown": {
                    "power": cluster_results["power"],
                    "geometric": cluster_results["geometric"],
                    "momentum": cluster_results["momentum"]
                },
                "judge_result": judge_result,
                "ai_analysis": None,
                "environment_status": "fallback",
                "data_quality": ud.get("quality_score", 0),
                "issues": ud.get("issues", []),
                "market": market,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception:
            logger.exception("Strategy-only fallback failed after AI exception: %s", e)
            result = {
                "recommendation": "تعليق",
                "confidence": 0,
                "reason": f"فشل التحليل: {str(e)}",
                "market": market,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    try:
        analysis = models.Analysis(
            user_id=current_user.id,
            market=market,
            image_path=saved_path,
            description=visual_description,
            result_json=json.dumps(result, ensure_ascii=False)
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        result['analysis_id'] = analysis.id
        vector_memory.store_analysis(analysis.id, visual_description, result.get('recommendation', 'unknown'), db=db)
        result['memory_matches'] = memory_matches
        result['memory_insight'] = memory_insight

        # Update daily analyses count
        current_user.daily_analyses_count += 1
        db.commit()
    except Exception as e:
        logger.exception(f"Failed to save analysis result for market {market}: {e}")

    cache_service.cache_analysis(market, payload_hash, result)
    return result

@app.get("/api/analysis/latest")
def get_latest_analysis(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    analysis = db.query(models.Analysis).filter(
        models.Analysis.user_id == current_user.id,
        models.Analysis.is_deleted == False
    ).order_by(models.Analysis.created_at.desc(), models.Analysis.id.desc()).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found")

    result_data = analysis.result_json
    if result_data:
        try:
            result_data = json.loads(result_data)
        except Exception:
            pass

    return {
        "id": analysis.id,
        "market": analysis.market,
        "image_path": analysis.image_path,
        "description": analysis.description,
        "result": result_data,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }

@app.get("/api/analysis/{analysis_id}")
def get_analysis_by_id(analysis_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    analysis = db.query(models.Analysis).filter(
        models.Analysis.id == analysis_id,
        models.Analysis.user_id == current_user.id,
        models.Analysis.is_deleted == False
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found")

    result_data = analysis.result_json
    if result_data:
        try:
            result_data = json.loads(result_data)
        except Exception:
            pass

    return {
        "id": analysis.id,
        "market": analysis.market,
        "image_path": analysis.image_path,
        "description": analysis.description,
        "result": result_data,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }

@app.post("/api/analysis/mentor")
async def mentor_chat(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    return {
        "error": "feature_disabled",
        "message": "Mentor chat feature غير متاحة حتى يتم ربطه بخدمة تحليل ذكي حقيقي."
    }


@app.get("/api/daily-limits/status")
def get_daily_limits_status(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Return daily limits status for the current user."""
    status = trade_protection_service.check_protection(current_user.id)
    # Include user preference details
    prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == current_user.id).first()
    if prefs:
        status["daily_loss_limit_percent"] = float(prefs.daily_loss_limit_percent or 5.0)
        status["daily_loss_limit_amount"] = float(prefs.daily_loss_limit_amount) if prefs.daily_loss_limit_amount else None
        status["capital"] = float(prefs.capital or 0.0)
    return status

@app.post("/api/cache/clear")
def clear_cache(current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    cache_service.clear()
    return {"status": "success", "message": "Cache cleared"}

# --- Journal & Stats ---
@app.post("/api/journal")
def add_journal(entry: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    required = ['market', 'result']
    for k in required:
        if k not in entry:
            raise HTTPException(status_code=400, detail=f"Field {k} is required")

    recommendation = entry.get('recommendation') or "No recommendation provided"
    profit = entry.get('pnl') if 'pnl' in entry else entry.get('profit_loss')
    if profit is None:
        profit = 0.0

    # Manual journal entries are admin-only to prevent users from spoofing historical data
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required to add journal entries manually")

    return journal_service.add_entry(
        user_id=current_user.id,
        market=entry['market'],
        recommendation=recommendation,
        result=entry['result'],
        profit_loss=profit,
        notes=entry.get('notes'),
        mood_before=entry.get('mood_before'),
        mood_after=entry.get('mood_after'),
        confidence=entry.get('confidence')
    )

@app.get("/api/journal")
def get_journal(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return journal_service.get_entries(user_id=current_user.id)

@app.get("/api/stats/comparison")
def get_comparison(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Aggregate strategy performance
    strategies = db.query(models.StrategyPerformance).all()
    total_wins = sum(s.wins for s in strategies)
    total_losses = sum(s.losses for s in strategies)
    total = total_wins + total_losses
    ai_win_rate = int((total_wins / total * 100) if total > 0 else 0)

    top3 = sorted(strategies, key=lambda s: (s.wins, getattr(s, 'total_profit', 0)), reverse=True)[:3]
    top3_list = [{"strategy": s.strategy_name, "wins": s.wins, "losses": s.losses, "total_profit": getattr(s, 'total_profit', 0)} for s in top3]

    # Markets success from journal entries
    journals = db.query(models.JournalEntry).filter(models.JournalEntry.user_id == current_user.id).all()
    market_stats = {}
    for j in journals:
        if not j.market:
            continue
        stat = market_stats.setdefault(j.market, {"wins": 0, "total": 0})
        if j.result and str(j.result).lower().startswith('win'):
            stat['wins'] += 1
        stat['total'] += 1

    market_list = []
    for m, v in market_stats.items():
        win_rate = int((v['wins'] / v['total'] * 100) if v['total'] > 0 else 0)
        market_list.append({"market": m, "win_rate": win_rate, "trades": v['total']})

    market_list = sorted(market_list, key=lambda x: x['win_rate'], reverse=True)[:5]

    human_win_rate = int((sum(1 for j in journals if j.result and str(j.result).lower().startswith('win')) / len(journals) * 100) if journals else 0)
    return {
        "human_win_rate": human_win_rate,
        "ai_win_rate": ai_win_rate,
        "best_strategy": top3_list[0]['strategy'] if top3_list else None,
        "total_profit": sum(getattr(s, 'total_profit', 0) for s in strategies),
        "top_strategies": top3_list,
        "top_markets": market_list
    }


def _normalize_result(result_value: str) -> str:
    if not result_value:
        return "pending"
    token = str(result_value).strip().lower()
    if token.startswith("win") or token.startswith("رابح") or token.startswith("ربح"):
        return "win"
    if token.startswith("loss") or token.startswith("خاسر") or token.startswith("خسارة"):
        return "loss"
    return "pending"


def _build_stats(entries):
    total = len(entries)
    wins = len([e for e in entries if _normalize_result(e.result) == "win"])
    losses = len([e for e in entries if _normalize_result(e.result) == "loss"])
    win_rate = int((wins / total * 100) if total > 0 else 0)
    pnl = sum((e.profit_loss or 0) for e in entries)
    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "rate": win_rate,
        "pnl": pnl
    }


def _period_entries(db, user_id, since: datetime):
    return db.query(models.JournalEntry).filter(
        models.JournalEntry.user_id == user_id,
        models.JournalEntry.date >= since
    ).all()

@app.get("/api/stats/today")
def get_today_stats(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    entries = _period_entries(db, current_user.id, today_start)
    stats = _build_stats(entries)
    return {
        "total_trades": stats["total"],
        "wins": stats["wins"],
        "losses": stats["losses"],
        "win_rate": stats["rate"],
        "profit_loss": stats["pnl"]
    }

@app.get("/api/stats/performance")
def get_performance_stats(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    now = datetime.now(timezone.utc)
    weekly = _build_stats(_period_entries(db, current_user.id, now - timedelta(days=7)))
    monthly = _build_stats(_period_entries(db, current_user.id, now - timedelta(days=30)))
    yearly = _build_stats(_period_entries(db, current_user.id, now - timedelta(days=365)))
    return {
        "weekly": weekly,
        "monthly": monthly,
        "yearly": yearly
    }

@app.get("/api/stats/scanner")
def get_scanner_stats(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    alerts = db.query(models.Alert).filter(models.Alert.user_id == current_user.id).all()
    total_opportunities = len(alerts)
    best_market = None
    if total_opportunities > 0:
        market_counts = {}
        for alert in alerts:
            market_counts[alert.market] = market_counts.get(alert.market, 0) + 1
        best_market = max(market_counts.items(), key=lambda item: item[1])[0]

    alert_markets = [alert.market for alert in alerts if alert.market]
    if alert_markets:
        journal_entries = db.query(models.JournalEntry).filter(
            models.JournalEntry.user_id == current_user.id,
            models.JournalEntry.market.in_(alert_markets)
        ).all()
    else:
        journal_entries = []

    wins = len([e for e in journal_entries if _normalize_result(e.result) == "win"])
    losses = len([e for e in journal_entries if _normalize_result(e.result) == "loss"])
    win_rate = int((wins / max(1, wins + losses) * 100)) if wins + losses > 0 else 0

    return {
        "total_opportunities": total_opportunities,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "best_market": best_market
    }

# --- Scanner Control ---
@app.post("/api/scanner/start")
def start_scanner(current_user: models.User = Depends(auth.get_current_user)):
    if not auto_scanner.is_running:
        thread = threading.Thread(target=auto_scanner.start)
        thread.daemon = True
        thread.start()
        return {"status": "started"}
    return {"status": "already running"}

@app.post("/api/scanner/stop")
def stop_scanner(current_user: models.User = Depends(auth.get_current_user)):
    try:
        if not hasattr(auto_scanner, 'stop'):
            raise RuntimeError('Auto-scanner stop method unavailable')
        auto_scanner.stop()
        return {"status": "stopped"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scanner stop failed: {exc}")

@app.get("/api/scanner/status")
def get_scanner_status(current_user: models.User = Depends(auth.get_current_user)):
    return {"is_running": auto_scanner.is_running}

@app.post("/api/strategy/refresh")
def refresh_strategy_performance(current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    summary = internal_brain_service.auto_update_strategy_performance()
    return {"status": "success", "summary": summary}

@app.get("/api/scanner/alerts")
def get_scanner_alerts(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    alerts = db.query(models.Alert).filter(models.Alert.user_id == current_user.id).order_by(models.Alert.created_at.desc()).limit(5).all()
    return [
        {
            "market": a.market,
            "recommendation": a.recommendation,
            "confidence": a.confidence,
            "entry": a.entry,
            "sl": a.sl,
            "tp": a.tp,
            "top_strategies": a.top_strategies,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in alerts
    ]

def _ensure_preferences(db: Session, current_user: models.User):
    prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == current_user.id).first()
    if not prefs:
        prefs = models.UserPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def _serialize_preferences(pref: models.UserPreferences):
    return {
        "theme": pref.theme,
        "language": pref.language,
        "telegram_chat_id": pref.telegram_chat_id,
        "email_notifications": pref.email_notifications,
        "demo_mode": pref.demo_mode,
        "demo_balance": pref.demo_balance,
        "trading_mode": pref.trading_mode,
        "capital": pref.capital,
        "account_balance": pref.account_balance,
        "risk_percentage": pref.risk_percentage,
        "favorite_strategies": json.loads(pref.favorite_strategies or "[]"),
        "watchlist": json.loads(pref.watchlist or "[]"),
        "daily_profit_target_percent": pref.daily_profit_target_percent,
        "daily_loss_limit_percent": pref.daily_loss_limit_percent,
        "trading_locked_today": pref.trading_locked_today,
        "lock_reason": pref.lock_reason,
        "notification_markets": json.loads(pref.notification_markets or "[]"),
        "enable_smart_notifications": pref.enable_smart_notifications,
        "custom_indicators": json.loads(pref.custom_indicators or "[]")
    }


@app.get("/api/user/preferences")
def get_user_preferences(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    prefs = _ensure_preferences(db, current_user)
    return _serialize_preferences(prefs)


@app.post("/api/user/preferences")
def update_user_preferences(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    prefs = _ensure_preferences(db, current_user)
    if "theme" in payload:
        prefs.theme = payload["theme"]
    if "language" in payload:
        prefs.language = payload["language"]
    if "telegram_chat_id" in payload:
        prefs.telegram_chat_id = payload["telegram_chat_id"]
    if "email_notifications" in payload:
        prefs.email_notifications = bool(payload["email_notifications"])
    if "demo_mode" in payload:
        prefs.demo_mode = bool(payload["demo_mode"])
    if "demo_balance" in payload:
        prefs.demo_balance = float(payload["demo_balance"])
    if "trading_mode" in payload:
        prefs.trading_mode = payload["trading_mode"]
    if "capital" in payload:
        prefs.capital = float(payload["capital"])
    if "account_balance" in payload:
        prefs.account_balance = float(payload["account_balance"])
    if "risk_percentage" in payload:
        prefs.risk_percentage = float(payload["risk_percentage"])
    if "favorite_strategies" in payload:
        favorites = payload["favorite_strategies"] or []
        if len(favorites) > 5:
            raise HTTPException(status_code=400, detail="يمكن اختيار حتى 5 استراتيجيات مفضلة فقط.")
        prefs.favorite_strategies = json.dumps(favorites)
    if "watchlist" in payload:
        prefs.watchlist = json.dumps(payload["watchlist"] or [])
    if "daily_profit_target_percent" in payload:
        prefs.daily_profit_target_percent = float(payload["daily_profit_target_percent"])
    if "daily_loss_limit_percent" in payload:
        prefs.daily_loss_limit_percent = float(payload["daily_loss_limit_percent"])
    if "notification_markets" in payload:
        prefs.notification_markets = json.dumps(payload["notification_markets"] or [])
    if "enable_smart_notifications" in payload:
        prefs.enable_smart_notifications = bool(payload["enable_smart_notifications"])
    if "custom_indicators" in payload:
        prefs.custom_indicators = json.dumps(payload["custom_indicators"] or [])
    db.commit()
    db.refresh(prefs)
    return _serialize_preferences(prefs)


@app.get("/api/user/favorites")
def get_user_favorites(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    prefs = _ensure_preferences(db, current_user)
    return json.loads(prefs.favorite_strategies or "[]")


@app.post("/api/user/favorites")
def add_user_favorite(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    strategy = (payload.get("strategy") or "").strip()
    if not strategy:
        raise HTTPException(status_code=400, detail="استراتيجية مطلوبة")

    prefs = _ensure_preferences(db, current_user)
    favorites = json.loads(prefs.favorite_strategies or "[]")
    if strategy in favorites:
        return favorites
    if len(favorites) >= 5:
        raise HTTPException(status_code=400, detail="يمكن اختيار حتى 5 استراتيجيات مفضلة فقط.")
    favorites.append(strategy)
    prefs.favorite_strategies = json.dumps(favorites)
    db.commit()
    db.refresh(prefs)
    return favorites


@app.post("/api/user/favorites/remove")
def remove_user_favorite(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    strategy = (payload.get("strategy") or "").strip()
    if not strategy:
        raise HTTPException(status_code=400, detail="استراتيجية مطلوبة")

    prefs = _ensure_preferences(db, current_user)
    favorites = json.loads(prefs.favorite_strategies or "[]")
    favorites = [item for item in favorites if item != strategy]
    prefs.favorite_strategies = json.dumps(favorites)
    db.commit()
    db.refresh(prefs)
    return favorites


@app.post("/api/analysis/draft")
def save_analysis_draft(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not payload:
        raise HTTPException(status_code=400, detail="البيانات مطلوبة لحفظ المسودة")
    market = payload.get("market") or "UNKNOWN"
    draft = db.query(models.DraftAnalysis).filter(models.DraftAnalysis.user_id == current_user.id, models.DraftAnalysis.market == market).first()
    if not draft:
        draft = models.DraftAnalysis(
            user_id=current_user.id,
            market=market,
            image_path=payload.get("image_path"),
            description=payload.get("description", ""),
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(draft)
    else:
        draft.image_path = payload.get("image_path", draft.image_path)
        draft.description = payload.get("description", draft.description)
        draft.payload_json = json.dumps(payload, ensure_ascii=False)
        draft.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(draft)
    return {"status": "saved", "draft_id": draft.id}


@app.get("/api/analysis/drafts")
def list_analysis_drafts(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    drafts = db.query(models.DraftAnalysis).filter(models.DraftAnalysis.user_id == current_user.id).order_by(models.DraftAnalysis.updated_at.desc()).all()
    return [
        {
            "id": d.id,
            "market": d.market,
            "description": d.description,
            "payload": json.loads(d.payload_json or "{}"),
            "updated_at": d.updated_at.isoformat() if d.updated_at else None
        }
        for d in drafts
    ]


@app.get("/api/journal/export")
def export_journal_csv(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    entries = db.query(models.JournalEntry).filter(models.JournalEntry.user_id == current_user.id).order_by(models.JournalEntry.date.desc()).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["التاريخ", "الزوج", "التوصية", "الثقة", "النتيجة", "الربح/الخسارة"])
    for entry in entries:
        row_date = entry.date.isoformat() if entry.date else ""
        confidence = entry.confidence if getattr(entry, 'confidence', None) is not None else 'N/A'
        writer.writerow([
            row_date,
            entry.market or "",
            entry.recommendation or "",
            confidence,
            entry.result or "",
            f"{(entry.profit_loss or 0):.2f}"
        ])
    payload = "\ufeff" + buffer.getvalue()
    return Response(payload, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=journal_history.csv"})


@app.get("/api/admin/system-health")
def get_system_health(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    uptime = datetime.now(timezone.utc) - SYSTEM_METRICS["start_time"]
    cpu_percent = psutil.cpu_percent(interval=0.5) if PSUTIL_AVAILABLE else None
    ram_info = psutil.virtual_memory() if PSUTIL_AVAILABLE else None
    return {
        "status": "online",
        "cpu_percent": cpu_percent,
        "ram_percent": ram_info.percent if ram_info else None,
        "ram_used": ram_info.used if ram_info else None,
        "ram_total": ram_info.total if ram_info else None,
        "gemini_calls": SYSTEM_METRICS["gemini_calls"],
        "deepseek_calls": SYSTEM_METRICS["deepseek_calls"],
        "request_count": SYSTEM_METRICS["request_count"],
        "daily_requests": SYSTEM_METRICS["daily_requests"],
        "last_error": SYSTEM_METRICS["last_error"],
        "uptime_seconds": int(uptime.total_seconds()),
        "uptime": str(uptime).split('.')[0]
    }

@app.get("/api/system/health-details")
def get_system_health_details(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    health = ai_core_service.get_system_health()
    return {
        "status": "ok",
        "system_health": health,
        "request_count": SYSTEM_METRICS["request_count"],
        "daily_requests": SYSTEM_METRICS["daily_requests"],
        "last_error": SYSTEM_METRICS["last_error"],
    }

@app.get("/api/recommendation/quick/{market}")
def get_quick_recommendation(market: str, current_user: models.User = Depends(auth.get_current_user)):
    recommendation = ai_core_service.smart_recommendation(market.upper(), current_user.id)
    return recommendation

@app.post("/api/markets/compare")
def compare_markets(payload: dict):
    markets = payload.get("markets") if isinstance(payload.get("markets"), list) else []
    if not markets:
        raise HTTPException(status_code=400, detail="Provide a markets list to compare.")
    return ai_core_service.compare_markets(markets)

@app.post("/api/system/tune-weights")
def tune_system_weights(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    summary = ai_core_service.auto_tune_weights()
    return {"status": "ok", "tuning_summary": summary}

@app.get("/api/user/watchlist")
def get_watchlist(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    prefs = _ensure_preferences(db, current_user)
    return json.loads(prefs.watchlist or "[]")


@app.post("/api/user/watchlist/add")
def add_watchlist_item(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    symbol = (payload.get("symbol") or "").strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
    prefs = _ensure_preferences(db, current_user)
    current_list = json.loads(prefs.watchlist or "[]")
    if symbol not in current_list:
        if len(current_list) >= 10:
            raise HTTPException(status_code=400, detail="Watchlist limit is 10 symbols")
        current_list.append(symbol)
        prefs.watchlist = json.dumps(current_list)
        db.commit()
        db.refresh(prefs)
    return json.loads(prefs.watchlist or "[]")


@app.post("/api/user/watchlist/remove")
def remove_watchlist_item(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    symbol = (payload.get("symbol") or "").strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
    prefs = _ensure_preferences(db, current_user)
    current_list = json.loads(prefs.watchlist or "[]")
    if symbol in current_list:
        current_list = [item for item in current_list if item != symbol]
        prefs.watchlist = json.dumps(current_list)
        db.commit()
        db.refresh(prefs)
    return json.loads(prefs.watchlist or "[]")


@app.get("/api/reports/daily")
def get_daily_reports(days: int = 7, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    report_rows = db.query(models.DailyReport).filter(models.DailyReport.user_id == current_user.id).order_by(models.DailyReport.report_date.desc()).limit(days).all()
    return [
        {
            "report_date": report.report_date.isoformat(),
            "summary": report.summary,
            "total_trades": report.total_trades,
            "entered_trades": report.entered_trades,
            "wins": report.wins,
            "losses": report.losses,
            "profit_loss": report.profit_loss,
            "sent_to_telegram": report.sent_to_telegram
        }
        for report in report_rows
    ]


@app.post("/api/reports/daily/generate")
def generate_daily_report(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    today = datetime.now(timezone.utc).date()
    entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.user_id == current_user.id,
        models.JournalEntry.date >= datetime(today.year, today.month, today.day)
    ).all()
    total_trades = len(entries)
    wins = len([e for e in entries if _normalize_result(e.result) == "win"])
    losses = len([e for e in entries if _normalize_result(e.result) == "loss"])
    pnl = sum((e.profit_loss or 0) for e in entries)
    summary = (
        f"اليوم: {total_trades} صفقات، {wins} رابحة، {losses} خاسرة، ربح/خسارة {pnl:.2f}$"
    )
    report = db.query(models.DailyReport).filter(
        models.DailyReport.user_id == current_user.id,
        models.DailyReport.report_date == today
    ).first()
    if not report:
        report = models.DailyReport(
            user_id=current_user.id,
            report_date=today,
            summary=summary,
            total_trades=total_trades,
            entered_trades=total_trades,
            wins=wins,
            losses=losses,
            profit_loss=pnl,
        )
        db.add(report)
    else:
        report.summary = summary
        report.total_trades = total_trades
        report.entered_trades = total_trades
        report.wins = wins
        report.losses = losses
        report.profit_loss = pnl
        report.created_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return {
        "report_date": report.report_date.isoformat(),
        "summary": report.summary,
        "total_trades": report.total_trades,
        "entered_trades": report.entered_trades,
        "wins": report.wins,
        "losses": report.losses,
        "profit_loss": report.profit_loss,
        "sent_to_telegram": report.sent_to_telegram
    }


@app.post("/api/reports/daily/send-telegram")
def send_daily_report_to_telegram(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    prefs = _ensure_preferences(db, current_user)
    if not prefs.telegram_chat_id:
        raise HTTPException(status_code=400, detail="Telegram chat ID is not configured.")
    report = db.query(models.DailyReport).filter(
        models.DailyReport.user_id == current_user.id,
    ).order_by(models.DailyReport.report_date.desc()).first()
    if not report:
        raise HTTPException(status_code=404, detail="No daily report available. Generate it first.")

    message = (
        f"📅 تقرير يومي لـ VisionTrader AI\n"
        f"التاريخ: {report.report_date.isoformat()}\n"
        f"الصفقات: {report.total_trades}\n"
        f"الرابحة: {report.wins}\n"
        f"الخاسرة: {report.losses}\n"
        f"PnL: {report.profit_loss:.2f}$\n"
        f"{report.summary}"
    )
    telegram_service.send_message(prefs.telegram_chat_id, message)
    report.sent_to_telegram = True
    db.commit()
    return {"status": "sent", "report_date": report.report_date.isoformat()}


@app.get("/api/account/summary")
def account_summary(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    prefs = _ensure_preferences(db, current_user)
    today = datetime.now(timezone.utc).date()
    today_report = db.query(models.DailyReport).filter(
        models.DailyReport.user_id == current_user.id,
        models.DailyReport.report_date == today
    ).first()
    return {
        "email": current_user.email,
        "account_balance": prefs.demo_balance if prefs.demo_mode else prefs.account_balance,
        "demo_mode": prefs.demo_mode,
        "trading_mode": prefs.trading_mode,
        "watchlist": json.loads(prefs.watchlist or "[]"),
        "daily_report": {
            "report_date": today_report.report_date.isoformat() if today_report else None,
            "summary": today_report.summary if today_report else None,
            "profit_loss": today_report.profit_loss if today_report else 0.0
        },
        "trial_status": {
            "active": bool(current_user.trial_start and current_user.trial_end and datetime.now(timezone.utc) < current_user.trial_end),
            "ends_at": current_user.trial_end.isoformat() if current_user.trial_end else None
        }
    }

@app.get("/api/deep-market/scan")
def deep_market_scan(symbol: str = "XAUUSDT", current_user: models.User = Depends(auth.get_current_user)):
    SYSTEM_METRICS["deepseek_calls"] += 1
    return deep_market_scanner.scan_market(symbol)

@app.get("/api/scanner/top-opportunities")
def get_top_opportunities(current_user: models.User = Depends(auth.get_current_user)):
    return auto_scanner.get_top_opportunities()

@app.get("/api/binance/scan")
def binance_scan(symbol: str = "BTCUSDT", current_user: models.User = Depends(auth.get_current_user)):
    return binance_service.scan(symbol)

@app.post("/api/tradingview/fetch")
def tradingview_fetch(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="TradingView URL is required")
    SYSTEM_METRICS["gemini_calls"] += 1
    return tradingview_service.fetch_and_analyze(url)


@app.get("/api/debug/integration")
def debug_integration():
    """Return minimal integration status for local testing.

    - Whether shared websocket is attached
    - Subset of symbols and their cumulative delta (if available)
    - List of registered agent names
    """
    try:
        import services.binance_service as bin_mod
        ws = getattr(bin_mod.binance_service, "ws_service", None)
        ws_present = ws is not None
        symbols = getattr(ws, "symbols", []) if ws_present else []
        sample = {}
        if ws_present and hasattr(ws, 'get_live_data'):
            for s in symbols[:8]:
                try:
                    d = ws.get_live_data(s) or {}
                    sample[s] = {
                        "cumulative_delta": d.get("cumulative_delta"),
                        "price": d.get("price")
                    }
                except Exception:
                    sample[s] = None
    except Exception:
        ws_present = False
        symbols = []
        sample = {}

    try:
        from services.agent_manager import AgentManager
        mgr = AgentManager()
        agent_names = [a.name for a in mgr.agents]
    except Exception:
        agent_names = []

    return {
        "ws_attached": ws_present,
        "symbols": symbols,
        "sample_live": sample,
        "agents": agent_names
    }


# === نظام تتبع الصفقات الحية ===

@app.get("/api/trade/active")
def get_active_trades(current_user: models.User = Depends(auth.get_current_user)):
    """الحصول على الصفقات المفتوحة مع الربح/الخسارة الحي"""
    trades = trade_manager_service.get_active_trades(user_id=current_user.id)
    return {"active_trades": trades}

@app.get("/api/trade/history")
def get_trade_history(limit: int = 20, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """الحصول على آخر 20 صفقة مع تقاريرها الكاملة"""
    entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.user_id == current_user.id
    ).order_by(models.JournalEntry.date.desc()).limit(limit).all()

    history = []
    for entry in entries:
        # الحصول على TradeExperience المرتبطة
        entry_price = getattr(entry, 'entry_price', None)
        exit_price = getattr(entry, 'exit_price', None)
        experience = None
        if entry_price is not None and exit_price is not None:
            experience = db.query(models.TradeExperience).filter(
                models.TradeExperience.user_id == current_user.id,
                models.TradeExperience.market == entry.market,
                models.TradeExperience.entry_price == entry_price,
                models.TradeExperience.exit_price == exit_price
            ).first()

        history.append({
            "id": entry.id,
            "date": entry.date.isoformat() if entry.date else None,
            "market": getattr(entry, 'market', None),
            "recommendation": getattr(entry, 'recommendation', None),
            "result": getattr(entry, 'result', None),
            "profit_loss": getattr(entry, 'profit_loss', None),
            "notes": getattr(entry, 'notes', None),
            "strategies": getattr(entry, 'strategies', None),
            "duration": getattr(entry, 'duration', None),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "stop_loss": getattr(entry, 'stop_loss', None),
            "take_profit": getattr(entry, 'take_profit', None),
            "confidence": getattr(entry, 'confidence', None),
            "experience": {
                "lessons": getattr(experience, 'lessons', None),
                "strategies_correct": getattr(experience, 'strategies', None),
            } if experience else None
        })

    return {"trade_history": history}


@app.post("/api/trade/start-monitoring")
def start_trade_monitoring(current_user: models.User = Depends(auth.get_current_user)):
    """بدء مراقبة الصفقات الحية"""
    trade_manager_service.start_live_monitoring()
    return {"status": "monitoring_started"}

@app.post("/api/trade/stop-monitoring")
def stop_trade_monitoring(current_user: models.User = Depends(auth.get_current_user)):
    """إيقاف مراقبة الصفقات الحية"""
    trade_manager_service.stop_live_monitoring()
    return {"status": "monitoring_stopped"}

@app.post("/api/trade/add-active")
def add_active_trade(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    """إضافة صفقة نشطة للتتبع (للاختبار أو الإدخال اليدوي)"""
    required_fields = ["trade_id", "market", "direction", "entry_price", "stop_loss", "take_profits", "position_size"]
    for field in required_fields:
        if field not in payload:
            raise HTTPException(status_code=400, detail=f"Field {field} is required")

    trade_manager_service.add_active_trade(
        trade_id=payload["trade_id"],
        user_id=current_user.id,
        market=payload["market"],
        direction=payload["direction"],
        entry_price=payload["entry_price"],
        stop_loss=payload["stop_loss"],
        take_profits=payload["take_profits"],
        position_size=payload["position_size"],
        entry_time=datetime.now(timezone.utc)
    )
    return {"status": "trade_added", "trade_id": payload["trade_id"]}

@app.post("/api/trade/remove-active")
def remove_active_trade(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    """إزالة صفقة من التتبع"""
    trade_id = payload.get("trade_id")
    if not trade_id:
        raise HTTPException(status_code=400, detail="trade_id is required")

    trade_manager_service.remove_active_trade(trade_id)
    return {"status": "trade_removed", "trade_id": trade_id}


# === نظام النبض والشخصية ===

@app.get("/api/system/pulse")
def get_system_pulse():
    """نبض النظام - حالة عامة للاختبار"""
    try:
        health = ai_core_service.get_system_health()
    except Exception:
        health = {
            "active_strategies": 0,
            "overall_system_win_rate": 0.0,
            "total_performance_records": 0,
            "memory_entries": 0,
            "external_api_state": {"binance": "failed", "tradingview": "missing_api_key", "deepseek": "missing_api_key"},
            "last_auto_tune": None,
            "last_cluster_tune": None,
            "last_monthly_review": None,
            "cluster_weights": {"power": 0.0, "geometric": 0.0, "momentum": 0.0},
            "judge_performance": {"total_decisions": 0, "correct_decisions": 0, "accuracy_rate": 0.0, "confidence_threshold": 60, "last_adjustment": None},
            "disabled_strategies": {"active_disabled": {}, "expired_and_reenabled": []},
            "trade_counter": 0,
            "strategy_weights_summary": {"total_strategies": 0, "weight_distribution": {"high": 0, "medium": 0, "low": 0}}
        }

    return {
        "status": "online",
        "refresh_time": datetime.now(timezone.utc).isoformat(),
        "active_strategies": health.get("active_strategies", 0),
        "system_healthy": health.get("overall_system_win_rate", 0) > 55,
        "health_details": health
    }

@app.get("/api/system/strategies")
def get_system_strategies(current_user: models.User = Depends(auth.get_current_user)):
    """قائمة الاستراتيجيات مع الأداء مرتبة من الأفضل للأسوأ"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    try:
        from .voting_engine import strategy_loader
    except:
        strategy_loader = None

    db = SessionLocal()
    try:
        strategy_records = db.query(models.StrategyPerformance).all()
        strategy_stats = {}

        for record in strategy_records:
            total_trades = (record.wins or 0) + (record.losses or 0)
            if total_trades >= 5:  # Minimum trades for meaningful stats
                win_rate = (record.wins or 0) / total_trades
                strategy_stats[record.strategy_name] = {
                    "win_rate": round(win_rate * 100, 1),
                    "total_trades": total_trades,
                    "wins": record.wins or 0,
                    "losses": record.losses or 0,
                    "last_updated": record.last_updated.isoformat() if record.last_updated else None
                }

        # Sort by win rate descending
        sorted_strategies = sorted(strategy_stats.items(), key=lambda x: x[1]["win_rate"], reverse=True)

        return {
            "strategies": [
                {
                    "name": name,
                    "win_rate": stats["win_rate"],
                    "total_trades": stats["total_trades"],
                    "wins": stats["wins"],
                    "losses": stats["losses"],
                    "last_updated": stats["last_updated"]
                }
                for name, stats in sorted_strategies
            ],
            "total_strategies": len(sorted_strategies)
        }

    finally:
        db.close()

@app.get("/api/system/personality")
def get_system_personality():
    """شخصية النظام الحالية"""
    weights = {}
    try:
        weights = ai_core_service.internal_brain.get_strategy_weights()
    except Exception:
        weights = {}
    sorted_strategies = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    top_strategies = [name for name, _ in sorted_strategies[:5]]

    return {
        "current_mode": "DAY_TRADING",
        "description": "الوضع الافتراضي للنظام للأختبار.",
        "favorite_strategies": top_strategies,
        "strengths": ["تحليل البيانات", "التركيز على السيولة", "المرونة"],
        "weaknesses": ["الأسواق الجانبية", "الأحداث غير المتوقعة"],
        "beliefs": ["الاتجاه صديقي", "السيولة تكشف القمم", "التعلم المستمر"],
        "performance_summary": {
            "win_rate": 0,
            "active_strategies": len(top_strategies),
            "memory_entries": 0
        }
    }

@app.post("/api/system/feedback")
def submit_system_feedback(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    """المستخدم يصحح للنظام"""
    trade_id = payload.get("trade_id")
    analysis_id = payload.get("analysis_id")
    correction = payload.get("correction", "").strip()

    if not correction or (not trade_id and not analysis_id):
        raise HTTPException(status_code=400, detail="trade_id or analysis_id and correction are required")

    result = ai_core_service.learn_from_feedback(trade_id=trade_id, analysis_id=analysis_id, correction=correction)
    return result

@app.post("/api/system/tune-weights")
def manual_tune_weights(current_user: models.User = Depends(auth.get_current_user)):
    """تشغيل auto_tune_weights يدوياً (Admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    result = ai_core_service.auto_tune_weights()
    return result

@app.get("/api/recommendation/quick/{market}")
def get_quick_recommendation(market: str, current_user: models.User = Depends(auth.get_current_user)):
    """توصية سريعة للموبايل"""
    recommendation = ai_core_service.smart_recommendation(market.upper(), current_user.id)
    return recommendation

@app.post("/api/markets/compare")
def compare_markets(payload: dict):
    """مقارنة الأسواق وترتيبها"""
    markets = payload.get("markets", [])
    if not markets or len(markets) > 10:
        raise HTTPException(status_code=400, detail="Provide 1-10 markets to compare")

    result = ai_core_service.compare_markets(markets)
    return result


@app.on_event("startup")
async def startup_event():
    """أحداث بدء الخادم"""
    # بدء مراقبة الصفقات الحية
    trade_manager_service.start_live_monitoring()
    print("✅ تم بدء مراقبة الصفقات الحية")

@app.get("/api/calendar/events")
def calendar_events(hours: int = 24, current_user: models.User = Depends(auth.get_current_user)):
    return calendar_service.get_upcoming_events(hours=hours)

@app.get("/api/calendar/high-impact")
def calendar_high_impact(minutes: int = 15, current_user: models.User = Depends(auth.get_current_user)):
    return calendar_service.get_high_impact_soon(minutes=minutes)

@app.post("/api/backtest/run")
def run_backtest(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    market = payload.get("market")
    timeframe = payload.get("timeframe")
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")
    if not market or not start_date or not end_date:
        raise HTTPException(status_code=400, detail="market, start_date, and end_date are required")

    try:
        report = backtest_engine.run_backtest(
            market=market,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=float(payload.get("initial_capital", 10000.0)),
            simulations=int(payload.get("simulations", 1000)),
            n_windows=int(payload.get("n_windows", 5)),
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# --- New Features 2.0 ---
@app.post("/api/voice/command")
async def voice_command(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    return {"response": voice_service.process_command(payload.get("command", ""))}

@app.get("/api/broker/audit")
async def broker_audit(current_user: models.User = Depends(auth.get_current_user)):
    return broker_auditor.get_audit_report(user_id=current_user.id)

@app.post("/api/smart-orders/create")
async def create_smart_order(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    if payload.get("type") == "zone":
        return smart_orders_service.create_zone_order(payload['market'], payload['start'], payload['end'], payload['lot'])
    return {"status": "Order type not supported"}

@app.post("/api/trade/plan")
def plan_trade(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    protection = trade_protection_service.check_protection(current_user.id)
    if protection.get("trading_locked"):
        raise HTTPException(status_code=403, detail=protection.get("trading_message") or "التداول مغلق مؤقتاً.")

    warning = trade_protection_service.correlation_warning(current_user.id, payload.get("market"))
    strategy_signals = payload.get("analysis_context", {}).get("strategy_signals") or payload.get("strategy_signals")
    strategy_clash = market_protection_service.detect_strategy_clash(strategy_signals)
    session_info = market_protection_service.get_current_session()

    if strategy_clash.get("reject"):
        return {
            "status": "rejected",
            "reason": strategy_clash.get("message"),
            "strategy_clash": strategy_clash,
            "session_info": session_info,
            "protection_status": protection,
            "correlation_warning": warning if warning else None,
        }

    plan = trade_manager_service.plan_trade(
        user_id=current_user.id,
        recommendation=payload.get("recommendation", ""),
        current_price=payload.get("current_price"),
        stop_loss=payload.get("stop_loss"),
        take_profit=payload.get("take_profit"),
        confidence=int(payload.get("confidence", 50)),
        account_balance=float(payload.get("account_balance", 100000.0)),
        base_risk_percent=float(payload.get("risk_percent", 2.0)),
        analysis_context=payload.get("analysis_context", {}),
    )

    if warning:
        plan["correlation_warning"] = warning
    plan = market_protection_service.apply_session_adjustment(plan, session_info)
    plan["strategy_clash"] = strategy_clash
    plan["session_info"] = session_info
    plan["protection_status"] = protection
    return plan

@app.get("/api/market/session")
def get_market_session(current_user: models.User = Depends(auth.get_current_user)):
    return market_protection_service.get_current_session()

@app.get("/api/market/spread")
def get_market_spread(current_user: models.User = Depends(auth.get_current_user)):
    return market_protection_service.get_spread_report()


def _format_binance_symbol(symbol: str) -> str:
    if not symbol:
        return ""
    normalized = re.sub(r'[^A-Z0-9]', '', symbol.upper())
    if normalized.endswith("USD") and not normalized.endswith("USDT") and len(normalized) > 3:
        normalized = normalized[:-3] + "USDT"
    return normalized


def _format_twelvedata_symbol(symbol: str) -> str:
    if not symbol:
        return ""
    normalized = symbol.strip().upper().replace('_', '/').replace('-', '/').replace(':', '/')
    if normalized.endswith('USDT'):
        normalized = normalized[:-4] + '/USD'
    elif normalized.endswith('USD') and not normalized.endswith('/USD'):
        normalized = normalized[:-3] + '/USD'
    elif '/' not in normalized and len(normalized) > 3:
        normalized = normalized[:-3] + '/USD'
    return normalized


@app.get("/api/market/price")
def get_market_price(symbol: str = "BTCUSDT"):
    symbol = (symbol or "BTCUSDT").strip().upper()
    binance_symbol = _format_binance_symbol(symbol)
    twelvedata_symbol = _format_twelvedata_symbol(symbol)
    binance_price = 0.0
    twelvedata_price = None
    binance_status = "skipped"
    twelvedata_status = "failed"

    # For metals and major FX pairs, prefer TwelveData / TradingView (do NOT use Binance)
    fx_and_metals = {"XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY"}
    normalized = symbol.replace('/', '').replace('-', '').replace('_', '').upper()

    if normalized in fx_and_metals:
        binance_status = "skipped"

        # Try TradingView/TwelveData first (isolate exceptions)
        price = None
        try:
            if twelvedata_symbol:
                price = tradingview_service.get_symbol_price(twelvedata_symbol)
        except Exception:
            price = None

        if price is not None:
            twelvedata_price = float(price)
            twelvedata_status = 'ok'
        else:
            # Fallback to Yahoo via yfinance then JSON API
            y_price = None
            try:
                try:
                    import yfinance as yf
                except Exception:
                    yf = None

                if yf:
                    yahoo_candidates = ['XAUUSD=X', 'GC=F'] if 'XAU' in normalized else (['XAGUSD=X', 'SI=F'] if 'XAG' in normalized else [normalized + '=X'])
                    for t in yahoo_candidates:
                        try:
                            tk = yf.Ticker(t)
                            hist = None
                            try:
                                hist = tk.history(period='1d', interval='1m')
                            except Exception:
                                hist = None
                            if hist is not None and not hist.empty:
                                y_price = float(hist['Close'].iloc[-1])
                                break
                            info_price = None
                            try:
                                if hasattr(tk, 'info') and isinstance(tk.info, dict):
                                    info_price = tk.info.get('regularMarketPrice')
                            except Exception:
                                info_price = None
                            if info_price:
                                y_price = float(info_price)
                                break
                        except Exception:
                            continue
            except Exception:
                y_price = None

            if y_price is None:
                try:
                    q = urllib.parse.quote(twelvedata_symbol or normalized, safe='')
                    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={q}"
                    resp = requests.get(url, timeout=8)
                    resp.raise_for_status()
                    body = resp.json()
                    results = body.get('quoteResponse', {}).get('result', [])
                    if results:
                        item = results[0]
                        p = item.get('regularMarketPrice') or item.get('bid') or item.get('ask') or item.get('lastPrice')
                        if p is not None:
                            y_price = float(p)
                except Exception:
                    y_price = None

            if y_price is not None:
                twelvedata_price = float(y_price)
                twelvedata_status = 'ok'
            else:
                # Safe static fallback for gold
                if normalized == 'XAUUSD':
                    twelvedata_price = 4320.0
                    twelvedata_status = 'fallback_estimate'
                else:
                    twelvedata_status = 'no_data'
    else:
        # Use Binance for crypto and keep TwelveData/TradingView as a fallback
        try:
            if binance_symbol:
                price = binance_service.get_ticker_price(binance_symbol)
                if price is not None:
                    binance_price = float(price)
                    binance_status = 'ok' if binance_price > 0 else 'no_data'
                else:
                    binance_status = 'no_data'
        except Exception:
            binance_status = 'failed'

        try:
            if twelvedata_symbol:
                price = tradingview_service.get_symbol_price(twelvedata_symbol)
                if price is not None:
                    twelvedata_price = float(price)
                    twelvedata_status = 'ok'
                else:
                    twelvedata_status = 'no_data'
        except Exception:
            twelvedata_status = 'failed'

    price_diff_pct = None
    if twelvedata_price is not None and binance_price:
        try:
            price_diff_pct = round(abs(binance_price - twelvedata_price) / max(abs(binance_price), 1) * 100, 3)
        except Exception:
            price_diff_pct = None

    return {
        "symbol": symbol,
        "binance_symbol": binance_symbol,
        "twelvedata_symbol": twelvedata_symbol,
        "binance_price": binance_price,
        "twelvedata_price": twelvedata_price,
        "binance_status": binance_status,
        "twelvedata_status": twelvedata_status,
        "price_diff_pct": price_diff_pct,
    }


@app.get("/api/price-alerts")
def get_price_alerts(current_user: models.User = Depends(auth.get_current_user)):
    return market_protection_service.list_price_alerts(current_user.id)

@app.post("/api/price-alerts")
def create_price_alert(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    try:
        alert = market_protection_service.create_price_alert(
            user_id=current_user.id,
            market=payload.get("market"),
            target_price=float(payload.get("target_price")),
            direction=payload.get("direction")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return alert

@app.post("/api/price-alerts/delete")
def delete_price_alert(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    if not payload.get("id"):
        raise HTTPException(status_code=400, detail="Alert id required")
    success = market_protection_service.delete_price_alert(current_user.id, int(payload.get("id")))
    if not success:
        raise HTTPException(status_code=404, detail="Price alert not found")
    return {"status": "deleted"}

@app.post("/api/journal/quick-entry")
def quick_journal_entry(payload: dict, current_user: models.User = Depends(auth.get_current_user)):
    def parse_float(value, default=None):
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    protection = trade_protection_service.check_protection(current_user.id)
    if protection.get("trading_locked"):
        raise HTTPException(status_code=403, detail=protection.get("trading_message") or "التداول مغلق مؤقتاً.")

    try:
        recommendation = payload.get("recommendation") or payload.get("direction") or ""
        result = market_protection_service.quick_trade_entry(
            user_id=current_user.id,
            market=payload.get("market"),
            recommendation=recommendation,
            entry_price=parse_float(payload.get("entry_price") or payload.get("entry"), 0.0),
            stop_loss=parse_float(payload.get("stop_loss"), None),
            take_profit=parse_float(payload.get("take_profit"), None),
            expected_price=parse_float(payload.get("expected_price"), None),
            notes=payload.get("notes")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "result": result, "protection_status": protection}

@app.get("/api/sentiment/scan")
async def sentiment_scan(symbol: str, current_user: models.User = Depends(auth.get_current_user)):
    if social_sentiment_service is None:
        return {
            "symbol": symbol,
            "sentiment": "unavailable",
            "detail": "Social sentiment service is disabled in this deployment."
        }
    return social_sentiment_service.analyze(symbol)

@app.get("/api/psychology/report")
def get_psych_report(current_user: models.User = Depends(auth.get_current_user)):
    return {"report": journal_service.generate_psych_report(user_id=current_user.id)}

@app.post("/api/shadow/trade")
def open_shadow_trade(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    protection = trade_protection_service.check_protection(current_user.id)
    if protection.get("trading_locked"):
        raise HTTPException(status_code=403, detail=protection.get("trading_message") or "التداول مغلق مؤقتاً.")

    market = payload.get('market')
    price = payload.get('price')
    if not market or price is None:
        raise HTTPException(status_code=400, detail='market and price are required')

    warning = trade_protection_service.correlation_warning(current_user.id, market)
    st = ShadowTrader(user_id=current_user.id)
    trade = st.open_trade(market, price, payload.get('sl'), payload.get('tp'))
    response = {"trade": trade}
    if warning:
        response["correlation_warning"] = warning

    if payload.get('expected_price') is not None:
        slippage = market_protection_service.record_slippage(
            user_id=current_user.id,
            market=market,
            expected_price=float(payload.get('expected_price')),
            executed_price=float(price),
            trade_id=trade.id
        )
        response['slippage'] = slippage

    response["protection_status"] = protection
    return response


@app.get('/api/shadow/stats')
def get_shadow_stats(current_user: models.User = Depends(auth.get_current_user)):
    st = ShadowTrader(user_id=current_user.id)
    stats = st.get_shadow_stats()
    return {'status': 'ok', 'stats': stats}


@app.get('/api/shadow/list')
def get_shadow_list(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    trades = db.query(models.ShadowTrade).filter(models.ShadowTrade.user_id == current_user.id).order_by(models.ShadowTrade.created_at.desc()).limit(200).all()
    return {'status': 'ok', 'trades': [{'id': t.id, 'market': t.market, 'entry_price': t.entry_price, 'exit_price': t.exit_price, 'status': t.status, 'pnl': t.pnl, 'created_at': t.created_at} for t in trades]}

@app.get("/api/protection/status")
def protection_status(current_user: models.User = Depends(auth.get_current_user)):
    return trade_protection_service.refresh_protection(current_user.id)


@app.get("/api/trade-mover/check")
def check_trade_mover(analysis_id: int, current_price: Optional[float] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id, models.Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        analysis_data = json.loads(analysis.result_json or '{}')
    except Exception:
        analysis_data = {}

    suggestion = trade_mover_service.suggest(analysis_data, current_price)
    suggestion.update({
        'analysis_id': analysis_id,
        'market': analysis.market,
        'analysis_description': analysis.description,
        'last_updated': analysis.created_at.isoformat() if analysis.created_at else None
    })
    return suggestion

# --- New Features 25-29 ---
@app.get("/api/trade/confidence")
def get_trade_confidence(analysis_id: Optional[int] = None, market: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if analysis_id:
        analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id, models.Analysis.user_id == current_user.id).first()
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        try:
            result = json.loads(analysis.result_json or '{}')
            confidence = result.get('confidence', 50)
        except:
            confidence = 50
    else:
        # Default or calculate based on market
        confidence = 50

    if confidence >= 80:
        color = "green"
        status = "ممتازة"
    elif confidence >= 60:
        color = "yellow"
        status = "جيدة"
    else:
        color = "red"
        status = "لا تدخل"

    return {
        "confidence": confidence,
        "color": color,
        "status": status,
        "message": f"ثقة الصفقة: {confidence}% {status}"
    }

@app.get("/api/market/countdown")
def get_market_countdown(current_user: models.User = Depends(auth.get_current_user)):
    from datetime import datetime, time
    now = datetime.now(timezone.utc)
    # Simplified market hours (example for forex)
    # New York: 13:30-20:00 UTC
    ny_open = time(13, 30)
    ny_close = time(20, 0)
    # London: 07:00-16:00 UTC
    london_open = time(7, 0)
    london_close = time(16, 0)

    def time_until(target_time):
        target = datetime.combine(now.date(), target_time)
        if target < now:
            target = datetime.combine(now.date() + timedelta(days=1), target_time)
        delta = target - now
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return hours, minutes

    ny_hours, ny_mins = time_until(ny_open if now.time() > ny_close else ny_close)
    london_hours, london_mins = time_until(london_open if now.time() > london_close else london_close)

    if now.time() < london_open:
        status = "مغلق"
        next_open = "لندن"
        hours, mins = london_hours, london_mins
    elif now.time() < london_close:
        status = "مفتوح"
        next_close = "لندن"
        hours, mins = time_until(london_close)[0], time_until(london_close)[1]
        color = "green"
    elif now.time() < ny_open:
        status = "مغلق"
        next_open = "نيويورك"
        hours, mins = ny_hours, ny_mins
        color = "gray"
    elif now.time() < ny_close:
        status = "مفتوح"
        next_close = "نيويورك"
        hours, mins = time_until(ny_close)[0], time_until(ny_close)[1]
        color = "green"
    else:
        status = "مغلق"
        next_open = "لندن"
        hours, mins = time_until(london_open)[0] + 24, time_until(london_open)[1]
        color = "gray"

    if status == "مفتوح":
        if hours < 1:
            color = "green"
        elif hours < 2:
            color = "yellow"
        else:
            color = "gray"
    else:
        color = "gray"

    return {
        "status": status,
        "next_event": f"يفتح {next_open}" if status == "مغلق" else f"يغلق {next_close}",
        "countdown": f"{hours} ساعات {mins} دقيقة",
        "color": color
    }

@app.post("/api/ai/assistant")
def ai_trade_assistant(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    question = payload.get("question", "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    # Get latest analysis
    latest_analysis = db.query(models.Analysis).filter(models.Analysis.user_id == current_user.id).order_by(models.Analysis.created_at.desc()).first()
    analysis_context = ""
    if latest_analysis:
        try:
            result = json.loads(latest_analysis.result_json or '{}')
            analysis_context = f"آخر تحليل: {latest_analysis.market} - {result.get('recommendation', 'unknown')} مع ثقة {result.get('confidence', 0)}%"
        except:
            analysis_context = f"آخر تحليل: {latest_analysis.market}"

    # Get memory insights
    memory_insight = vector_memory.get_insight(question, db=db)

    # Get news sentiment
    if social_sentiment_service is not None:
        news_sentiment = social_sentiment_service.analyze("XAUUSD")  # Default to gold
    else:
        news_sentiment = "لا تتوفر بيانات تحليل الأخبار حالياً"

    # Combine into prompt for AI
    prompt = f"""
سؤال المستخدم: {question}

سياق آخر تحليل: {analysis_context}

رؤى الذاكرة: {memory_insight}

تحليل الأخبار: {news_sentiment}
"""
    # Use ai_core to generate response
    answer = ai_core_service.answer_question(question, prompt)

    return {"answer": answer}

# --- Super AI Agent Helpers ---

def _normalize_text(value: str) -> str:
    return re.sub(r"[^\w\s]", " ", (value or "").strip().lower())


def _find_numbers(value: str):
    if not value:
        return []
    numbers = re.findall(r"\d+[\.,]?\d*", value.replace("،", "."))
    results = []
    for n in numbers:
        try:
            results.append(float(n.replace(",", ".")))
        except Exception:
            continue
    return results


def _map_named_market(text: str) -> str:
    name = _normalize_text(text)
    mappings = {
        "ذهب": "XAUUSD",
        "الذهب": "XAUUSD",
        "يورودولار": "EURUSD",
        "يورو دولار": "EURUSD",
        "يورو": "EURUSD",
        "جنيه": "GBPUSD",
        "باوند": "GBPUSD",
        "بيتكوين": "BTCUSDT",
        "بتكوين": "BTCUSDT",
        "إيثيريوم": "ETHUSDT",
        "إيثريوم": "ETHUSDT",
        "دولار ين": "USDJPY",
        "دولار/ين": "USDJPY",
        "داوجونز": "US30",
        "ناسداك": "US100",
        "نفط": "WTI",
        "ذهب": "XAUUSD",
    }
    for key, value in mappings.items():
        if key in name:
            return value
    symbols = ["XAUUSD", "EURUSD", "GBPUSD", "BTCUSDT", "ETHUSDT", "USDJPY", "USDCAD", "AUDUSD", "US30", "US100", "SPX500"]
    for symbol in symbols:
        if symbol.lower() in name.replace("/", "").replace(" ", ""):
            return symbol
    return "XAUUSD"


def _infer_intent(question: str) -> str:
    q = _normalize_text(question)
    if any(word in q for word in ["تنبيه", "alert", "سعر", "نبه", "target", "above", "below"]):
        return "price_alert"
    if any(word in q for word in ["backtest", "اختبار", "محاكاة", "walk", "عودة"]):
        return "backtest"
    if any(word in q for word in ["سجل", "تاريخ", "صفقات", "journal", "history"]):
        return "trade_history"
    if any(word in q for word in ["استراتيجية", "performance", "أداء", "win rate", "خسارة"]):
        return "strategy_performance"
    if any(word in q for word in ["إعدادات", "theme", "risk", "capital", "mode", "preferences", "preference"]):
        return "settings"
    if any(word in q for word in ["footprint", "bookmap", "سيولة", "مناطق السيولة", "شمعة", "نموذج"]):
        return "visual_analysis"
    return "market_analysis"


def _infer_mood(question: str) -> str:
    q = _normalize_text(question)
    if any(word in q for word in ["قلق", "متوتر", "خائف", "خوف"]):
        return "anxious"
    if any(word in q for word in ["متحمس", "فخور", "confident", "حماس"]):
        return "excited"
    if any(word in q for word in ["متردد", "مش متأكد", "حائر"]):
        return "uncertain"
    return "neutral"


def _build_user_profile(current_user: models.User, db: Session) -> dict:
    prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == current_user.id).first()
    journal = db.query(models.JournalEntry).filter(models.JournalEntry.user_id == current_user.id).order_by(models.JournalEntry.created_at.desc()).limit(40).all()
    analyses = db.query(models.Analysis).filter(models.Analysis.user_id == current_user.id).order_by(models.Analysis.created_at.desc()).limit(40).all()
    alerts = db.query(models.PriceAlert).filter(models.PriceAlert.user_id == current_user.id).order_by(models.PriceAlert.created_at.desc()).limit(20).all()

    market_counts = {}
    for entry in journal + analyses:
        if getattr(entry, 'market', None):
            market = entry.market.upper()
            market_counts[market] = market_counts.get(market, 0) + 1

    favorite_markets = [k for k, _ in sorted(market_counts.items(), key=lambda item: item[1], reverse=True)][:3]
    recent_mistakes = [entry.market for entry in journal if entry.result and str(entry.result).lower() in ['loss', 'خاسر', 'losses', 'loss']][:3]
    style = 'محافظ' if prefs and float(getattr(prefs, 'risk_percentage', 1.0)) <= 1.0 else 'معتدل' if prefs and float(getattr(prefs, 'risk_percentage', 1.0)) <= 2.0 else 'مغامر'

    return {
        'user_email': current_user.email,
        'favorite_markets': favorite_markets,
        'recent_questions': [a.description for a in analyses if a.description][:5],
        'recent_mistakes': recent_mistakes,
        'settings': {
            'theme': getattr(prefs, 'theme', 'dark') if prefs else 'dark',
            'risk_percentage': float(getattr(prefs, 'risk_percentage', 1.0)) if prefs else 1.0,
            'capital': float(getattr(prefs, 'capital', 10000.0)) if prefs else 10000.0,
            'trading_mode': getattr(prefs, 'trading_mode', 'day') if prefs else 'day',
        },
        'alert_count': len(alerts),
        'journal_count': len(journal),
        'analysis_count': len(analyses),
        'style': style,
    }


def _summarize_visual_analysis(visual_analysis: dict) -> str:
    if not visual_analysis:
        return ''
    analysis = visual_analysis.get('analysis') if isinstance(visual_analysis.get('analysis'), dict) else visual_analysis.get('analysis')
    if isinstance(analysis, dict):
        note = analysis.get('note') or analysis.get('recommendation') or ''
        confidence = analysis.get('confidence')
        pair = visual_analysis.get('pair') or visual_analysis.get('symbol')
        timeframe = visual_analysis.get('timeframe')
        parts = []
        if note:
            parts.append(f"{note}")
        if pair:
            parts.append(f"زوج: {pair}")
        if timeframe:
            parts.append(f"فريم: {timeframe}")
        if confidence is not None:
            parts.append(f"ثقة {confidence}%")
        return "تحليل مرئي: " + ", ".join(parts) if parts else "تم إنشاء تحليل مرئي للصورة."
    return str(analysis)


def _sanitize_string_for_user(s: str) -> str:
    if not s or not isinstance(s, str):
        return s
    # Remove mentions of internal provider/model names and phrases that leak implementation
    banned = [r"gemini", r"deepseek", r"openrouter", r"openai", r"anthropic", r"deepmind"]
    pattern = re.compile(r"(" + r"|".join(banned) + r")", re.IGNORECASE)
    s = pattern.sub("", s)
    # Remove common leaked phrases in Arabic or English
    s = re.sub(r"تَم\s+التحليل\s+بواسطة|تم التحليل بواسطة|وفقاً لـ\s+\w+|according to\s+\w+|powered by\s+\w+", "", s, flags=re.IGNORECASE)
    # Clean up extra whitespace and stray punctuation
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"\s+[,\.؛]", ",", s)
    return s


def _sanitize_obj_for_user(obj):
    # Recursively sanitize strings in nested dict/list structures
    if isinstance(obj, str):
        return _sanitize_string_for_user(obj)
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            # drop explicit provider/model keys
            if k.lower() in ("provider", "model", "engine", "source"):
                continue
            out[k] = _sanitize_obj_for_user(v)
        return out
    if isinstance(obj, list):
        return [_sanitize_obj_for_user(x) for x in obj]
    return obj


def _record_agent_memory(db: Session, current_user: models.User, question: str, answer: str, visual_summary: str):
    try:
        analysis = models.Analysis(
            user_id=current_user.id,
            market='AGENT',
            image_path=None,
            description=question,
            result_json=json.dumps({'answer': answer, 'visual_summary': visual_summary}, ensure_ascii=False),
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        vector_memory.store_analysis(analysis.id, question, answer, db=db)
    except Exception:
        db.rollback()
    try:
        memory = internal_brain_service.get_component_memory('super_agent') or {}
        conversations = memory.setdefault('conversations', [])
        conversations.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': current_user.id,
            'question': question,
            'answer': answer,
            'visual_summary': visual_summary,
        })
        if len(conversations) > 400:
            conversations[:] = conversations[-400:]
        internal_brain_service._save_component_memory('super_agent', memory)
    except Exception:
        pass


def _build_agent_answer(question: str, intent: str, mood: str, profile: dict, market: str, market_data: dict, memory_matches: list, visual_analysis: dict, action_result: dict, quick_backtest: dict, session_info: dict) -> str:
    greeting = 'مساء الخير' if 15 <= datetime.now(timezone.utc).hour < 21 else 'صباح الخير' if 6 <= datetime.now(timezone.utc).hour < 15 else 'مساء النور'
    mood_sentence = ''
    if mood == 'anxious':
        mood_sentence = 'أشعر بأن لديك قلق خفيف، سأبقي النصيحة مركزة وحذرة.'
    elif mood == 'excited':
        mood_sentence = 'يبدو أنك متحمس، سأوازن النصيحة مع تحذير مخاطر واضح.'
    elif mood == 'uncertain':
        mood_sentence = 'واضح أنك متردد، سأعرض لك سيناريوهات واضحة لتسهيل القرار.'

    base = [f"{greeting}، أنا الوكيل الخارق الخاص بك. {mood_sentence}".strip()]
    base.append(f"ملاحظاتي عن أسلوبك: تداولك تميل لأن يكون {profile.get('style')} ويتركز حول {', '.join(profile.get('favorite_markets', [])) or 'الذهب وأسواق رئيسية'}." )

    if memory_matches:
        matches = ', '.join(f"{m.get('market', 'سوق غير محدد')}" for m in memory_matches[:2])
        base.append(f"أسترجع حديثاً عن {matches}. سأبني عليه لإجابتك.")

    if visual_analysis:
        visual_text = _summarize_visual_analysis(visual_analysis)
        base.append(visual_text)

    if intent == 'price_alert' and action_result:
        base.append(f"تم إنشاء تنبيه سعر ل {action_result.get('market')} عند {action_result.get('target_price')} ({action_result.get('direction')}). سأراقبه لك.")
    elif intent == 'settings' and action_result:
        updates = action_result.get('updated', {})
        changes = ', '.join(f"{k} = {v}" for k, v in updates.items())
        base.append(f"تم تحديث الإعدادات بنجاح: {changes}.")
    elif intent == 'trade_history':
        base.append('إليك ملخص سريع من سجل تداولاتك الأخيرة:')
    elif intent == 'strategy_performance':
        base.append('سأعرض لك أهم مقاييس أداء الاستراتيجيات الخاصة بك الآن.')
    elif intent == 'backtest' and quick_backtest:
        perf = quick_backtest.get('metrics', {})
        base.append(f"إليك نتائج backtest السريع لـ {market}: معدل الفوز {perf.get('win_rate', 0.0):.1f}%, العائد الإجمالي {perf.get('total_return', 0.0):.1f}.")
    elif action_result and 'real_analysis' in action_result:
        real = action_result['real_analysis']
        rec = real.get('recommendation', 'غير واضح')
        conf = real.get('confidence', 0)
        thesis = real.get('reason', 'لا يوجد سبب مفصل.')
        targets = real.get('targets', [])
        stop_loss = real.get('stop_loss')
        
        target_str = f"الأهداف: {', '.join(map(str, targets))}." if targets else ""
        stop_str = f"وقف الخسارة: {stop_loss}." if stop_loss else ""
        
        base.append(f"التحليل الفعلي للسوق: التوصية {rec} (بثقة {conf}%). {target_str} {stop_str} أطروحة السوق: {thesis}")
    elif action_result and 'error' in action_result:
        base.append(action_result['error'])
    else:
        base.append(f"سأقدم لك تحليل السوق في {market} مع توصية واضحة ورؤية مبسطة.")

    if market_data and market_data.get('price'):
        base.append(f"السعر الحالي لـ {market} هو {market_data.get('price'):.4f}.")
    if session_info:
        base.append(f"جاري التداول في جلسة {session_info.get('label')}، {session_info.get('note')}")

    if quick_backtest and isinstance(quick_backtest, dict) and quick_backtest.get('note'):
        base.append(f"ملاحظة backtest: {quick_backtest.get('note')}")

    return ' '.join(base)


async def _analyze_image_file(image: UploadFile) -> dict:
    try:
        image_bytes = await image.read()
        if not image_bytes:
            return {}

        raw = tradingview_service.analyze_with_gemini(image_bytes)

        # Standardize provider responses into a consistent shape the agent expects
        standardized: dict = {}
        source = raw.get('source') if isinstance(raw, dict) else None

        # Extract analysis payload
        analysis = None
        if isinstance(raw, dict):
            analysis = raw.get('analysis') or raw
        else:
            analysis = raw

        # If analysis is a dict, pick common fields
        if isinstance(analysis, dict):
            recommendation = analysis.get('recommendation') or analysis.get('result') or ''
            # Build a human-friendly note by looking for common keys
            note = analysis.get('note') or analysis.get('text') or analysis.get('summary') or ''
            if not note:
                parts = [str(v) for v in analysis.values() if isinstance(v, str) and v.strip()]
                note = ' '.join(parts[:3]).strip() if parts else ''
            confidence = analysis.get('confidence') or analysis.get('score') or analysis.get('confidence_score') or 0
            try:
                confidence = int(float(confidence))
            except Exception:
                confidence = 0

            standardized['analysis'] = {
                'recommendation': recommendation or (note[:100] if note else 'محايد'),
                'note': note,
                'confidence': confidence
            }
        elif isinstance(analysis, str):
            standardized['analysis'] = {'recommendation': analysis[:120], 'note': analysis, 'confidence': 0}
        else:
            standardized['analysis'] = {'recommendation': 'محايد', 'note': 'لم يتم الحصول على تحليل مفصل من المزود.', 'confidence': 0}

        # Preserve metadata if present
        if isinstance(raw, dict):
            for k in ('pair', 'timeframe', 'source'):
                if k in raw and raw.get(k):
                    standardized[k] = raw.get(k)

        # Sanitize provider/model mentions before returning
        return _sanitize_obj_for_user(standardized)
    except Exception:
        return {}


def _build_simple_response(answer: str, intent: str = "conversational"):
    return {
        'answer': answer,
        'intent': intent,
        'mood': 'neutral',
        'profile': {}, 'market_data': {}, 'session_info': {}, 'spread_report': {}, 'memory_matches': [], 'visual_analysis': {}, 'action_result': {}, 'quick_backtest': {}
    }

@app.post("/api/ai/agent")
async def super_ai_agent(
    question: str = Form(""),
    image: UploadFile = File(None),
    market: str = Form(None),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    question = (question or "").strip()

    # ── Session init ───────────────────────────────────────────────────────────
    if current_user.id not in USER_SESSIONS:
        USER_SESSIONS[current_user.id] = {"history": [], "last_market": None}
    session = USER_SESSIONS[current_user.id]

    SYSTEM_PROMPT = (
        "أنت وكيل تداول ذكي في منصة VisionTrader AI. "
        "أنت خبير في التحليل الفني والأساسي. "
        "تجيب على أسئلة المستخدمين عن الأسواق المالية والعملات والذهب والنفط والمؤشرات. "
        "تقدم تحليلات مفيدة ونصائح ذكية. "
        "تتحدث بالعربية بطلاقة. أسلوبك ودود ومحترف. "
        "إذا طُلب منك تحليل سوق، اذكر الاتجاه والتوصية ومستويات الدعم والمقاومة."
    )

    # ── Helper: call Gemini REST API ───────────────────────────────────────────
    async def call_gemini(user_text: str, image_b64: str = None, image_mime: str = None) -> str:
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            return ""
        import httpx
        contents = []
        # Prepend system as first user turn (Gemini has no system role)
        contents.append({
            "role": "user",
            "parts": [{"text": SYSTEM_PROMPT}]
        })
        contents.append({"role": "model", "parts": [{"text": "تمام، أنا جاهز لمساعدتك."}]})
        # Add conversation history (last 16 turns)
        for msg in session["history"][-16:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        # Current user turn
        current_parts = [{"text": user_text}]
        if image_b64 and image_mime:
            current_parts.append({"inlineData": {"mimeType": image_mime, "data": image_b64}})
        contents.append({"role": "user", "parts": current_parts})

        # Try gemini-3.0-flash, fallback to gemini-2.5-flash, then gemini-1.5-flash
        models_to_try = ["gemini-3.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
        for model_name in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": contents,
                "generationConfig": {"temperature": 0.75, "maxOutputTokens": 1024}
            }
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as exc:
                logger.warning(f"Gemini API call with {model_name} failed: {exc}")
        
        # DeepSeek Fallback
        deepseek_key = getattr(settings, "DEEPSEEK_API_KEY", "")
        if deepseek_key:
            try:
                url = "https://api.deepseek.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {deepseek_key}",
                    "Content-Type": "application/json"
                }
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for msg in session["history"][-16:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                # DeepSeek does not support images usually, so we only pass text
                messages.append({"role": "user", "content": user_text})
                
                payload = {
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.75,
                    "max_tokens": 1024
                }
                async with httpx.AsyncClient(timeout=20) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as exc:
                logger.warning(f"DeepSeek fallback failed: {exc}")

        return "التحليل من نظام التصويت فقط - Gemini غير متاح"

    # ── Helper: detect market symbol from text ─────────────────────────────────
    def detect_market(text: str) -> str:
        t = text.lower()
        mapping = [
            (["ذهب", "gold", "xauusd"], "XAUUSD"),
            (["بيتكوين", "bitcoin", "btc"], "BTCUSDT"),
            (["يورو", "euro", "eurusd"], "EURUSD"),
            (["باوند", "جنيه", "pound", "gbpusd"], "GBPUSD"),
            (["نفط", "oil", "crude", "usoil"], "USOIL"),
            (["ناسداك", "nasdaq", "nas100"], "NAS100"),
            (["داو جونز", "dow", "us30"], "US30"),
            (["فضة", "silver", "xagusd"], "XAGUSD"),
            (["ايثيريوم", "ethereum", "eth"], "ETHUSDT"),
            (["دولار ين", "usdjpy"], "USDJPY"),
        ]
        for keywords, symbol in mapping:
            if any(k in t for k in keywords):
                return symbol
        return ""

    # ── Helper: Enhanced Analysis with Live Data and Footprint ────────────────
    async def get_enhanced_engine_analysis(market_target: str, user_question: str) -> str:
        engine_suffix = ""
        try:
            from services.binance_service import binance_service
            from services.footprint_service import FootprintChartAnalyzer, BookmapDOMReader, CumulativeDeltaAnalyzer
            from services.auto_scanner import auto_scanner
            
            # 1. Fetch live binance data
            mapping = {"BTCUSD": "BTCUSDT", "ETHUSD": "ETHUSDT", "SOLUSD": "SOLUSDT", "BNBUSD": "BNBUSDT", "XRPUSD": "XRPUSDT"}
            b_symbol = mapping.get(market_target.upper().replace(' ', ''), market_target.upper().replace(' ', ''))
            
            market_live_data = None
            if binance_service.ws_service:
                market_live_data = binance_service.ws_service.get_live_data(b_symbol)
            
            footprint_text = ""
            if market_live_data:
                recent_trades = market_live_data.get("recent_trades", [])
                ob = market_live_data.get("order_book", {})
                
                if recent_trades or ob:
                    fp = FootprintChartAnalyzer()
                    bm = BookmapDOMReader()
                    cd = CumulativeDeltaAnalyzer()
                    
                    for t in recent_trades:
                        fp.ingest_trade(t['price'], t['qty'], t.get('side'))
                        cd.ingest_trade(t['price'], t['qty'], t.get('side'))
                    
                    if ob.get('bids') or ob.get('asks'):
                        bm.ingest_snapshot(ob.get('bids', []), ob.get('asks', []))
                        
                    fp_res = fp.analyze()
                    bm_res = bm.analyze()
                    cd_res = cd.analyze()
                    
                    footprint_text = f"\n\n📊 **تحليل السيولة الحي (Footprint & Bookmap):**\n- توازن السيولة: {fp_res.get('imbalance_signal', 'محايد')}\n- ضغط صانع السوق: {bm_res.get('pressure_side', 'محايد')}\n- دلتا التراكمية: {cd_res.get('delta', 0)}"

            # 2. Add to context and analyze
            visual_context = [{"description": (user_question or "تحليل شارت") + footprint_text}]
            unified = voting_engine.data_adapter.normalize_input(visual_context, market_target)
            ap = agent_manager.run(unified)
            ow = ap.get("orchestrator", {}).get("weights")
            rr = await asyncio.wait_for(
                asyncio.to_thread(voting_engine.analyze, visual_context, market_target, current_user.id, orchestrator_weights=ow),
                timeout=12
            )
            
            rec = rr.get("recommendation", "محايد")
            conf = rr.get("confidence", 0)
            reason = rr.get("reason", "")
            targets = rr.get("targets", [])
            sl = rr.get("stop_loss", "")
            
            best_ops = auto_scanner.get_top_opportunities()
            def format_opportunity(best):
                return (
                    f"💡 أفضل فرصة حالياً هي على {best['market']} بثقة {best['confidence']}%.\n"
                    f"- التوصية: {best['recommendation']}\n"
                    f"- الدخول: {best['entry']}\n"
                    f"- SL: {best['sl']}\n"
                    f"- TP: {best['tp']}\n"
                    f"- R:R: {best.get('rr', '1:3')}"
                )

            strong_op = next((op for op in best_ops if op.get("confidence", 0) > 70), None)
            strong_alert_added = False
            if strong_op:
                alert_msg = f"🚨 فرصة قوية على {strong_op['market']}! ثقة {strong_op['confidence']}%"
                engine_suffix += f"\n\n{alert_msg}\n"
                strong_alert_added = True
                try:
                    await ws_manager.broadcast(json.dumps({"type": "alert", "message": alert_msg}, ensure_ascii=False))
                except Exception as e:
                    logger.error(f"Failed to broadcast alert: {e}")
                try:
                    telegram_service.send_alert(None, strong_op["market"], strong_op["recommendation"], strong_op["confidence"], [])
                except Exception as e:
                    logger.error(f"Failed to send Telegram alert: {e}")
                try:
                    create_alert(
                        current_user.id,
                        strong_op["market"],
                        strong_op["recommendation"],
                        strong_op["confidence"],
                        strong_op["entry"],
                        strong_op["sl"],
                        strong_op["tp"],
                        f"R:R {strong_op.get('rr', '1:3')}"
                    )
                except Exception as e:
                    logger.error(f"Failed to record strong opportunity dashboard alert: {e}")

            # 3. Check Confidence < 60%
            if conf < 60 or rec not in ["شراء", "بيع"]:
                if best_ops:
                    best = best_ops[0]
                    engine_suffix += f"\n\n⚠️ {market_target} متذبذب الآن. {format_opportunity(best)}"
                else:
                    engine_suffix += f"\n\n⚠️ {market_target} متذبذب الآن. لا توجد فرصة قوية معلنة في الأسواق الأخرى حالياً."
                return engine_suffix
            else:
                if conf > 70:
                    if not strong_alert_added:
                        alert_msg = f"🚨 فرصة قوية على {market_target}! ثقة {conf}%"
                        engine_suffix += f"\n\n{alert_msg}\n"
                    engine_suffix += f"📊 **نظام VisionTrader ({market_target})**: {rec}"
                else:
                    engine_suffix += f"\n\n📊 **نظام VisionTrader ({market_target})**: {rec} | ثقة {conf}%"

                if footprint_text:
                    engine_suffix += footprint_text
                if targets:
                    engine_suffix += f"\n🎯 أهداف: {', '.join(map(str, targets))}"
                if sl:
                    engine_suffix += f"\n🛑 وقف: {sl}"
                if reason:
                    engine_suffix += f"\n💡 {reason}"
                    
        except Exception as e:
            logger.warning(f"Enhanced Voting engine failed: {e}")
            
        return engine_suffix

    try:
        SYSTEM_METRICS["gemini_calls"] += 1

        # ── IMAGE PATH ──────────────────────────────────────────────────────────
        if image is not None:
            image_bytes = await image.read()
            if not image_bytes:
                return _build_simple_response("الصورة فارغة. يرجى إرسال صورة واضحة.", "error")
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            mime = image.content_type or "image/jpeg"

            vision_prompt = (
                (question + "\n\n") if question else ""
            ) + (
                "حلل هذا الشارت بالتفصيل: حدد الاتجاه العام، مستويات الدعم والمقاومة، "
                "أي نماذج سعرية، وقدم توصية واضحة (شراء/بيع/انتظار) مع السبب."
            )

            gemini_answer = await call_gemini(vision_prompt, image_b64, mime)

            # Also run enhanced voting engine if market context available
            market_target = detect_market(question) or session.get("last_market") or (market or "")
            engine_suffix = ""
            if market_target:
                session["last_market"] = market_target
                engine_suffix = await get_enhanced_engine_analysis(market_target, question)

            if not gemini_answer:
                gemini_answer = "تم استلام الصورة لكن تعذّر تحليلها. تأكد من وضوح الشارت وحاول مرة أخرى."

            final_answer = gemini_answer + engine_suffix
            session["history"].append({"role": "user", "content": f"[صورة] {question}"})
            session["history"].append({"role": "ai", "content": final_answer})
            if len(session["history"]) > 20:
                session["history"] = session["history"][-20:]
            resp = _build_simple_response(final_answer, "visual_analysis")
            return resp

        # ── TEXT PATH ───────────────────────────────────────────────────────────
        if not question:
            return _build_simple_response("أهلاً! كيف يمكنني مساعدتك في التداول اليوم؟", "general")

        session["history"].append({"role": "user", "content": question})
        if len(session["history"]) > 20:
            session["history"] = session["history"][-20:]

        # 1. Get Gemini's natural language answer (pass history minus current msg)
        gemini_answer = await call_gemini(question)

        # 2. Detect market and enrich with voting engine if relevant
        market_target = detect_market(question) or session.get("last_market") or (market or "")
        wants_analysis = any(w in question for w in [
            "حلل", "تحليل", "كيف حال", "وين", "ايش رأيك", "رأيك",
            "توصية", "ادخل", "اشتري", "بيع", "اشوف", "تتوقع"
        ])

        engine_suffix = ""
        if wants_analysis and market_target:
            session["last_market"] = market_target
            engine_suffix = await get_enhanced_engine_analysis(market_target, question)

        # Fallback if Gemini had no API key or failed
        if not gemini_answer:
            if engine_suffix:
                gemini_answer = f"بناءً على تحليل السوق لـ {market_target}:"
            else:
                gemini_answer = "يمكنني مساعدتك في تحليل الأسواق المالية. اذكر لي السوق الذي تريد تحليله (مثل: الذهب، اليورو، البيتكوين)."

        final_answer = gemini_answer + engine_suffix
        session["history"].append({"role": "ai", "content": final_answer})

        return _build_simple_response(final_answer, "market_analysis" if engine_suffix else "conversational")

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"super_ai_agent failed: {exc}")
        return _build_simple_response("حدث خطأ مؤقت. يرجى المحاولة مرة أخرى.", "error")

# ─────────────────────────────────────────────────────────────
# Conversational Agent — Multi-step trading analysis with auto TradingView screenshot
# ─────────────────────────────────────────────────────────────
CONV_STATES = {
    "idle": "idle",
    "ask_pair": "ask_pair",
    "ask_timeframe": "ask_timeframe",
    "ask_trade_type": "ask_trade_type",
    "analyzing": "analyzing",
    "done": "done",
}

SUPPORTED_PAIRS = [
    "XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "AUDUSD", "USDCAD", "BTCUSDT", "ETHUSDT", "USOIL",
    "NAS100", "US30", "XAGUSD", "GBPJPY", "EURJPY",
]

SUPPORTED_TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"]
SUPPORTED_TRADE_TYPES = ["سكالبينج", "يومي", "سوينج", "scalping", "day", "swing"]

PAIR_ALIASES = {
    "ذهب": "XAUUSD", "gold": "XAUUSD", "xau": "XAUUSD",
    "يورو": "EURUSD", "euro": "EURUSD", "eur": "EURUSD",
    "باوند": "GBPUSD", "جنيه": "GBPUSD", "pound": "GBPUSD", "gbp": "GBPUSD",
    "ين": "USDJPY", "yen": "USDJPY", "jpy": "USDJPY",
    "بيتكوين": "BTCUSDT", "bitcoin": "BTCUSDT", "btc": "BTCUSDT",
    "ايثيريوم": "ETHUSDT", "ethereum": "ETHUSDT", "eth": "ETHUSDT",
    "نفط": "USOIL", "oil": "USOIL", "crude": "USOIL",
    "ناسداك": "NAS100", "nasdaq": "NAS100", "nas": "NAS100",
    "داو": "US30", "dow": "US30", "us30": "US30",
    "فضة": "XAGUSD", "silver": "XAGUSD", "xag": "XAGUSD",
    "كابي": "GBPJPY", "gbpjpy": "GBPJPY",
}

TF_ALIASES = {
    "1m": "M1", "m1": "M1", "دقيقة": "M1",
    "5m": "M5", "m5": "M5", "5 دقائق": "M5",
    "15m": "M15", "m15": "M15", "15 دقيقة": "M15",
    "30m": "M30", "m30": "M30", "30 دقيقة": "M30",
    "1h": "H1", "h1": "H1", "ساعة": "H1", "ساعه": "H1",
    "4h": "H4", "h4": "H4", "4 ساعات": "H4",
    "1d": "D1", "d1": "D1", "يومي": "D1", "daily": "D1",
    "1w": "W1", "w1": "W1", "اسبوعي": "W1", "weekly": "W1",
}

def _parse_pair(text: str) -> Optional[str]:
    t = text.strip().upper()
    if t in SUPPORTED_PAIRS:
        return t
    for alias, sym in PAIR_ALIASES.items():
        if alias in text.lower():
            return sym
    return None

def _parse_timeframe(text: str) -> Optional[str]:
    t = text.strip().upper()
    if t in SUPPORTED_TIMEFRAMES:
        return t
    for alias, tf in TF_ALIASES.items():
        if alias in text.lower():
            return tf
    return None

def _parse_trade_type(text: str) -> Optional[str]:
    t = text.lower()
    if any(k in t for k in ["سكالب", "scalp", "سريع"]):
        return "سكالبينج"
    if any(k in t for k in ["سوينج", "swing", "اسبوعي", "طويل"]):
        return "سوينج"
    if any(k in t for k in ["يومي", "day", "daily", "نهاري"]):
        return "يومي"
    return None

def _is_analysis_request(text: str) -> bool:
    keywords = ["حلل", "تحليل", "ابي", "أبي", "اريد", "أريد", "اعطني", "صفقة", "trade", "analyze", "analysis", "شارت", "chart", "توصية"]
    return any(k in text.lower() for k in keywords)

@app.get("/api/ai/screenshot")
async def get_tv_screenshot(
    symbol: str,
    timeframe: str = "H1",
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Get a direct screenshot of a TradingView chart.
    """
    from services.tv_screenshot import capture_tradingview_chart
    screenshot_bytes = await capture_tradingview_chart(symbol, timeframe)
    if not screenshot_bytes:
        raise HTTPException(status_code=500, detail="Failed to capture screenshot")
    return Response(content=screenshot_bytes, media_type="image/png")

@app.post("/api/ai/conversational-agent")
async def conversational_agent(
    message: str = Form(""),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Multi-step conversational trading agent.
    Guides user through: pair selection → timeframe → trade type → auto screenshot → AI analysis
    """
    message = (message or "").strip()
    uid = current_user.id

    # Init or retrieve session state
    if uid not in USER_SESSIONS:
        USER_SESSIONS[uid] = {"history": [], "last_market": None}
    session = USER_SESSIONS[uid]

    # Init conversation state
    if "conv" not in session:
        session["conv"] = {
            "state": "idle",
            "pair": None,
            "timeframe": None,
            "trade_type": None,
        }
    conv = session["conv"]

    def reply(msg: str, state: str, options: list = None, action: str = None):
        conv["state"] = state
        return {
            "message": msg,
            "state": state,
            "options": options or [],
            "action": action or "",
        }

    # ── Handle RESET command ────────────────────────────────────────────────
    if message.lower() in ["reset", "إعادة", "ابدأ من جديد", "جديد", "بداية"]:
        session["conv"] = {"state": "idle", "pair": None, "timeframe": None, "trade_type": None}
        return reply(
            "حسناً، أبدأ من جديد! 🔄\n\nأنا وكيل التداول الذكي. تقدر تطلب مني:\n• تحليل شارت أي زوج\n• توصية بدخول وخروج\n• أو ترفع صورة شارت وأحللها\n\nبماذا أقدر أساعدك؟",
            "idle",
            ["أبي تحليل", "حلل الذهب", "ارفع شارت"]
        )

    # ── STATE: idle — detect if user wants analysis ─────────────────────────
    if conv["state"] == "idle":
        if not message:
            return reply(
                "أهلاً! 👋 أنا وكيل التداول الذكي في VisionTrader AI.\n\nأقدر أحلل لك أي زوج تداولي بشكل احترافي مع:\n✅ نقطة الدخول\n✅ وقف الخسارة (SL)\n✅ الأهداف (TP1, TP2, TP3)\n✅ نسبة المخاطرة/العائد (R:R)\n\nبماذا أقدر أساعدك؟",
                "idle",
                ["أبي تحليل شارت", "حلل الذهب", "حلل EURUSD", "حلل البيتكوين"]
            )

        # Try to detect pair directly from first message
        detected_pair = _parse_pair(message)
        if detected_pair:
            conv["pair"] = detected_pair
            conv["state"] = "ask_timeframe"
            return reply(
                f"ممتاز! اخترت **{detected_pair}** ✅\n\nأي إطار زمني تريد التحليل عليه؟",
                "ask_timeframe",
                ["M15", "H1", "H4", "D1", "M5", "M30", "W1"]
            )

        if _is_analysis_request(message):
            conv["state"] = "ask_pair"
            return reply(
                "بالتأكيد! 📊 سأحلل لك الشارت بالكامل.\n\n**أولاً**: أي زوج أو سوق تريد تحليله؟",
                "ask_pair",
                ["XAUUSD (ذهب)", "EURUSD", "GBPUSD", "BTCUSDT", "NAS100", "USOIL", "ETHUSDT", "GBPJPY"]
            )

        # General question — pass to regular Gemini agent
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if api_key:
            import httpx
            contents = [
                {"role": "user", "parts": [{"text": "أنت وكيل تداول ذكي. تجيب بالعربية بأسلوب ودود ومحترف. تقدر تساعد في تحليل الأسواق."}]},
                {"role": "model", "parts": [{"text": "تمام، أنا جاهز لمساعدتك."}]},
                {"role": "user", "parts": [{"text": message}]},
            ]
            for model_name in ["gemini-2.5-flash", "gemini-1.5-flash"]:
                try:
                    url_g = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    async with httpx.AsyncClient(timeout=15) as client:
                        resp = await client.post(url_g, json={"contents": contents, "generationConfig": {"maxOutputTokens": 512}})
                        resp.raise_for_status()
                        ans = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        return reply(ans, "idle", ["أبي تحليل شارت", "حلل الذهب"])
                except Exception:
                    pass
        return reply("يمكنني مساعدتك في تحليل الأسواق! اكتب 'أبي تحليل' وسأسألك عن التفاصيل. 📊", "idle", ["أبي تحليل شارت"])

    # ── STATE: ask_pair ─────────────────────────────────────────────────────
    if conv["state"] == "ask_pair":
        pair = _parse_pair(message)
        if not pair:
            return reply(
                "لم أتعرف على الزوج. جرب أحد هذه الخيارات أو اكتب رمز الزوج مباشرة:",
                "ask_pair",
                ["XAUUSD", "EURUSD", "GBPUSD", "BTCUSDT", "NAS100", "USOIL", "ETHUSDT", "USDJPY"]
            )
        conv["pair"] = pair
        conv["state"] = "ask_timeframe"
        return reply(
            f"ممتاز! اخترت **{pair}** ✅\n\n**ثانياً**: أي إطار زمني تريد التحليل عليه؟",
            "ask_timeframe",
            ["M5 (5 دقائق)", "M15 (15 دقيقة)", "H1 (ساعة)", "H4 (4 ساعات)", "D1 (يومي)", "W1 (أسبوعي)"]
        )

    # ── STATE: ask_timeframe ────────────────────────────────────────────────
    if conv["state"] == "ask_timeframe":
        tf = _parse_timeframe(message)
        if not tf:
            return reply(
                "لم أتعرف على الإطار الزمني. اختر أحد هذه:",
                "ask_timeframe",
                ["M5", "M15", "H1", "H4", "D1", "W1"]
            )
        conv["timeframe"] = tf
        conv["state"] = "ask_trade_type"
        return reply(
            f"ممتاز! **{conv['pair']}** على **{tf}** ✅\n\n**ثالثاً**: ما نوع التداول الذي تفضله؟",
            "ask_trade_type",
            ["سكالبينج ⚡ (دقائق)", "يومي 📅 (ساعات)", "سوينج 🌊 (أيام/أسابيع)"]
        )

    # ── STATE: ask_trade_type ───────────────────────────────────────────────
    if conv["state"] == "ask_trade_type":
        trade_type = _parse_trade_type(message)
        if not trade_type:
            trade_type = "يومي"  # Default
        conv["trade_type"] = trade_type
        conv["state"] = "analyzing"

        pair = conv["pair"]
        tf = conv["timeframe"]

        from services.multi_tf_analyzer import ANALYSIS_TIMEFRAMES, DEFAULT_TFS
        tfs_to_run = ANALYSIS_TIMEFRAMES.get(trade_type.lower(), DEFAULT_TFS)
        tfs_str = ", ".join(tfs_to_run)

        # Start async analysis
        return reply(
            f"🔍 **بدأت التحليل الشامل!**\n\nأفتح شارت **{pair}** على الأطر الزمنية **({tfs_str})**...\nسيتم تشغيل الوكلاء واستراتيجيات النظام بالكامل. قد يستغرق هذا بضع ثوانٍ ⏳",
            "analyzing",
            [],
            "fetch_analysis"
        )

    # ── STATE: analyzing — perform the actual multi-TF screenshot + AI analysis ──
    if conv["state"] == "analyzing":
        pair = conv.get("pair", "XAUUSD")
        trade_type = conv.get("trade_type", "يومي")

        from services.multi_tf_analyzer import full_multi_tf_analysis
        
        try:
            api_key = getattr(settings, "GEMINI_API_KEY", "")
            user_id_to_pass = current_user.id if current_user else None
            
            # This handles screenshots, agent_manager, voting_engine, and gemini
            analysis_data = await asyncio.wait_for(
                full_multi_tf_analysis(pair, trade_type, user_id_to_pass, api_key),
                timeout=60
            )
            analysis_result = analysis_data.get("final_analysis", "")
        except Exception as e:
            logger.exception("Multi-TF analysis failed in conv agent")
            analysis_result = f"""📊 **تحليل {pair}**

⚠️ تعذّر إكمال التحليل الشامل: {e}

حاول مرة أخرى لاحقاً أو جرب إطاراً زمنياً آخر. 🔄"""

        # Reset conversation after analysis
        session["conv"] = {"state": "idle", "pair": None, "timeframe": None, "trade_type": None}
        session["last_market"] = pair

        return reply(
            analysis_result,
            "done",
            ["تحليل زوج آخر", "أبي تحليل جديد", "إعادة"],
            "analysis_complete"
        )

    # Fallback
    session["conv"] = {"state": "idle", "pair": None, "timeframe": None, "trade_type": None}
    return reply("حدث خطأ في المحادثة. اضغط 'إعادة' للبدء من جديد.", "idle", ["إعادة"])


@app.post("/api/chart/detect")
async def detect_chart_screenshot(file: UploadFile = File(...), current_user: models.User = Depends(auth.get_current_user)):
    if not file:
        raise HTTPException(status_code=400, detail="File is required")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    SYSTEM_METRICS["gemini_calls"] += 1
    # Use tradingview service to detect pair and timeframe
    detected = tradingview_service.detect_chart_details(image_bytes)

    return {
        "pair": detected.get("pair", "UNKNOWN"),
        "timeframe": detected.get("timeframe", "UNKNOWN"),
        "confidence": detected.get("confidence", 50)
    }

# --- New Features 30-34 ---
@app.get("/api/daily-limits/status")
def get_daily_limits_status(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    prefs = _ensure_preferences(db, current_user)
    today = datetime.now(timezone.utc).date()
    entries = db.query(models.JournalEntry).filter(
        models.JournalEntry.user_id == current_user.id,
        models.JournalEntry.date >= datetime(today.year, today.month, today.day)
    ).all()
    daily_pnl = sum((e.profit_loss or 0) for e in entries)
    capital = float(prefs.capital or 10000.0)
    profit_target = capital * (prefs.daily_profit_target_percent / 100.0)
    loss_limit = capital * (prefs.daily_loss_limit_percent / 100.0)

    return {
        "daily_pnl": daily_pnl,
        "profit_target": profit_target,
        "loss_limit": loss_limit,
        "trading_locked_today": prefs.trading_locked_today,
        "lock_reason": prefs.lock_reason
    }

@app.get("/api/weekly-challenge")
def get_weekly_challenge(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    week_start = datetime.now(timezone.utc).date() - timedelta(days=datetime.now(timezone.utc).weekday())
    challenge = db.query(models.WeeklyChallenge).filter(models.WeeklyChallenge.week_start == week_start).first()
    if not challenge:
        return {"challenge": None}

    progress = db.query(models.UserChallengeProgress).filter(
        models.UserChallengeProgress.user_id == current_user.id,
        models.UserChallengeProgress.challenge_id == challenge.id
    ).first()
    if not progress:
        progress = models.UserChallengeProgress(user_id=current_user.id, challenge_id=challenge.id)
        db.add(progress)
        db.commit()
        db.refresh(progress)

    # Calculate current value based on challenge type
    current_value = 0.0
    if challenge.challenge_type == "trades_on_market":
        week_entries = db.query(models.JournalEntry).filter(
            models.JournalEntry.user_id == current_user.id,
            models.JournalEntry.market == challenge.market,
            models.JournalEntry.date >= week_start,
            _normalize_result(models.JournalEntry.result) == "win"
        ).count()
        current_value = week_entries
    elif challenge.challenge_type == "success_rate":
        week_entries = db.query(models.JournalEntry).filter(
            models.JournalEntry.user_id == current_user.id,
            models.JournalEntry.date >= week_start
        ).all()
        wins = len([e for e in week_entries if _normalize_result(e.result) == "win"])
        total = len(week_entries)
        current_value = (wins / max(1, total)) * 100.0
    elif challenge.challenge_type == "profit_target":
        week_entries = db.query(models.JournalEntry).filter(
            models.JournalEntry.user_id == current_user.id,
            models.JournalEntry.date >= week_start
        ).all()
        current_value = sum((e.profit_loss or 0) for e in week_entries)

    progress.current_value = current_value
    if current_value >= challenge.target_value and not progress.completed:
        progress.completed = True
        progress.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "challenge": {
            "id": challenge.id,
            "description": challenge.description,
            "target": challenge.target_value,
            "reward": challenge.reward_description
        },
        "progress": {
            "current": current_value,
            "completed": progress.completed
        }
    }

@app.get("/api/leaderboard")
def get_leaderboard(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    week_start = datetime.now(timezone.utc).date() - timedelta(days=datetime.now(timezone.utc).weekday())
    progresses = db.query(models.UserChallengeProgress).join(models.WeeklyChallenge).filter(
        models.WeeklyChallenge.week_start == week_start,
        models.UserChallengeProgress.completed == True
    ).all()
    leaderboard = []
    for p in progresses:
        user = db.query(models.User).filter(models.User.id == p.user_id).first()
        if user:
            leaderboard.append({
                "username": user.email.split('@')[0],  # Simple username
                "completed_at": p.completed_at.isoformat() if p.completed_at else None
            })
    leaderboard.sort(key=lambda x: x['completed_at'])
    return {"leaderboard": leaderboard[:10]}

# --- Vault & Security 2.0 ---
from vault import vault

@app.post("/api/settings/save-sensitive")
async def save_sensitive(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Example: saving encrypted API key
    key = payload.get("api_key")
    encrypted_key = vault.encrypt(key)
    # In real app, save encrypted_key to UserPreferences or dedicated Vault table
    return {"status": "Encrypted and saved", "preview": encrypted_key[:10] + "..."}

@app.get("/api/settings/retrieve-sensitive")
async def retrieve_sensitive(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Example: retrieve and decrypt
    mock_encrypted = "gAAAAABmT..." # This would come from DB
    try:
        decrypted = vault.decrypt(mock_encrypted)
        return {"data": decrypted}
    except:
        return {"error": "Failed to decrypt"}

# Mount frontend static files after API path registration to avoid swallowing /api routes
if frontend_path:
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend_alias")
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
    print(f"Frontend mounted from: {frontend_path}")

    @app.get("/frontend", include_in_schema=False)
    @app.get("/frontend/", include_in_schema=False)
    async def frontend_index_redirect():
        return RedirectResponse("/")

# Serve index or login page at root if available
@app.get("/", include_in_schema=False)
async def root():
    if frontend_path:
        index_path = os.path.join(frontend_path, "index.html")
        login_path = os.path.join(frontend_path, "login.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        if os.path.exists(login_path):
            return FileResponse(login_path)
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":

    import uvicorn
    # Start Telegram bot in background if available
    if TELEGRAM_BOT_AVAILABLE and dp is not None:
        def run_bot():
            asyncio.run(dp.start_polling())

        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
    else:
        print("Telegram bot not started because aiogram is unavailable or bot initialization failed.")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
