from datetime import datetime, timedelta
from math import sqrt
from typing import Dict, List

from database import SessionLocal
import models


class PerformanceTracker:
    def _normalize_result(self, result: str) -> str:
        token = str(result or "").strip().lower()
        if token.startswith("win") or token.startswith("رابح") or token.startswith("ربح"):
            return "win"
        if token.startswith("loss") or token.startswith("خاسر") or token.startswith("خسارة"):
            return "loss"
        return "pending"

    def _max_drawdown(self, equity_curve: List[float]) -> float:
        peak = equity_curve[0] if equity_curve else 0.0
        drawdowns = [0.0]
        for value in equity_curve:
            if value > peak:
                peak = value
            drawdowns.append(max(0.0, peak - value))
        return round(max(drawdowns), 2)

    def _sharpe_ratio(self, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        volatility = sqrt(variance) if variance > 0 else 0.0
        if volatility == 0.0:
            return 0.0
        return round((mean_return / volatility) * sqrt(252), 2)

    def _session_name(self, created_at: datetime) -> str:
        hour = created_at.hour
        if 0 <= hour < 2:
            return "جلسة سيدني"
        if 2 <= hour < 10:
            return "جلسة طوكيو"
        if 10 <= hour < 18:
            return "جلسة لندن"
        return "جلسة نيويورك"

    def _best_session(self, entries: List[models.JournalEntry]) -> Dict[str, object]:
        if not entries:
            return {"session": None, "win_rate": 0.0, "trades": 0, "pnl": 0.0}

        sessions = {}
        for entry in entries:
            session = self._session_name(entry.created_at or entry.date or datetime.utcnow())
            stats = sessions.setdefault(session, {"wins": 0, "trades": 0, "pnl": 0.0})
            stats["trades"] += 1
            if self._normalize_result(entry.result) == "win":
                stats["wins"] += 1
            stats["pnl"] += float(entry.profit_loss or 0.0)

        best = None
        best_score = -1.0
        for session, stats in sessions.items():
            if stats["trades"] == 0:
                continue
            win_rate = stats["wins"] / stats["trades"]
            score = win_rate * 100 + (stats["pnl"] / 1000.0)
            if score > best_score:
                best_score = score
                best = {"session": session, "win_rate": round(win_rate * 100, 2), "trades": stats["trades"], "pnl": round(stats["pnl"], 2)}

        return best or {"session": None, "win_rate": 0.0, "trades": 0, "pnl": 0.0}

    def summarize_performance(self, user_id: int, lookback_days: int = 90) -> Dict[str, object]:
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)
            entries = db.query(models.JournalEntry).filter(models.JournalEntry.user_id == user_id, models.JournalEntry.date >= cutoff).order_by(models.JournalEntry.date.asc()).all()

            if not entries:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "average_pnl": 0.0,
                    "profit_factor": 0.0,
                    "sharpe_ratio": 0.0,
                    "max_drawdown": 0.0,
                    "best_session": None,
                    "current_session_boost": 1.0,
                }

            profits = [float(e.profit_loss or 0.0) for e in entries]
            wins = len([e for e in entries if self._normalize_result(e.result) == "win"])
            losses = len([e for e in entries if self._normalize_result(e.result) == "loss"])
            total = len(entries)
            total_pnl = sum(profits)
            avg_pnl = total_pnl / total if total else 0.0
            daily_returns = profits
            sharpe_ratio = self._sharpe_ratio(daily_returns)
            cumulative = 0.0
            equity_curve = []
            for profit in profits:
                cumulative += profit
                equity_curve.append(cumulative)
            max_drawdown = self._max_drawdown(equity_curve)
            winning_pnl = sum(p for p in profits if p > 0)
            losing_pnl = abs(sum(p for p in profits if p < 0))
            profit_factor = round((winning_pnl / losing_pnl) if losing_pnl > 0 else (winning_pnl if winning_pnl > 0 else 0.0), 2)
            best_session = self._best_session(entries)
            current_session = self._session_name(datetime.utcnow())
            session_boost = 1.05 if best_session and best_session.get("session") == current_session and best_session.get("trades", 0) >= 3 else 1.0

            return {
                "total_trades": total,
                "wins": wins,
                "losses": losses,
                "win_rate": round((wins / total) * 100.0, 2) if total else 0.0,
                "total_pnl": round(total_pnl, 2),
                "average_pnl": round(avg_pnl, 2),
                "profit_factor": profit_factor,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "best_session": best_session,
                "current_session_boost": session_boost,
                "average_win": round((winning_pnl / wins) if wins else 0.0, 2),
                "average_loss": round((losing_pnl / losses) if losses else 0.0, 2),
            }
        finally:
            db.close()

    def detect_trade_patterns(self, user_id: int) -> Dict[str, object]:
        db = SessionLocal()
        try:
            experiences = db.query(models.TradeExperience).filter(models.TradeExperience.user_id == user_id).all()
            if not experiences:
                return {
                    "best_sessions": [],
                    "news_correlations": [],
                    "avoid_patterns": []
                }

            session_stats = {}
            news_stats = {}
            pattern_losses = {}

            for exp in experiences:
                session = exp.session or self._session_name(exp.created_at or datetime.utcnow())
                stats = session_stats.setdefault(session, {"wins": 0, "trades": 0, "pnl": 0.0})
                stats["trades"] += 1
                if exp.result and exp.result.lower().startswith("win"):
                    stats["wins"] += 1
                stats["pnl"] += float(exp.profit_loss or 0.0)

                if exp.news_sentiment is not None:
                    key = "positive" if exp.news_sentiment > 0.2 else "negative" if exp.news_sentiment < -0.2 else "neutral"
                    bucket = news_stats.setdefault(key, {"wins": 0, "trades": 0, "pnl": 0.0})
                    bucket["trades"] += 1
                    if exp.result and exp.result.lower().startswith("win"):
                        bucket["wins"] += 1
                    bucket["pnl"] += float(exp.profit_loss or 0.0)

                if exp.pattern_signature and exp.result and exp.result.lower().startswith("loss"):
                    pattern_losses[exp.pattern_signature] = pattern_losses.get(exp.pattern_signature, 0) + 1

            best_sessions = []
            for session, stats in session_stats.items():
                if stats["trades"] >= 2:
                    win_rate = stats["wins"] / stats["trades"]
                    best_sessions.append({
                        "session": session,
                        "win_rate": round(win_rate * 100, 2),
                        "trades": stats["trades"],
                        "pnl": round(stats["pnl"], 2)
                    })
            best_sessions.sort(key=lambda x: (x["win_rate"], x["pnl"]), reverse=True)

            news_correlations = []
            for key, bucket in news_stats.items():
                win_rate = bucket["wins"] / max(bucket["trades"], 1)
                news_correlations.append({
                    "sentiment": key,
                    "win_rate": round(win_rate * 100, 2),
                    "trades": bucket["trades"],
                    "pnl": round(bucket["pnl"], 2)
                })
            news_correlations.sort(key=lambda x: x["win_rate"], reverse=True)

            avoid_patterns = [
                {"pattern_signature": sig, "loss_count": count}
                for sig, count in pattern_losses.items() if count >= 3
            ]

            return {
                "best_sessions": best_sessions[:3],
                "news_correlations": news_correlations[:3],
                "avoid_patterns": avoid_patterns,
            }
        finally:
            db.close()

    def get_strategy_trends(self, top_n: int = 5) -> Dict[str, object]:
        db = SessionLocal()
        try:
            records = db.query(models.StrategyPerformance).order_by(models.StrategyPerformance.total_profit.desc()).limit(top_n).all()
            return {
                "top_strategies": [
                    {
                        "strategy_name": r.strategy_name,
                        "wins": r.wins,
                        "losses": r.losses,
                        "total_profit": round(float(r.total_profit or 0.0), 2),
                        "win_rate": round((r.wins / max(r.wins + r.losses, 1)) * 100.0, 2),
                    }
                    for r in records
                ]
            }
        finally:
            db.close()

    def current_session_boost(self, user_id: int) -> float:
        performance = self.summarize_performance(user_id, lookback_days=90)
        return float(performance.get("current_session_boost", 1.0))
