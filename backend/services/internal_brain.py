import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
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

# مسار الذاكرة السريعة (JSON)
_MEMORY_DIR = Path(__file__).resolve().parent.parent / "_evolved" / "memory"
_MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class InternalBrain:
    """
    العقل المركزي لنظام VisionTrader AI
    يجمع خبرات كافة المكونات ويوزعها ويتعلم منها يومياً
    
    Global Memory يسجل:
    - أداء الوكلاء (Agent Accuracy)
    - تأثير الأخبار (News Impact)
    - أخطاء الكود (Code Errors)
    - سرعة الإصلاح (Fix Speed)
    - تفضيلات التنبيهات (Alert Preferences)
    """
    
    def __init__(self):
        self.default_weight = 1.0
        self.min_weight = 0.3
        self.max_weight = 3.0
        self.performance_tracker = PerformanceTracker()
        # أوزان افتراضية مدروسة
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
        # ذاكرة سريعة محلية (JSON cache)
        self._memory_cache: Dict[str, Any] = {}
        self._load_memory_cache()
    
    # ═══════════════════════════════════════════════════════════
    #  الذاكرة السريعة (JSON Fast Memory)
    # ═══════════════════════════════════════════════════════════
    
    def _get_memory_path(self, component: str) -> Path:
        """الحصول على مسار ملف الذاكرة لمكون معين"""
        return _MEMORY_DIR / f"{component}_memory.json"
    
    def _load_memory_cache(self):
        """تحميل كل ملفات الذاكرة في الكاش المحلي"""
        try:
            for f in _MEMORY_DIR.glob("*_memory.json"):
                component = f.stem.replace("_memory", "")
                with open(f, "r", encoding="utf-8") as fp:
                    self._memory_cache[component] = json.load(fp)
        except Exception as e:
            logger.warning(f"فشل تحميل الذاكرة السريعة: {e}")
    
    def _save_component_memory(self, component: str, data: Dict):
        """حفظ ذاكرة مكون في ملف JSON"""
        try:
            path = self._get_memory_path(component)
            self._memory_cache[component] = data
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"فشل حفظ ذاكرة {component}: {e}")
    
    def get_component_memory(self, component: str) -> Dict:
        """قراءة ذاكرة مكون من الكاش"""
        if component not in self._memory_cache:
            path = self._get_memory_path(component)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as fp:
                        self._memory_cache[component] = json.load(fp)
                except Exception:
                    self._memory_cache[component] = {}
            else:
                self._memory_cache[component] = {}
        return self._memory_cache.get(component, {})
    
    # ═══════════════════════════════════════════════════════════
    #  نظام تسجيل الأحداث (Event Experience Logging)
    # ═══════════════════════════════════════════════════════════
    
    def log_event_experience(
        self,
        component: str,
        event_type: str,
        event_key: str,
        event_value: float = 0.0,
        metadata: Optional[Dict] = None,
        context: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """
        تسجيل حدث في الذاكرة العالمية
        
        Args:
            component: اسم المكون (agent_manager, news_adapter, etc.)
            event_type: نوع الحدث (agent_accuracy, news_impact, fix_applied, etc.)
            event_key: مفتاح فرعي (اسم الوكيل، الكلمة المفتاحية، إلخ)
            event_value: القيمة الرقمية
            metadata: بيانات إضافية
            context: سياق الحدث
            success: هل نجح الحدث
        """
        # 1. حفظ في قاعدة البيانات
        db = self._get_db_session()
        try:
            event = models.GlobalMemoryEvent(
                component=component,
                event_type=event_type,
                event_key=event_key,
                event_value=event_value,
                metadata_json=json.dumps(metadata or {}, ensure_ascii=False, default=str),
                context=context,
                success=success,
                created_at=datetime.utcnow(),
            )
            db.add(event)
            db.commit()
        except Exception as e:
            logger.error(f"فشل تسجيل حدث في الذاكرة العالمية: {e}")
            db.rollback()
        finally:
            db.close()
        
        # 2. تحديث الذاكرة السريعة
        mem = self.get_component_memory(component)
        events_list = mem.setdefault("events", [])
        events_list.append({
            "type": event_type,
            "key": event_key,
            "value": event_value,
            "success": success,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # الاحتفاظ بآخر 500 حدث فقط
        if len(events_list) > 500:
            events_list[:] = events_list[-500:]
        self._save_component_memory(component, mem)
    
    # ═══════════════════════════════════════════════════════════
    #  العتبات الديناميكية (Dynamic Thresholds)
    # ═══════════════════════════════════════════════════════════
    
    def get_dynamic_threshold(
        self,
        component: str,
        threshold_name: str,
        default_value: float,
        lookback_days: int = 30,
    ) -> float:
        """
        الحصول على عتبة ديناميكية تتكيف مع أداء النظام
        
        العتبة تتغير بناءً على:
        - نسبة نجاح الأحداث الأخيرة
        - معدل القيمة للأحداث الأخيرة
        
        Args:
            component: اسم المكون
            threshold_name: اسم العتبة (deployment_threshold, max_drawdown, etc.)
            default_value: القيمة الافتراضية
            lookback_days: عدد أيام الرجوع
        
        Returns:
            العتبة المعدلة ديناميكياً
        """
        db = self._get_db_session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=lookback_days)
            events = db.query(models.GlobalMemoryEvent).filter(
                models.GlobalMemoryEvent.component == component,
                models.GlobalMemoryEvent.event_type == threshold_name,
                models.GlobalMemoryEvent.created_at >= cutoff,
            ).all()
            
            if not events or len(events) < 3:
                return default_value
            
            # حساب نسبة النجاح
            total = len(events)
            successes = sum(1 for e in events if e.success)
            success_rate = successes / total
            
            # حساب متوسط القيمة
            avg_value = sum(e.event_value for e in events) / total
            
            # تعديل العتبة بناءً على الأداء
            # إذا كان النجاح عالياً -> يمكن تخفيف العتبة قليلاً
            # إذا كان النجاح منخفضاً -> تشديد العتبة
            if success_rate > 0.7:
                adjustment = 1.0 - (success_rate - 0.7) * 0.3  # تخفيف بحد أقصى 9%
            elif success_rate < 0.4:
                adjustment = 1.0 + (0.4 - success_rate) * 0.5  # تشديد بحد أقصى 20%
            else:
                adjustment = 1.0
            
            dynamic_value = default_value * adjustment
            
            logger.info(
                f"عتبة ديناميكية [{component}.{threshold_name}]: "
                f"افتراضي={default_value:.3f} -> ديناميكي={dynamic_value:.3f} "
                f"(نجاح={success_rate:.1%}, أحداث={total})"
            )
            
            return round(dynamic_value, 4)
            
        except Exception as e:
            logger.warning(f"فشل حساب العتبة الديناميكية: {e}")
            return default_value
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════
    #  أداء الوكلاء (Agent Performance Tracking)
    # ═══════════════════════════════════════════════════════════
    
    def get_agent_dynamic_weight(self, agent_name: str, default_weight: float = 1.0) -> float:
        """
        حساب وزن ديناميكي لوكيل بناءً على دقته السابقة
        
        الوزن يرتفع مع الدقة العالية وينخفض مع الأخطاء
        """
        db = self._get_db_session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=30)
            events = db.query(models.GlobalMemoryEvent).filter(
                models.GlobalMemoryEvent.component == "agent_manager",
                models.GlobalMemoryEvent.event_type == "agent_accuracy",
                models.GlobalMemoryEvent.event_key == agent_name,
                models.GlobalMemoryEvent.created_at >= cutoff,
            ).all()
            
            if not events or len(events) < 5:
                return default_weight
            
            total = len(events)
            correct = sum(1 for e in events if e.success)
            accuracy = correct / total
            
            # الوزن = 0.5 + (الدقة * 2.0)، محصور بين min_weight و max_weight
            dynamic_weight = 0.5 + (accuracy * 2.0)
            dynamic_weight = max(self.min_weight, min(self.max_weight, dynamic_weight))
            
            return round(dynamic_weight, 3)
            
        except Exception as e:
            logger.warning(f"فشل حساب وزن الوكيل {agent_name}: {e}")
            return default_weight
        finally:
            db.close()
    
    def log_agent_accuracy(self, agent_name: str, was_correct: bool, market: str = "", confidence: float = 0.0):
        """تسجيل دقة وكيل بعد التحقق من النتيجة"""
        self.log_event_experience(
            component="agent_manager",
            event_type="agent_accuracy",
            event_key=agent_name,
            event_value=confidence,
            metadata={"market": market, "correct": was_correct},
            context=market,
            success=was_correct,
        )
    
    # ═══════════════════════════════════════════════════════════
    #  أداء الاستراتيجيات (Strategy Performance - حدود ديناميكية)
    # ═══════════════════════════════════════════════════════════
    
    def get_dynamic_sandbox_duration(self, strategy_quality_score: float) -> int:
        """
        حساب مدة الاختبار الديناميكية للاستراتيجية
        
        - استراتيجية ممتازة (score > 0.8): 3 أيام
        - استراتيجية متوسطة (0.5-0.8): 5 أيام
        - استراتيجية ضعيفة (score < 0.5): 7 أيام
        """
        if strategy_quality_score > 0.8:
            return 3
        elif strategy_quality_score > 0.5:
            return 5
        else:
            return 7
    
    def get_dynamic_deployment_threshold(self, volatility_level: float = 0.0) -> float:
        """
        عتبة النشر الديناميكية بناءً على تقلبات السوق
        
        - سوق هادئ: عتبة 0.60
        - سوق متوسط: عتبة 0.65
        - سوق متقلب: عتبة 0.75
        """
        base = self.get_dynamic_threshold("deployer", "deployment_threshold", 0.65)
        if volatility_level > 0.7:
            return min(0.85, base + 0.10)
        elif volatility_level > 0.4:
            return base
        else:
            return max(0.55, base - 0.05)
    
    def get_dynamic_drawdown_limit(self) -> float:
        """حد السحب الديناميكي بناءً على الجلسة الحالية"""
        return self.get_dynamic_threshold("watcher", "max_drawdown", 15.0)
    
    def get_dynamic_win_rate_floor(self) -> float:
        """الحد الأدنى لنسبة النجاح الديناميكية"""
        return self.get_dynamic_threshold("watcher", "min_win_rate", 40.0)
    
    # ═══════════════════════════════════════════════════════════
    #  ذاكرة الإصلاحات (Fix Cache)
    # ═══════════════════════════════════════════════════════════
    
    def get_cached_fix(self, error_signature: str) -> Optional[Dict]:
        """البحث عن إصلاح مخزن لخطأ معين"""
        db = self._get_db_session()
        try:
            fix = db.query(models.FixCacheEntry).filter_by(
                error_signature=error_signature
            ).first()
            if fix and fix.success_rate >= 0.5:
                return {
                    "fix_code": fix.fix_code,
                    "fix_description": fix.fix_description,
                    "times_applied": fix.times_applied,
                    "success_rate": fix.success_rate,
                }
            return None
        except Exception as e:
            logger.warning(f"فشل البحث عن إصلاح مخزن: {e}")
            return None
        finally:
            db.close()
    
    def cache_fix(
        self,
        error_signature: str,
        error_message: str,
        fix_code: str,
        fix_description: str = "",
        component: str = "unknown",
        success: bool = True,
    ) -> None:
        """تخزين إصلاح ناجح للاستخدام المستقبلي"""
        db = self._get_db_session()
        try:
            existing = db.query(models.FixCacheEntry).filter_by(
                error_signature=error_signature
            ).first()
            
            if existing:
                existing.times_applied += 1
                # تحديث نسبة النجاح (المتوسط المتحرك)
                total = existing.times_applied
                if success:
                    existing.success_rate = ((existing.success_rate * (total - 1)) + 1.0) / total
                else:
                    existing.success_rate = ((existing.success_rate * (total - 1)) + 0.0) / total
                existing.last_applied = datetime.utcnow()
            else:
                new_fix = models.FixCacheEntry(
                    error_signature=error_signature,
                    error_message=error_message,
                    fix_code=fix_code,
                    fix_description=fix_description,
                    component=component,
                    times_applied=1,
                    success_rate=1.0 if success else 0.0,
                    created_at=datetime.utcnow(),
                )
                db.add(new_fix)
            
            db.commit()
            logger.info(f"تم تخزين/تحديث إصلاح: {error_signature[:50]}")
        except Exception as e:
            logger.error(f"فشل تخزين الإصلاح: {e}")
            db.rollback()
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════
    #  تعلم تأثير الأخبار (News Impact Learning)
    # ═══════════════════════════════════════════════════════════
    
    def learn_keyword_impact(
        self,
        keyword: str,
        market: str,
        predicted_impact: float,
        actual_impact: float,
        price_before: float = 0.0,
        price_after: float = 0.0,
    ) -> float:
        """
        تعلم التأثير الفعلي لكلمة مفتاحية إخبارية
        يُعيد الوزن المتعلّم الجديد
        """
        db = self._get_db_session()
        try:
            existing = db.query(models.NewsKeywordImpact).filter_by(
                keyword=keyword, market=market
            ).first()
            
            if existing:
                n = existing.times_observed
                # متوسط متحرك أسّي (EMA) للتأثير المتعلّم
                alpha = 2.0 / (n + 1)
                existing.learned_weight = round(
                    alpha * actual_impact + (1 - alpha) * existing.learned_weight, 4
                )
                existing.actual_impact = actual_impact
                existing.price_before = price_before
                existing.price_after = price_after
                existing.times_observed += 1
                new_weight = existing.learned_weight
            else:
                new_entry = models.NewsKeywordImpact(
                    keyword=keyword,
                    market=market,
                    predicted_impact=predicted_impact,
                    actual_impact=actual_impact,
                    price_before=price_before,
                    price_after=price_after,
                    times_observed=1,
                    learned_weight=actual_impact,
                )
                db.add(new_entry)
                new_weight = actual_impact
            
            db.commit()
            return new_weight
        except Exception as e:
            logger.error(f"فشل تعلم تأثير الكلمة {keyword}: {e}")
            db.rollback()
            return predicted_impact
        finally:
            db.close()
    
    def get_learned_keyword_weights(self, min_observations: int = 3) -> Dict[str, float]:
        """الحصول على أوزان الكلمات المفتاحية المتعلّمة"""
        db = self._get_db_session()
        try:
            entries = db.query(models.NewsKeywordImpact).filter(
                models.NewsKeywordImpact.times_observed >= min_observations
            ).all()
            return {
                entry.keyword: entry.learned_weight
                for entry in entries
            }
        except Exception as e:
            logger.warning(f"فشل قراءة أوزان الكلمات: {e}")
            return {}
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════
    #  تفضيلات التنبيهات (Alert Preferences Learning)
    # ═══════════════════════════════════════════════════════════
    
    def track_alert_response(
        self,
        user_id: int,
        alert_type: str,
        was_read: bool = False,
        was_acted_upon: bool = False,
    ) -> None:
        """تتبع تفاعل المستخدم مع التنبيه"""
        db = self._get_db_session()
        try:
            pref = db.query(models.AlertPreference).filter_by(
                user_id=user_id, alert_type=alert_type
            ).first()
            
            if not pref:
                pref = models.AlertPreference(
                    user_id=user_id,
                    alert_type=alert_type,
                    times_sent=1,
                    times_read=1 if was_read else 0,
                    times_acted=1 if was_acted_upon else 0,
                )
                db.add(pref)
            else:
                pref.times_sent += 1
                if was_read:
                    pref.times_read += 1
                if was_acted_upon:
                    pref.times_acted += 1
                pref.last_sent = datetime.utcnow()
                
                # حساب تعديل الأولوية
                if pref.times_sent >= 5:
                    read_rate = pref.times_read / pref.times_sent
                    act_rate = pref.times_acted / pref.times_sent
                    
                    if read_rate < 0.2:
                        pref.priority_adjustment = -2.0  # تنزيل حاد
                    elif read_rate < 0.4:
                        pref.priority_adjustment = -1.0  # تنزيل خفيف
                    elif act_rate > 0.6:
                        pref.priority_adjustment = 1.0   # رفع (مهم للمستخدم)
                    else:
                        pref.priority_adjustment = 0.0
            
            db.commit()
        except Exception as e:
            logger.error(f"فشل تتبع تفاعل التنبيه: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_alert_priority_adjustment(self, user_id: int, alert_type: str) -> float:
        """الحصول على تعديل الأولوية لنوع تنبيه معين"""
        db = self._get_db_session()
        try:
            pref = db.query(models.AlertPreference).filter_by(
                user_id=user_id, alert_type=alert_type
            ).first()
            return pref.priority_adjustment if pref else 0.0
        except Exception:
            return 0.0
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════
    #  تتبع أخطاء الكود (Code Review Tracking)
    # ═══════════════════════════════════════════════════════════
    
    def log_code_error(self, file_path: str, error_type: str) -> str:
        """
        تسجيل خطأ برمجي وإرجاع مستوى التدقيق المطلوب
        
        Returns:
            مستوى التدقيق: "low", "medium", "high", "critical"
        """
        db = self._get_db_session()
        try:
            record = db.query(models.CodeReviewHistory).filter_by(
                file_path=file_path, error_type=error_type
            ).first()
            
            if record:
                record.error_count += 1
                record.last_review = datetime.utcnow()
                
                # ترقية مستوى التدقيق تلقائياً
                if record.error_count >= 10:
                    record.strictness_level = "critical"
                elif record.error_count >= 5:
                    record.strictness_level = "high"
                elif record.error_count >= 3:
                    record.strictness_level = "medium"
                
                strictness = record.strictness_level
            else:
                new_record = models.CodeReviewHistory(
                    file_path=file_path,
                    error_type=error_type,
                    error_count=1,
                    strictness_level="medium",
                )
                db.add(new_record)
                strictness = "medium"
            
            db.commit()
            return strictness
        except Exception as e:
            logger.error(f"فشل تسجيل خطأ الكود: {e}")
            db.rollback()
            return "medium"
        finally:
            db.close()
    
    def get_file_strictness(self, file_path: str) -> str:
        """الحصول على مستوى التدقيق لملف معين"""
        db = self._get_db_session()
        try:
            records = db.query(models.CodeReviewHistory).filter_by(
                file_path=file_path
            ).all()
            if not records:
                return "medium"
            
            # إرجاع أعلى مستوى تدقيق
            levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            max_level = max(levels.get(r.strictness_level, 1) for r in records)
            reverse_levels = {v: k for k, v in levels.items()}
            return reverse_levels.get(max_level, "medium")
        except Exception:
            return "medium"
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════
    #  ملخص يومي للتعلّم (Daily Learning Summary)
    # ═══════════════════════════════════════════════════════════
    
    def get_daily_learning_summary(self) -> Dict[str, Any]:
        """ملخص شامل لما تعلمه النظام اليوم"""
        db = self._get_db_session()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            today_events = db.query(models.GlobalMemoryEvent).filter(
                models.GlobalMemoryEvent.created_at >= today
            ).all()
            
            summary = {
                "date": today.isoformat(),
                "total_events": len(today_events),
                "components": {},
                "success_rate": 0.0,
            }
            
            if today_events:
                successes = sum(1 for e in today_events if e.success)
                summary["success_rate"] = round(successes / len(today_events) * 100, 1)
                
                for event in today_events:
                    comp = event.component
                    if comp not in summary["components"]:
                        summary["components"][comp] = {
                            "events": 0,
                            "successes": 0,
                            "failures": 0,
                        }
                    summary["components"][comp]["events"] += 1
                    if event.success:
                        summary["components"][comp]["successes"] += 1
                    else:
                        summary["components"][comp]["failures"] += 1
            
            return summary
        except Exception as e:
            logger.error(f"فشل إنشاء ملخص التعلم: {e}")
            return {"date": today.isoformat(), "total_events": 0, "error": str(e)}
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════
    #  الدوال الأصلية (Original Functions - محفوظة)
    # ═══════════════════════════════════════════════════════════

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
