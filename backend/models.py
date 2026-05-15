from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Date
from sqlalchemy.orm import relationship

try:
    from backend.database import Base
except ImportError:
    try:
        from .database import Base
    except ImportError:
        from database import Base

import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    invite_code = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)
    # Security features
    force_logout_at = Column(DateTime, nullable=True)
    is_frozen = Column(Boolean, default=False)
    locked_device_id = Column(Integer, ForeignKey("user_devices.id"), nullable=True)
    # Trial system
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    daily_analyses_count = Column(Integer, default=0)
    last_analysis_date = Column(Date, nullable=True)
    has_used_trial = Column(Boolean, default=False)
    email_change_blocked = Column(Boolean, default=False)
    
    preferences = relationship("UserPreferences", uselist=False, backref="user")
    journal_entries = relationship("JournalEntry", backref="user")
    daily_reports = relationship("DailyReport", backref="user")
    alerts = relationship("Alert", backref="user")


class InviteCode(Base):
    __tablename__ = "invite_codes"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    used_ip = Column(String, nullable=True)
    created_by_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
    max_uses = Column(Integer, default=1)
    uses_count = Column(Integer, default=0)


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    theme = Column(String, default="dark") # dark, light
    language = Column(String, default="ar") # ar, en, tr, zh, es
    telegram_chat_id = Column(String, nullable=True)
    email_notifications = Column(Boolean, default=False)
    demo_mode = Column(Boolean, default=False)
    demo_balance = Column(Float, default=1000000.0)
    # Trading preferences
    trading_mode = Column(String, default="day")  # scalping, day, swing
    capital = Column(Float, default=10000.0)
    account_balance = Column(Float, default=10000.0)
    risk_percentage = Column(Float, default=1.0)
    favorite_strategies = Column(Text, default='[]')
    watchlist = Column(Text, default='[]')
    analysis_locked_until = Column(DateTime, nullable=True)
    trading_locked_until = Column(DateTime, nullable=True)
    # New features 30-34
    daily_profit_target_percent = Column(Float, default=30.0)  # 30% of capital
    daily_loss_limit_percent = Column(Float, default=10.0)    # 10% of capital
    trading_locked_today = Column(Boolean, default=False)
    lock_reason = Column(String, nullable=True)
    notification_markets = Column(Text, default='["XAUUSD", "EURUSD", "GBPUSD"]')  # JSON list
    enable_smart_notifications = Column(Boolean, default=True)
    custom_indicators = Column(Text, default='[]')  # JSON list of indicators


class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market = Column(String)
    image_path = Column(String)
    description = Column(Text)
    result_json = Column(Text) # JSON string of all votes
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market = Column(String)
    recommendation = Column(String)
    confidence = Column(Integer)
    entry = Column(String, nullable=True)
    sl = Column(String, nullable=True)
    tp = Column(String, nullable=True)
    top_strategies = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PriceAlert(Base):
    __tablename__ = "price_alerts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market = Column(String, index=True)
    target_price = Column(Float)
    direction = Column(String, default="above")
    active = Column(Boolean, default=True)
    message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)


class TradeSlippageLog(Base):
    __tablename__ = "trade_slippage_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market = Column(String)
    expected_price = Column(Float, nullable=True)
    executed_price = Column(Float, nullable=True)
    slippage = Column(Float, nullable=True)
    trade_id = Column(Integer, ForeignKey("shadow_trades.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class JournalEntry(Base):
    __tablename__ = "journal"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, default=datetime.datetime.utcnow)
    market = Column(String)
    recommendation = Column(String) # Buy, Sell
    result = Column(String) # Win, Loss
    profit_loss = Column(Float) # USD
    confidence = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    screenshot_url = Column(String, nullable=True)
    mood = Column(String, nullable=True) # optimistic, pessimistic
    session = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DailyReport(Base):
    __tablename__ = "daily_reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    report_date = Column(Date, nullable=False)
    summary = Column(Text, nullable=False)
    total_trades = Column(Integer, default=0)
    entered_trades = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    profit_loss = Column(Float, default=0.0)
    sent_to_telegram = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class StrategyPerformance(Base):
    __tablename__ = "strategy_performance"
    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String, unique=True)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    total_profit = Column(Float, default=0.0)
    last_updated = Column(DateTime, nullable=True)


class TradeExperience(Base):
    __tablename__ = "trade_experience"
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market = Column(String)
    session = Column(String, nullable=True)
    recommendation = Column(String)
    result = Column(String)
    profit_loss = Column(Float, default=0.0)
    strategy_names = Column(Text, nullable=True)
    chart_features = Column(Text, nullable=True)
    news_sentiment = Column(Float, nullable=True)
    pattern_signature = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    trades_count = Column(Integer)
    win_rate = Column(Float)
    best_market = Column(String)
    best_strategy = Column(String)
    total_pnl = Column(Float)
    report_json = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class PsychologyLog(Base):
    __tablename__ = "psychology_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_type = Column(String) # revenge_trading, excessive_trading, over_leveraging
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ShadowTrade(Base):
    __tablename__ = "shadow_trades"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    status = Column(String, default="open") # open, closed
    pnl = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SecurityLog(Base):
    __tablename__ = "security_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String) # session_expired, failed_login, unauthorized_access
    ip_address = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class UserDevice(Base):
    __tablename__ = "user_devices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_id = Column(String, index=True)
    device_name = Column(String, nullable=True)
    is_trusted = Column(Boolean, default=False)
    first_seen = Column(DateTime, default=datetime.datetime.utcnow)


class UserActivityMaster(Base):
    __tablename__ = "user_activity_master"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String)
    ip = Column(String, nullable=True)
    device = Column(String, nullable=True)
    location = Column(String, nullable=True)
    is_vpn = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class DraftAnalysis(Base):
    __tablename__ = "draft_analyses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    market = Column(String)
    image_path = Column(String, nullable=True)
    description = Column(Text)
    payload_json = Column(Text)  # Draft payload
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class WeeklyChallenge(Base):
    __tablename__ = "weekly_challenges"
    id = Column(Integer, primary_key=True, index=True)
    week_start = Column(Date, nullable=False)
    challenge_type = Column(String)  # "trades_on_market", "success_rate", "profit_target"
    target_value = Column(Float)  # e.g., 5 trades, 70% rate, $500 profit
    market = Column(String, nullable=True)  # for trades_on_market
    description = Column(Text)
    reward_type = Column(String)  # "free_analysis", "badge"
    reward_description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UserChallengeProgress(Base):
    __tablename__ = "user_challenge_progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    challenge_id = Column(Integer, ForeignKey("weekly_challenges.id"))
    current_value = Column(Float, default=0.0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
