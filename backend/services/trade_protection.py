from datetime import datetime, timedelta
import math
from typing import Dict, List, Optional

from database import SessionLocal
import models
from .telegram_service import telegram_service
from .binance_service import BinanceService
from .performance_tracker import PerformanceTracker


def _normalize_result(result: str) -> str:
    token = str(result or "").strip().lower()
    if token.startswith("win") or token.startswith("رابح") or token.startswith("ربح"):
        return "Win"
    if token.startswith("loss") or token.startswith("خاسر") or token.startswith("خسارة"):
        return "Loss"
    return "Pending"


class TradeProtectionService:
    def __init__(self):
        self.market_service = BinanceService()
        self.performance_tracker = PerformanceTracker()

    def _get_user_preferences(self, db, user_id: int) -> Optional[models.UserPreferences]:
        prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == user_id).first()
        if prefs is None:
            prefs = models.UserPreferences(user_id=user_id)
            db.add(prefs)
            db.commit()
            db.refresh(prefs)
        return prefs

    def _end_of_day(self) -> datetime:
        now = datetime.utcnow()
        return datetime(now.year, now.month, now.day, 23, 59, 59)

    def _compute_daily_loss(self, db, user_id: int) -> float:
        # Compute today's net P&L from TradeExperience entries (preferred over Journal)
        today = datetime.utcnow().date()
        start = datetime(today.year, today.month, today.day)
        entries = db.query(models.TradeExperience).filter(
            models.TradeExperience.user_id == user_id,
            models.TradeExperience.created_at >= start
        ).all()
        # profit_loss expected to be positive for profit, negative for loss
        return sum(float(e.profit_loss or 0.0) for e in entries)

    def _has_three_consecutive_losses(self, db, user_id: int) -> bool:
        recent = db.query(models.JournalEntry).filter(models.JournalEntry.user_id == user_id).order_by(models.JournalEntry.date.desc()).limit(3).all()
        if len(recent) < 3:
            return False
        results = [_normalize_result(entry.result) for entry in recent]
        return results == ["Loss", "Loss", "Loss"]

    def _symbol_correlation(self, symbol_a: str, symbol_b: str) -> float:
        if not symbol_a or not symbol_b or symbol_a == symbol_b:
            return 0.0

        klines_a = self.market_service.get_klines(symbol_a, interval="1h", limit=40)
        klines_b = self.market_service.get_klines(symbol_b, interval="1h", limit=40)
        closes_a = [float(k[4]) for k in klines_a if isinstance(k, list) and len(k) >= 5]
        closes_b = [float(k[4]) for k in klines_b if isinstance(k, list) and len(k) >= 5]
        n = min(len(closes_a), len(closes_b))
        if n < 10:
            return 0.0

        if len(closes_a) != len(closes_b):
            closes_a = closes_a[-n:]
            closes_b = closes_b[-n:]

        returns_a = [(closes_a[i] - closes_a[i - 1]) / closes_a[i - 1] for i in range(1, len(closes_a)) if closes_a[i - 1] != 0]
        returns_b = [(closes_b[i] - closes_b[i - 1]) / closes_b[i - 1] for i in range(1, len(closes_b)) if closes_b[i - 1] != 0]
        n = min(len(returns_a), len(returns_b))
        if n < 8:
            return 0.0

        returns_a = returns_a[-n:]
        returns_b = returns_b[-n:]
        mean_a = sum(returns_a) / n
        mean_b = sum(returns_b) / n
        cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(returns_a, returns_b)) / n
        var_a = sum((a - mean_a) ** 2 for a in returns_a) / n
        var_b = sum((b - mean_b) ** 2 for b in returns_b) / n
        if var_a <= 0 or var_b <= 0:
            return 0.0
        corr = cov / math.sqrt(var_a * var_b)
        return round(corr, 3)

    def _correlation_pairs(self, open_trades: List[models.ShadowTrade], new_market: Optional[str] = None) -> List[Dict[str, object]]:
        warnings = []
        if new_market:
            for trade in open_trades:
                if trade.market and trade.market.upper() != new_market.upper():
                    corr = self._symbol_correlation(trade.market.upper(), new_market.upper())
                    if abs(corr) > 0.8:
                        warnings.append({
                            "pairs": [trade.market, new_market],
                            "correlation": corr,
                            "message": f"صفقتين مترابطتين ({trade.market} + {new_market}) = مخاطرة مضاعفة. اختر الأقوى فقط."
                        })
        else:
            for i in range(len(open_trades)):
                for j in range(i + 1, len(open_trades)):
                    a = open_trades[i].market
                    b = open_trades[j].market
                    if a and b and a.upper() != b.upper():
                        corr = self._symbol_correlation(a.upper(), b.upper())
                        if abs(corr) > 0.8:
                            warnings.append({
                                "pairs": [a, b],
                                "correlation": corr,
                                "message": f"صفقتين مترابطتين ({a} + {b}) = مخاطرة مضاعفة. اختر الأقوى فقط."
                            })
        return warnings

    def _update_protection_states(self, db, user_id: int) -> Dict[str, object]:
        user_prefs = self._get_user_preferences(db, user_id)
        if not user_prefs:
            return {
                "analysis_locked": False,
                "trading_locked": False,
                "analysis_locked_until": None,
                "trading_locked_until": None,
                "analysis_message": None,
                "trading_message": None,
                "daily_drawdown_pct": 0.0,
                "weekly_drawdown_pct": 0.0,
            }

        now = datetime.utcnow()
        changed = False
        if user_prefs.analysis_locked_until and user_prefs.analysis_locked_until <= now:
            user_prefs.analysis_locked_until = None
            changed = True

        if user_prefs.trading_locked_until and user_prefs.trading_locked_until <= now:
            user_prefs.trading_locked_until = None
            changed = True

        daily_loss = self._compute_daily_loss(db, user_id)
        capital = float(user_prefs.capital or 10000.0)
        daily_drawdown_pct = round(max(0.0, -daily_loss / capital * 100.0), 2)

        # If absolute daily loss amount is set, use it; otherwise compute from percent
        if user_prefs.daily_loss_limit_amount and user_prefs.daily_loss_limit_amount > 0:
            daily_loss_limit_amount = float(user_prefs.daily_loss_limit_amount)
            daily_loss_limit = daily_loss_limit_amount
            daily_loss_limit_pct = round(daily_loss_limit_amount / max(1.0, capital) * 100.0, 2)
        else:
            daily_loss_limit_pct = float(user_prefs.daily_loss_limit_percent or 5.0)
            daily_loss_limit = capital * (daily_loss_limit_pct / 100.0)

        # If drawdown crosses hard limit, lock trading for rest of the day and notify
        if daily_loss <= -daily_loss_limit and not user_prefs.trading_locked_today:
            user_prefs.trading_locked_today = True
            user_prefs.lock_reason = "تم إيقاف التداول اليوم. الخسائر تجاوزت الحد المسموح."
            # create an alert record and psychology log
            try:
                db.add(models.Alert(
                    user_id=user_id,
                    market=None,
                    recommendation="",
                    confidence=0,
                    entry=None,
                    sl=None,
                    tp=None,
                    top_strategies=None,
                ))
            except Exception:
                pass
            db.add(models.PsychologyLog(
                user_id=user_id,
                event_type="daily_loss_limit_locked",
                description=f"تم إيقاف التداول لليوم بعد خسارة {abs(round(daily_loss,2))}$ (الحد: {round(daily_loss_limit,2)}$)."
            ))
            # send telegram if configured
            try:
                if user_prefs.telegram_chat_id:
                    telegram_service.send_message(user_prefs.telegram_chat_id, "تم إيقاف التداول اليوم. الخسائر تجاوزت الحد المسموح.")
            except Exception:
                pass
            changed = True

        # Handle profit target similarly (existing behavior)
        daily_profit_target = capital * (float(user_prefs.daily_profit_target_percent or 30.0) / 100.0)
        if daily_loss >= daily_profit_target and not user_prefs.trading_locked_today:
            user_prefs.trading_locked_today = True
            user_prefs.lock_reason = f"🎉 حققت هدفك اليومي {user_prefs.daily_profit_target_percent}%. تداولك متوقف لليوم"
            changed = True

        if self._has_three_consecutive_losses(db, user_id) and not user_prefs.analysis_locked_until:
            user_prefs.analysis_locked_until = now + timedelta(hours=1)
            db.add(models.PsychologyLog(
                user_id=user_id,
                event_type="consecutive_losses_lock",
                description="خسرت 3 صفقات متتالية. تم قفل التحليل لمدة ساعة."
            ))
            changed = True

        if changed:
            db.commit()
            db.refresh(user_prefs)

        weekly_drawdown = self.performance_tracker.summarize_performance(user_id, lookback_days=7).get("max_drawdown", 0.0)
        today_drawdown = self.performance_tracker.summarize_performance(user_id, lookback_days=1).get("max_drawdown", 0.0)

        return {
            "analysis_locked": bool(user_prefs.analysis_locked_until and user_prefs.analysis_locked_until > now),
            "trading_locked": bool(user_prefs.trading_locked_until and user_prefs.trading_locked_until > now),
            "analysis_locked_until": user_prefs.analysis_locked_until.isoformat() if user_prefs.analysis_locked_until else None,
            "trading_locked_until": user_prefs.trading_locked_until.isoformat() if user_prefs.trading_locked_until else None,
            "analysis_message": "خسرت 3 صفقات متتالية. خذ استراحة" if (user_prefs.analysis_locked_until and user_prefs.analysis_locked_until > now) else None,
            "trading_message": ("تم إيقاف التداول اليوم. الخسائر تجاوزت الحد المسموح." if user_prefs.trading_locked_today else ("وصلت حد الخسارة اليومية {}%. تداولك متوقف لليوم".format(user_prefs.daily_loss_limit_percent) if (user_prefs.trading_locked_until and user_prefs.trading_locked_until > now) else None)),
            "daily_drawdown_pct": today_drawdown,
            "weekly_drawdown_pct": weekly_drawdown,
            "daily_loss_usd": round(daily_loss, 2),
            "daily_loss_limit_pct": float(user_prefs.daily_loss_limit_percent or 5.0),
            "daily_loss_limit_amount": float(user_prefs.daily_loss_limit_amount) if user_prefs.daily_loss_limit_amount else None,
        }

    def refresh_protection(self, user_id: int) -> Dict[str, object]:
        db = SessionLocal()
        try:
            return self._update_protection_states(db, user_id)
        finally:
            db.close()

    def check_protection(self, user_id: int) -> Dict[str, object]:
        status = self.refresh_protection(user_id)
        return status

    def correlation_warning(self, user_id: int, market: Optional[str] = None) -> Optional[Dict[str, object]]:
        db = SessionLocal()
        try:
            open_trades = db.query(models.ShadowTrade).filter(models.ShadowTrade.user_id == user_id, models.ShadowTrade.status == "open").all()
            if not open_trades:
                return None
            warnings = self._correlation_pairs(open_trades, new_market=market)
            if warnings:
                top = sorted(warnings, key=lambda item: abs(item["correlation"]), reverse=True)[0]
                return top
            return None
        finally:
            db.close()

    def get_open_correlation_warnings(self, user_id: int) -> List[Dict[str, object]]:
        db = SessionLocal()
        try:
            open_trades = db.query(models.ShadowTrade).filter(models.ShadowTrade.user_id == user_id, models.ShadowTrade.status == "open").all()
            return self._correlation_pairs(open_trades)
        finally:
            db.close()


trade_protection_service = TradeProtectionService()
