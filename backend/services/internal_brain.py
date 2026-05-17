import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

try:
    from database import SessionLocal
    import models
    from models import StrategyPerformance
except ImportError:
    from database import SessionLocal
    import models
    from models import StrategyPerformance

from .performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)

class InternalBrain:
    def __init__(self):
        self.default_weight = 1.0
        # updated bounds per request
        self.min_weight = 0.3
        self.max_weight = 3.0
        self.performance_tracker = PerformanceTracker()
        # studied default weights; crypto default is lower for Forex context
        self.default_weight_map = {
            'ICT': 1.5,
            'VSA': 1.3,
            'PriceAction': 1.3,
            'RSI': 1.0,
            'MACD': 1.0,
            'RSI/MACD': 1.0,
            'Elliott': 0.8,
            'crypto': 0.5,
        }

    def _get_db_session(self) -> Session:
        return SessionLocal()

    def get_strategy_weights(self, user_id: Optional[int] = None) -> Dict[str, float]:
        weights = {}
        db = self._get_db_session()
        try:
            records = db.query(StrategyPerformance).all()
            session_multiplier = 1.0
            pattern_penalties = {}

            if user_id is not None:
                try:
                    user_perf = self.performance_tracker.summarize_performance(user_id, lookback_days=90)
                    session_multiplier = float(user_perf.get("current_session_boost", 1.0))
                    if user_perf.get("win_rate", 0.0) < 40.0:
                        session_multiplier *= 0.9
                    pattern_penalties = self._load_recent_penalties(user_id)
                except Exception as e:
                    logger.exception(f"Failed to compute session multiplier for user {user_id}: {e}")

            for record in records:
                score = self._compute_weight(record)
                penalty = pattern_penalties.get(record.strategy_name, 1.0)
                scaled_score = score * session_multiplier * penalty
                weights[record.strategy_name] = round(max(self.min_weight, min(self.max_weight, scaled_score)), 3)
            # ensure studied defaults are present when no historical record exists
            for name, val in self.default_weight_map.items():
                if name not in weights:
                    weights[name] = round(max(self.min_weight, min(self.max_weight, float(val))), 3)
        except Exception as e:
            logger.exception(f"Unable to load strategy weights: {e}")
        finally:
            db.close()
        return weights

    def _load_recent_penalties(self, user_id: int) -> Dict[str, float]:
        db = self._get_db_session()
        penalties = {}
        try:
            rows = db.query(models.TradeExperience).filter(models.TradeExperience.user_id == user_id).order_by(models.TradeExperience.created_at.desc()).limit(50).all()
            recent_losses = [row for row in rows if row.result and row.result.lower().startswith("loss")]
            for row in recent_losses:
                for strategy in (row.strategy_names or "").split(","):
                    name = strategy.strip()
                    if not name:
                        continue
                    penalties[name] = min(penalties.get(name, 1.0), 0.85)
        except Exception as e:
            logger.exception(f"Failed to load recent penalties: {e}")
        finally:
            db.close()
        return penalties

    def record_trade_experience(
        self,
        user_id: int,
        market: str,
        recommendation: str,
        result: str,
        profit_loss: float,
        strategy_names: Optional[str] = None,
        session: Optional[str] = None,
        news_sentiment: Optional[float] = None,
        pattern_signature: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        db = self._get_db_session()
        try:
            experience = models.TradeExperience(
                user_id=user_id,
                market=market,
                session=session,
                recommendation=recommendation,
                result=result,
                profit_loss=profit_loss,
                strategy_names=strategy_names,
                news_sentiment=news_sentiment,
                pattern_signature=pattern_signature,
                notes=notes,
                created_at=datetime.utcnow(),
            )
            db.add(experience)
            db.commit()
            # call weight updater immediately after logging the trade experience
            try:
                # don't raise if update_weights fails; it's best-effort
                self.update_weights(user_id=user_id)
            except Exception:
                logger.exception("update_weights failed after recording trade experience")
        except Exception as e:
            logger.exception(f"Failed to record trade experience: {e}")
            db.rollback()
        finally:
            db.close()

    def _compute_weight(self, record: StrategyPerformance) -> float:
        if record.wins + record.losses == 0:
            # if no history, return a studied default when available
            return self.default_weight_map.get(record.strategy_name, self.default_weight)

        success_ratio = record.wins / max(record.wins + record.losses, 1)
        profit_factor = 1.0 + min(0.3, max(-0.3, record.total_profit / max(abs(record.total_profit), 1.0) * 0.15))
        base_weight = 0.8 + (success_ratio * 1.2)
        weight = base_weight * profit_factor
        return max(self.min_weight, min(self.max_weight, weight))

    def resolve_conflict(self, details: List[Dict], vote_scores: Dict[str, float]) -> Dict[str, object]:
        buy_score = vote_scores.get("شراء", 0)
        sell_score = vote_scores.get("بيع", 0)
        neutral_score = vote_scores.get("محايد", 0)

        if buy_score == sell_score:
            dominant = self._break_tie_by_performance(details)
        else:
            dominant = "شراء" if buy_score > sell_score else "بيع"

        explanation = self._build_conflict_reason(details, dominant, buy_score, sell_score)
        return {"recommendation": dominant, "resolution_reason": explanation}

    def _break_tie_by_performance(self, details: List[Dict]) -> str:
        buy_perf = 0.0
        sell_perf = 0.0
        for item in details:
            if item["vote"] == "شراء":
                buy_perf += item.get("weight", self.default_weight)
            elif item["vote"] == "بيع":
                sell_perf += item.get("weight", self.default_weight)
        if buy_perf == sell_perf:
            top = sorted(details, key=lambda x: x.get("weight", self.default_weight), reverse=True)
            return top[0]["vote"] if top else "محايد"
        return "شراء" if buy_perf > sell_perf else "بيع"

    def _build_conflict_reason(self, details: List[Dict], dominant: str, buy_score: float, sell_score: float) -> str:
        summary = []
        summary.append(f"Conflict resolved toward {dominant} based on weighted strategy performance.")
        if abs(buy_score - sell_score) < 0.3 * max(buy_score, sell_score, 1):
            summary.append("The opposing side had nearly equal support, so performance weights decided the outcome.")
        if dominant == "شراء":
            summary.append("Strong buy frameworks held more live conviction.")
        else:
            summary.append("Strong sell frameworks were more reliable this cycle.")
        return " ".join(summary)

    def boost_confidence(self, recommendation: str, details: List[Dict], base_confidence: int) -> int:
        same_votes = [item for item in details if item["vote"] == recommendation]
        if len(same_votes) >= 5 and base_confidence < 95:
            return min(100, int(base_confidence * 1.12))
        return base_confidence

    def update_strategy_performance(self, strategy_name: str, outcome: str, profit: float = 0.0) -> None:
        db = self._get_db_session()
        try:
            record = db.query(StrategyPerformance).filter_by(strategy_name=strategy_name).first()
            if not record:
                record = StrategyPerformance(strategy_name=strategy_name, wins=0, losses=0, total_profit=0.0)
                db.add(record)

            if outcome == "win":
                record.wins += 1
                record.total_profit += profit
            elif outcome == "loss":
                record.losses += 1
                record.total_profit -= abs(profit)
            db.commit()
        except Exception as e:
            logger.exception(f"Failed to update strategy performance for {strategy_name}: {e}")
            db.rollback()
        finally:
            db.close()

    def learn_from_history(self, historical_results: List[Dict[str, object]]) -> None:
        for result in historical_results:
            try:
                self.update_strategy_performance(
                    strategy_name=result.get("strategy_name", "unknown"),
                    outcome=result.get("outcome", "loss"),
                    profit=float(result.get("profit", 0.0))
                )
            except Exception as e:
                logger.exception(f"Failed to learn from history item {result}: {e}")

    def update_weights(self, user_id: Optional[int] = None, lookback_days: int = 90, min_trades: int = 20) -> Dict[str, object]:
        """Recompute strategy performance weights from recent TradeExperience entries.
        This will only apply updates for strategies with at least `min_trades` observations.
        Called automatically after each logged trade (best-effort).
        """
        db = self._get_db_session()
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        strategy_stats: Dict[str, Dict[str, float]] = {}
        try:
            query = db.query(models.TradeExperience).filter(models.TradeExperience.created_at >= cutoff)
            if user_id is not None:
                query = query.filter(models.TradeExperience.user_id == user_id)
            experiences = query.all()

            for exp in experiences:
                strategy_names = [name.strip() for name in (exp.strategy_names or "").split(",") if name.strip()]
                result = str(exp.result or "").strip().lower()
                for name in strategy_names:
                    stats = strategy_stats.setdefault(name, {"wins": 0, "losses": 0, "profit": 0.0, "trades": 0})
                    stats["trades"] += 1
                    if result.startswith("win") or result.startswith("رابح") or result.startswith("ربح"):
                        stats["wins"] += 1
                        stats["profit"] += float(exp.profit_loss or 0.0)
                    elif result.startswith("loss") or result.startswith("خاسر") or result.startswith("خسارة"):
                        stats["losses"] += 1
                        stats["profit"] -= abs(float(exp.profit_loss or 0.0))

            updated = []
            for name, stats in strategy_stats.items():
                if stats["trades"] < min_trades:
                    continue
                record = db.query(StrategyPerformance).filter_by(strategy_name=name).first()
                if not record:
                    record = StrategyPerformance(strategy_name=name)
                    db.add(record)

                record.wins = int(stats["wins"])
                record.losses = int(stats["losses"])
                record.total_profit = round(float(stats["profit"]), 2)
                record.last_updated = datetime.utcnow()
                updated.append({
                    "strategy_name": name,
                    "trades": stats["trades"],
                    "win_rate": round((float(stats["wins"]) / max(stats["trades"], 1)) * 100.0, 2),
                    "total_profit": round(record.total_profit, 2),
                })

            db.commit()
            return {"updated_strategies": updated, "strategy_count": len(updated)}
        except Exception as e:
            logger.exception(f"Failed to update weights: {e}")
            db.rollback()
            return {"updated_strategies": [], "strategy_count": 0, "error": str(e)}
        finally:
            db.close()

    def auto_update_strategy_performance(self, lookback_days: int = 30, min_trades: int = 5) -> Dict[str, object]:
        # Respect new default: don't learn before 20 trades unless explicitly overridden
        if min_trades < 20:
            min_trades = 20
        db = self._get_db_session()
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        strategy_stats: Dict[str, Dict[str, float]] = {}
        try:
            experiences = db.query(models.TradeExperience).filter(models.TradeExperience.created_at >= cutoff).all()
            for exp in experiences:
                strategy_names = [name.strip() for name in (exp.strategy_names or "").split(",") if name.strip()]
                result = str(exp.result or "").strip().lower()
                for name in strategy_names:
                    stats = strategy_stats.setdefault(name, {"wins": 0, "losses": 0, "profit": 0.0, "trades": 0})
                    stats["trades"] += 1
                    if result.startswith("win") or result.startswith("رابح") or result.startswith("ربح"):
                        stats["wins"] += 1
                        stats["profit"] += float(exp.profit_loss or 0.0)
                    elif result.startswith("loss") or result.startswith("خاسر") or result.startswith("خسارة"):
                        stats["losses"] += 1
                        stats["profit"] -= abs(float(exp.profit_loss or 0.0))

            updated = []
            for name, stats in strategy_stats.items():
                if stats["trades"] < min_trades:
                    continue
                win_rate = float(stats["wins"]) / max(stats["trades"], 1)
                record = db.query(StrategyPerformance).filter_by(strategy_name=name).first()
                if not record:
                    record = StrategyPerformance(strategy_name=name)
                    db.add(record)

                record.wins = int(stats["wins"])
                record.losses = int(stats["losses"])
                record.total_profit = round(float(stats["profit"]), 2)
                if win_rate < 0.4:
                    record.total_profit -= abs(record.total_profit) * 0.05
                record.last_updated = datetime.utcnow()
                updated.append({
                    "strategy_name": name,
                    "trades": stats["trades"],
                    "win_rate": round(win_rate * 100.0, 2),
                    "total_profit": round(record.total_profit, 2),
                })

            db.commit()
            return {"updated_strategies": updated, "strategy_count": len(updated)}
        except Exception as e:
            logger.exception(f"Failed to auto update strategy performance: {e}")
            db.rollback()
            return {"updated_strategies": [], "strategy_count": 0, "error": str(e)}
        finally:
            db.close()
