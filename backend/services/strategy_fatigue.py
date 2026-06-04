import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from database import SessionLocal
    import models
    from models import StrategyPerformance, TradeExperience
    _DB_AVAILABLE = True
except Exception:
    SessionLocal = None
    models = None
    StrategyPerformance = None
    TradeExperience = None
    _DB_AVAILABLE = False

logger = logging.getLogger(__name__)

_MEMORY_DIR = Path(__file__).resolve().parent.parent / "_evolved" / "memory"
_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
_MEMORY_FILE = _MEMORY_DIR / "strategy_fatigue_memory.json"


def _round(value: float, digits: int = 4) -> float:
    try:
        return round(float(value), digits)
    except Exception:
        return 0.0


def _safe_ratio(numerator: float, denominator: float) -> float:
    try:
        return float(numerator) / float(denominator) if denominator else 0.0
    except Exception:
        return 0.0


class StrategyFatigue:
    """Strategy Fatigue Index service.

    يحسب المؤشر بناءً على انتهاج ربح تقلصي، تأخر الدخول، وتراجع نسبة النجاح.
    يوفر تحذيرات مبكرة، قرار التجميد، وتطور استباقي مع Strategy Generator.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.memory_path = Path(storage_path) if storage_path else _MEMORY_FILE
        self.memory: Dict[str, Any] = {}
        self._load_memory()

    def _load_memory(self) -> None:
        if self.memory_path.exists():
            try:
                with open(self.memory_path, "r", encoding="utf-8") as fp:
                    self.memory = json.load(fp)
            except Exception:
                self.memory = {}
        else:
            self.memory = {}

    def _save_memory(self) -> None:
        try:
            with open(self.memory_path, "w", encoding="utf-8") as fp:
                json.dump(self.memory, fp, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save strategy fatigue memory: {e}")

    def _record_evaluation(self, strategy_name: str, evaluation: Dict[str, Any]) -> None:
        self.memory[strategy_name] = {
            "last_evaluated": datetime.now(timezone.utc).isoformat(),
            **evaluation,
        }
        self._save_memory()

    def _build_fallback_history(self, strategy_name: str) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        demo = []
        for i in range(1, 22):
            profit = 0.8 - 0.03 * i
            result = "Win" if i % 3 != 0 else "Loss"
            notes = "delay" if i % 5 == 0 else ""
            demo.append({
                "created_at": now - timedelta(days=i),
                "result": result,
                "profit_loss": profit if result == "Win" else -abs(profit),
                "notes": notes,
            })
        return demo

    def _safe_datetime(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except Exception:
            return datetime.now(timezone.utc)

    def _load_trade_history(self, strategy_name: str) -> List[Dict[str, Any]]:
        trades: List[Dict[str, Any]] = []
        if not _DB_AVAILABLE:
            return self._build_fallback_history(strategy_name)

        db = SessionLocal()
        try:
            query = db.query(TradeExperience)
            query = query.filter(TradeExperience.strategy_names.like(f"%{strategy_name}%"))
            experiences = query.order_by(TradeExperience.created_at.desc()).limit(200).all()
            for t in experiences:
                trades.append({
                    "created_at": self._safe_datetime(t.created_at),
                    "result": str(t.result or "").title(),
                    "profit_loss": float(t.profit_loss or 0.0),
                    "notes": str(t.notes or ""),
                    "chart_features": str(t.chart_features or ""),
                })
        except Exception as e:
            logger.warning(f"Failed to load trade history for {strategy_name}: {e}")
            trades = self._build_fallback_history(strategy_name)
        finally:
            db.close()

        if not trades:
            trades = self._build_fallback_history(strategy_name)

        return trades

    def _load_strategy_performance(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        if not _DB_AVAILABLE:
            return None

        db = SessionLocal()
        try:
            perf = db.query(StrategyPerformance).filter_by(strategy_name=strategy_name).first()
            if not perf:
                return None
            return {
                "wins": int(perf.wins or 0),
                "losses": int(perf.losses or 0),
                "total_profit": float(perf.total_profit or 0.0),
                "last_updated": self._safe_datetime(perf.last_updated) if perf.last_updated else None,
            }
        except Exception as e:
            logger.warning(f"Failed to load performance summary for {strategy_name}: {e}")
            return None
        finally:
            db.close()

    def _score_success_rate_decay(self, trades: List[Dict[str, Any]]) -> float:
        if len(trades) < 9:
            return 0.0

        sorted_trades = sorted(trades, key=lambda x: x["created_at"], reverse=True)
        window = max(3, len(sorted_trades) // 3)
        groups = [sorted_trades[i:i + window] for i in range(0, min(len(sorted_trades), window * 3), window)]
        if len(groups) < 3 or any(len(g) < 2 for g in groups):
            return 0.0

        rates = []
        for group in groups[:3]:
            wins = sum(1 for t in group if "win" in str(t.get("result", "")).lower())
            rates.append(_safe_ratio(wins, len(group)) * 100)

        decay = 0.0
        if rates[0] < rates[1]:
            decay += rates[1] - rates[0]
        if rates[1] < rates[2]:
            decay += rates[2] - rates[1]

        return min(1.0, decay / 30.0)

    def _score_profit_compression(self, trades: List[Dict[str, Any]]) -> float:
        profits = [t.get("profit_loss", 0.0) for t in trades if t.get("profit_loss") is not None]
        wins = [p for p in profits if p > 0]
        if len(wins) < 4:
            return 0.0

        mid = max(1, len(wins) // 2)
        recent = wins[:mid]
        previous = wins[mid: mid * 2]
        if not previous:
            return 0.0

        recent_avg = sum(recent) / len(recent)
        previous_avg = sum(previous) / len(previous)
        if previous_avg <= 0.0:
            return 0.0

        compression = max(0.0, (previous_avg - recent_avg) / previous_avg)
        return min(1.0, compression * 2.0)

    def _score_late_entry(self, trades: List[Dict[str, Any]]) -> float:
        wins = [t for t in trades if t.get("profit_loss", 0.0) > 0]
        if not wins:
            return 0.0

        small_wins = [t for t in wins if 0.0 < t.get("profit_loss", 0.0) < 0.5]
        ratio = _safe_ratio(len(small_wins), len(wins))
        notes = " ".join(str(t.get("notes", "")) for t in trades[-20:] if t.get("notes"))
        delay_flag = 1.0 if re.search(r"late|delay|slow|late entry|تأخر", notes, re.IGNORECASE) else 0.0

        score = min(1.0, ratio + 0.2 * delay_flag)
        return score

    def calculate_fatigue(self, strategy_name: str) -> Dict[str, Any]:
        trades = self._load_trade_history(strategy_name)
        performance = self._load_strategy_performance(strategy_name)

        success_decay = self._score_success_rate_decay(trades)
        profit_compression = self._score_profit_compression(trades)
        late_entry = self._score_late_entry(trades)

        fatigue_index = _round(
            min(100.0, 100.0 * (
                success_decay * 0.45 +
                profit_compression * 0.35 +
                late_entry * 0.20
            ))
        )

        reason_fragments: List[str] = []
        if success_decay >= 0.2:
            reason_fragments.append("نسبة النجاح تتراجع تدريجياً")
        if profit_compression >= 0.2:
            reason_fragments.append("الأرباح تتقلص قبل أن تتحول خسائر")
        if late_entry >= 0.3:
            reason_fragments.append("علامات تأخر الدخول واضحة")

        summary = {
            "strategy_name": strategy_name,
            "fatigue_index": fatigue_index,
            "success_rate_decay": _round(success_decay),
            "profit_compression": _round(profit_compression),
            "late_entry": _round(late_entry),
            "recent_trades": len(trades),
            "total_wins": sum(1 for t in trades if t.get("profit_loss", 0.0) > 0),
            "total_losses": sum(1 for t in trades if t.get("profit_loss", 0.0) <= 0),
            "reason": "، ".join(reason_fragments) if reason_fragments else "لا توجد علامات تعب قوية حتى الآن.",
            "performance_summary": performance or {},
        }

        self._record_evaluation(strategy_name, summary)
        return summary

    def detect_early_warning(self, strategy_name: str) -> Dict[str, Any]:
        fatigue = self.calculate_fatigue(strategy_name)
        warnings: List[str] = []
        if fatigue["success_rate_decay"] >= 0.15:
            warnings.append("انخفاض تدريجي في معدل النجاح خلال الأسبوعين الأخيرين")
        if fatigue["profit_compression"] >= 0.15:
            warnings.append("تقلص الأرباح يسبق بدء فترة خسائر")
        if fatigue["late_entry"] >= 0.25:
            warnings.append("تأخر دخول الصفقات يظهر ضعفا في تفاعل الاستراتيجية")

        fatigue["warnings"] = warnings
        fatigue["is_warning"] = bool(warnings)
        fatigue["should_freeze"] = self.should_freeze(strategy_name, fatigue)
        fatigue["reason"] = fatigue["reason"] if warnings else "المؤشر طبيعي حالياً"
        return fatigue

    def should_freeze(self, strategy_name: str, fatigue_summary: Optional[Dict[str, Any]] = None) -> bool:
        if fatigue_summary is None:
            fatigue_summary = self.calculate_fatigue(strategy_name)

        if fatigue_summary["fatigue_index"] >= 65:
            return True
        if fatigue_summary["success_rate_decay"] >= 0.35:
            return True
        if fatigue_summary["profit_compression"] >= 0.4:
            return True
        return False

    def _find_strategy_path(self, strategy_name: str) -> Optional[Path]:
        backend_dir = Path(__file__).resolve().parent.parent
        search_dirs = [backend_dir / "strategies", backend_dir / "frozen", backend_dir / "_evolved"]
        for root in search_dirs:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if path.stem == strategy_name:
                    return path
        return None

    def proactive_evolution(
        self,
        strategy_name: str,
        reason: Optional[str] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        summary = self.detect_early_warning(strategy_name)
        action = "monitor"
        details = {
            "strategy_name": strategy_name,
            "fatigue_index": summary["fatigue_index"],
            "reason": reason or summary.get("reason"),
            "warnings": summary.get("warnings", []),
        }

        if not self.should_freeze(strategy_name, summary):
            details["action"] = action
            return details

        action = "proactive_evolution"
        details["action"] = action
        details["should_freeze"] = True
        details["freeze_reason"] = details["reason"]

        strategy_path = self._find_strategy_path(strategy_name)
        if not strategy_path:
            details["error"] = f"لم يتم العثور على ملف الاستراتيجية {strategy_name} في المجلدات المتوقعة."
            logger.warning(details["error"])
            return details

        failure_report = {
            "type": "strategy_fatigue",
            "reason": details["freeze_reason"],
            "time": datetime.now(timezone.utc).isoformat(),
        }

        try:
            from .strategy_generator import generate_from_failure
        except Exception as e:
            details["error"] = f"Strategy Generator unavailable: {e}"
            return details

        try:
            generated_code, saved_path = generate_from_failure(
                failed_strategy_path=str(strategy_path),
                failure_report=failure_report,
                top_successful_strategies=[],
                market_data=market_data,
            )
            details["generated_path"] = str(saved_path)
            details["generated_code_snippet"] = generated_code[:280]
            details["status"] = "generated"
        except Exception as e:
            details["error"] = f"Failed to generate proactive replacement: {e}"
            logger.error(details["error"])

        try:
            from .internal_brain import InternalBrain
            InternalBrain().log_event_experience(
                "strategy_fatigue",
                "proactive_evolution",
                strategy_name,
                float(summary["fatigue_index"]),
                {"reason": details["freeze_reason"]},
                success=False,
            )
        except Exception:
            pass

        self._record_evaluation(strategy_name, details)
        return details


strategy_fatigue = StrategyFatigue()
