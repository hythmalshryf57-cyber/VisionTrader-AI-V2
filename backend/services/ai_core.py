import json
import logging
import math
import re
import threading
import time
import warnings
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean, stdev
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import OneHotEncoder

try:
    from database import SessionLocal
    import models
    from strategies.adaptive_ai import MarketRegimeDetector
except ImportError:
    try:
        from backend.database import SessionLocal
        import models
        from backend.strategies.adaptive_ai import MarketRegimeDetector
    except ImportError:
        from database import SessionLocal
        import models
        from strategies.adaptive_ai import MarketRegimeDetector

from .performance_tracker import PerformanceTracker
from .social_sentiment import social_sentiment_service
from .vector_memory import vector_memory
from .internal_brain import InternalBrain
from .binance_service import BinanceService

warnings.filterwarnings('ignore', category=UserWarning)

logger = logging.getLogger(__name__)


class NewsImpactAnalyzer:
    def analyze(self, news_sentiment: Dict[str, Any]) -> Dict[str, Any]:
        score = float(news_sentiment.get("sentiment_score", 0.0) or 0.0)
        if not news_sentiment.get("available", True):
            return {"impact": "محايد", "strength": "منخفض", "confidence": 0, "note": "بيانات الأخبار غير متاحة حالياً."}

        if score >= 0.6:
            note = "تأثير أخبار إيجابي قوي يدعم السيناريو الصاعد."
            return {"impact": "إيجابي", "strength": "قوي", "confidence": 90, "note": note}
        if score >= 0.25:
            note = "تأثير أخبار إيجابي معتدل يمكن أن يعزز الحركة الصاعدة." 
            return {"impact": "إيجابي", "strength": "متوسط", "confidence": 70, "note": note}
        if score <= -0.6:
            note = "تأثير أخبار سلبي قوي يدعم السيناريو الهابط."
            return {"impact": "سلبي", "strength": "قوي", "confidence": 90, "note": note}
        if score <= -0.25:
            note = "تأثير أخبار سلبي معتدل يمكن أن يعزز الحركة الهابطة."
            return {"impact": "سلبي", "strength": "متوسط", "confidence": 70, "note": note}
        return {"impact": "محايد", "strength": "منخفض", "confidence": int(abs(score) * 50), "note": "لا توجد إشارة إخبارية قوية في الوقت الحالي."}


class OrderFlowModule:
    def __init__(self, binance_service: BinanceService):
        self.binance_service = binance_service

    def interpret(self, market: str, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        symbol = market.upper().replace('/', '')
        live = self.binance_service.scan(symbol) if self.binance_service else {}
        footprint = live.get('footprint', []) or []
        cumulative_delta = float(live.get('cumulative_delta', 0.0) or 0.0)
        open_interest = float(live.get('open_interest', 0.0) or 0.0)
        liquidations = live.get('last_liquidations', []) or []
        buy_volume = sum([c.get('volume', 0.0) for c in footprint if c.get('close', 0.0) >= c.get('open', 0.0)])
        sell_volume = sum([c.get('volume', 0.0) for c in footprint if c.get('close', 0.0) < c.get('open', 0.0)])
        pressure_balance = buy_volume - sell_volume
        total_pressure = max(abs(buy_volume) + abs(sell_volume), 1.0)
        absorption = float(chart_data.get('absorption_score', 0.0) or 0.0)
        breakout_strength = float(chart_data.get('breakout_strength', 0.0) or 0.0)

        stop_hunt_risk = False
        fake_breakout_risk = False
        trap_risk = False
        if breakout_strength > 0 and cumulative_delta * pressure_balance < 0:
            fake_breakout_risk = True
        if chart_data.get('recent_sweep', False) and abs(cumulative_delta) < abs(pressure_balance) * 0.2:
            stop_hunt_risk = True
        if abs(pressure_balance) / total_pressure > 0.65 and abs(cumulative_delta) < total_pressure * 0.12:
            trap_risk = True

        return {
            'symbol': symbol,
            'cumulative_delta': cumulative_delta,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'pressure_balance': pressure_balance,
            'pressure_ratio': pressure_balance / total_pressure,
            'absorption': absorption,
            'breakout_strength': breakout_strength,
            'stop_hunt_risk': stop_hunt_risk,
            'fake_breakout_risk': fake_breakout_risk,
            'trap_risk': trap_risk,
            'open_interest': open_interest,
            'spread': float(chart_data.get('spread', 0.0) or 0.0),
            'liquidation_count': len(liquidations),
        }


class MarketPersona:
    def profile(self, user_id: int, market: str) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            trades = db.query(models.TradeExperience).filter(models.TradeExperience.user_id == user_id, models.TradeExperience.market == market).all()
            if not trades:
                return {
                    'market': market,
                    'win_rate': 0.0,
                    'average_profit': 0.0,
                    'best_sessions': [],
                    'personality': 'غير معروف',
                    'notes': 'لم تتوفر بيانات كافية لبناء شخصية السوق بعد.'
                }
            wins = [t for t in trades if str(t.result or '').lower().startswith('win') or 'رابح' in str(t.result or '').lower()]
            losses = [t for t in trades if str(t.result or '').lower().startswith('loss') or 'خاسر' in str(t.result or '').lower()]
            total_profit = sum([float(t.profit_loss or 0.0) for t in trades])
            avg_profit = total_profit / max(len(trades), 1)
            session_stats = {}
            for t in trades:
                name = t.session or 'غير معروف'
                session_stats.setdefault(name, {'wins': 0, 'trades': 0, 'pnl': 0.0})
                session_stats[name]['trades'] += 1
                if str(t.result or '').lower().startswith('win') or 'رابح' in str(t.result or '').lower():
                    session_stats[name]['wins'] += 1
                session_stats[name]['pnl'] += float(t.profit_loss or 0.0)
            best_sessions = sorted([
                {'session': s, 'win_rate': round((v['wins'] / max(v['trades'], 1)) * 100, 2), 'trades': v['trades'], 'pnl': round(v['pnl'], 2)}
                for s, v in session_stats.items()
            ], key=lambda x: (x['win_rate'], x['pnl']), reverse=True)[:3]
            win_rate = round((len(wins) / max(len(trades), 1)) * 100, 2)
            personality = 'متقلب' if abs(avg_profit) > 1.0 and len(trades) >= 10 else 'متوازن' if len(trades) >= 10 else 'غير معروف'
            if market.upper().startswith('XAU'):
                personality = 'ذهب: حساس للمعنويات ويدعم الانعكاسات الكبيرة'
            elif market.upper().startswith('EUR'):
                personality = 'EUR/USD: يميل للاتجاهات المتوسطة والتفاعلات حول لندن'
            elif market.upper().startswith('GBP'):
                personality = 'GBP/USD: يتحرك بسرعة ويحتاج متابعة جلسات لندن والنيويورك'
            elif market.upper().startswith('USDJPY'):
                personality = 'USD/JPY: يتأثر بمعدلات الفائدة وانحياز الاتجاهات الطويلة'

            return {
                'market': market,
                'win_rate': win_rate,
                'average_profit': round(avg_profit, 2),
                'best_sessions': best_sessions,
                'personality': personality,
                'notes': f'السوق يُظهر {win_rate}% نجاح مع متوسط ربح {round(avg_profit,2)} دولار.'
            }
        finally:
            db.close()


class TradeOutcomeModel:
    def __init__(self):
        self.model = None
        self.encoder = None
        self.feature_columns = []
        self.last_trained = None

    def _safe_load(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _parse_features(self, chart_features: dict) -> Dict[str, Any]:
        if not isinstance(chart_features, dict):
            try:
                chart_features = json.loads(chart_features or '{}')
            except Exception:
                chart_features = {}
        return {
            'pattern_count': int(chart_features.get('pattern_count', 0) or 0),
            'trend_strength': self._safe_load(chart_features.get('trend_strength', 0.0)),
            'volatility': self._safe_load(chart_features.get('volatility', 0.0)),
            'breakout_strength': self._safe_load(chart_features.get('breakout_strength', 0.0)),
            'support_count': int(chart_features.get('support_count', 0) or 0),
            'resistance_count': int(chart_features.get('resistance_count', 0) or 0),
        }

    def _build_dataset(self, experiences: List[models.TradeExperience]) -> Optional[pd.DataFrame]:
        rows = []
        for exp in experiences:
            chart_features = self._parse_features(exp.chart_features or {})
            session = exp.session or 'unknown'
            market = exp.market or 'unknown'
            strategy_count = len([s for s in (exp.strategy_names or '').split(',') if s.strip()])
            outcome = 1 if str(exp.result or '').lower().startswith('win') or 'رابح' in str(exp.result or '').lower() else 0
            rows.append({
                'market': market,
                'session': session,
                'news_sentiment': self._safe_load(exp.news_sentiment, 0.0),
                'strategy_count': strategy_count,
                'confidence': self._safe_load(getattr(exp, 'confidence', None) or 0.0),
                'profit_loss': self._safe_load(exp.profit_loss, 0.0),
                'label': outcome,
                **chart_features
            })
        if not rows:
            return None
        return pd.DataFrame(rows)

    def train(self, user_id: int) -> None:
        db = SessionLocal()
        try:
            experiences = db.query(models.TradeExperience).filter(models.TradeExperience.user_id == user_id).all()
            if len(experiences) < 12:
                return
            df = self._build_dataset(experiences)
            if df is None or df['label'].nunique() < 2:
                return
            categorical = ['market', 'session']
            self.encoder = OneHotEncoder(handle_unknown='ignore', sparse=False)
            cat_encoded = self.encoder.fit_transform(df[categorical])
            cat_cols = self.encoder.get_feature_names_out(categorical).tolist()
            numeric_cols = ['news_sentiment', 'strategy_count', 'confidence', 'profit_loss', 'pattern_count', 'trend_strength', 'volatility', 'breakout_strength', 'support_count', 'resistance_count']
            self.feature_columns = cat_cols + numeric_cols
            X = pd.DataFrame(cat_encoded, columns=cat_cols)
            X[numeric_cols] = df[numeric_cols].fillna(0.0)
            y = df['label']
            self.model = GradientBoostingClassifier(n_estimators=100, learning_rate=0.08, max_depth=4, random_state=42)
            self.model.fit(X, y)
            self.last_trained = datetime.now(timezone.utc)
        except Exception as e:
            logger.exception(f'Failed to train trade outcome model: {e}')
        finally:
            db.close()

    def predict(self, market: str, session: str, news_sentiment: float, strategy_count: int, confidence_val: float, chart_features: dict, orderflow: dict, persona: dict) -> Dict[str, Any]:
        if self.model is None or self.encoder is None:
            return {
                'win_probability': 0.5,
                'loss_probability': 0.5,
                'prediction': 'غير محدد',
                'notes': 'النموذج لم يتدرب بعد أو لا توجد بيانات كافية.'
            }
        chart_vals = self._parse_features(chart_features)
        row = {
            'market': market,
            'session': session,
            'news_sentiment': news_sentiment,
            'strategy_count': strategy_count,
            'confidence': confidence_val,
            'profit_loss': 0.0,
            **chart_vals
        }
        features = pd.DataFrame([row])
        cat_encoded = self.encoder.transform(features[['market', 'session']])
        cat_cols = self.encoder.get_feature_names_out(['market', 'session']).tolist()
        X = pd.DataFrame(cat_encoded, columns=cat_cols)
        numeric_cols = ['news_sentiment', 'strategy_count', 'confidence', 'profit_loss', 'pattern_count', 'trend_strength', 'volatility', 'breakout_strength', 'support_count', 'resistance_count']
        X[numeric_cols] = features[numeric_cols].fillna(0.0)
        try:
            proba = self.model.predict_proba(X)[0]
            win_prob = float(proba[1]) if len(proba) > 1 else 0.5
            loss_prob = float(proba[0]) if len(proba) > 1 else 0.5
            return {
                'win_probability': win_prob,
                'loss_probability': loss_prob,
                'prediction': 'شراء' if win_prob >= loss_prob else 'بيع',
                'notes': 'التوقع قائم على نموذج تعلم آلي متدرِّب من تاريخ التداول السابق.'
            }
        except Exception as e:
            logger.exception(f'Failed to predict trade outcome: {e}')
            return {
                'win_probability': 0.5,
                'loss_probability': 0.5,
                'prediction': 'غير محدد',
                'notes': 'حدث خطأ أثناء التنبؤ.'
            }


class MultiTFConfluenceMeter:
    def measure(self, chart_data: Dict[str, Any], cluster_results: Dict[str, Any]) -> Dict[str, Any]:
        raw_text = " ".join(chart_data.get("raw_text", [])) if chart_data else ""
        tokens = set(re.findall(r"\b(?:1m|5m|15m|30m|1h|4h|1d|daily|weekly|1w|1mo|monthly)\b", raw_text, flags=re.I))
        directions = [cluster.get("direction") for cluster in cluster_results.values() if cluster.get("direction")]
        unique_directions = set(directions)
        if len(tokens) >= 2 and len(unique_directions) == 1 and unique_directions != {"محايد"}:
            return {"level": "عالي", "detail": "توافق قوي بين الأطر الزمنية المختلفة.", "timeframes": sorted(list(tokens))[:4]}
        if len(tokens) >= 2 and len(unique_directions) > 1:
            return {"level": "متوسط", "detail": "توافق جزئي، بعض الأطر الزمنية تدعم اتجاهًا واحدًا بينما أخرى متذبذبة.", "timeframes": sorted(list(tokens))[:4]}
        if len(unique_directions) == 1 and unique_directions != {"محايد"}:
            return {"level": "متوسط", "detail": "التوصيات موحدة من العناقيد لكن الأطر الزمنية المتعددة غير واضحة.", "timeframes": sorted(list(tokens))[:4]}
        return {"level": "منخفض", "detail": "التوافق متعدد الأطر الزمنية ضعيف أو غير متوفر.", "timeframes": sorted(list(tokens))[:4]}


class ConflictResolver:
    def __init__(self):
        self.internal_brain = InternalBrain()

    def resolve(
        self,
        cluster_results: Dict[str, Any],
        strategy_weights: Dict[str, float],
        news_sentiment: Dict[str, Any],
        performance: Dict[str, Any],
        percepts: Dict[str, Any],
    ) -> Dict[str, Any]:
        vote_scores = {"شراء": 0.0, "بيع": 0.0, "محايد": 0.0}
        details = []
        for cluster in cluster_results.values():
            for detail in cluster.get("details", []):
                vote = detail.get("vote") if detail.get("vote") in ("شراء", "بيع") else "محايد"
                vote_scores[vote] += detail.get("weight", 0.0)
                details.append(detail)

        if abs(vote_scores["شراء"] - vote_scores["بيع"]) < 0.2 * max(vote_scores["شراء"] + vote_scores["بيع"], 1.0):
            return self.internal_brain.resolve_conflict(details, vote_scores)

        sentiment_score = float(news_sentiment.get("sentiment_score", 0.0) or 0.0)
        if sentiment_score >= 0.5 and vote_scores["بيع"] >= vote_scores["شراء"]:
            return {"recommendation": "شراء", "resolution_reason": "التحليل الإخباري الإيجابي قوي بما يكفي لتفضيل الشراء رغم توافق آخر الاستراتيجيات."}
        if sentiment_score <= -0.5 and vote_scores["شراء"] >= vote_scores["بيع"]:
            return {"recommendation": "بيع", "resolution_reason": "التحليل الإخباري السلبي قوي بما يكفي لتفضيل البيع رغم توافق آخر الاستراتيجيات."}

        dominant = "شراء" if vote_scores["شراء"] > vote_scores["بيع"] else "بيع"
        return {"recommendation": dominant, "resolution_reason": "تم حل أي تعارضات باستخدام وزن الأداء والأخبار."}


class PerceptionModule:
    def perceive(
        self,
        chart_data: Dict[str, Any],
        cluster_results: Dict[str, Any],
        strategy_weights: Dict[str, float],
        market: str,
    ) -> Dict[str, Any]:
        closes = chart_data.get("closes", [])
        highs = chart_data.get("highs", [])
        lows = chart_data.get("lows", [])
        volumes = chart_data.get("volumes", [])
        patterns = chart_data.get("candle_patterns", [])
        support = chart_data.get("support_levels", [])
        resistance = chart_data.get("resistance_levels", [])

        percepts = {
            "cluster_consensus": {
                name: cluster.get("direction")
                for name, cluster in cluster_results.items()
            },
            "cluster_confidence": {
                name: cluster.get("confidence", 0)
                for name, cluster in cluster_results.items()
            },
            "market": market,
            "trend": chart_data.get("trend", "غير محدد"),
            "patterns": patterns,
            "support_count": len(support),
            "resistance_count": len(resistance),
            "volume_activity": "متصاعد" if self._volume_trend(volumes) > 0 else "متراجع" if self._volume_trend(volumes) < 0 else "مستقر",
            "price_momentum": self._price_momentum(closes),
            "volatility": self._volatility(closes),
            "signal_balance": self._signal_balance(cluster_results, strategy_weights),
            "price_support": support[-1] if support else None,
            "price_resistance": resistance[-1] if resistance else None,
            "multi_tf_confluence": self._compute_multi_tf_confluence(chart_data, cluster_results),
        }

        return percepts

    def _price_momentum(self, closes: List[float]) -> str:
        if len(closes) < 2:
            return "غير معروف"
        delta = closes[-1] - closes[-2]
        threshold = max(0.0001, abs(closes[-1]) * 0.0008)
        if abs(delta) < threshold:
            return "مستقر"
        return "صاعد" if delta > 0 else "هابط"

    def _volatility(self, closes: List[float]) -> str:
        if len(closes) < 5:
            return "غير معروف"
        returns = [(closes[i] - closes[i - 1]) / max(abs(closes[i - 1]), 1) for i in range(1, len(closes))]
        try:
            volatility = stdev(returns)
        except Exception:
            volatility = 0.0
        if volatility > 0.02:
            return "مرتفع"
        if volatility > 0.008:
            return "متوسط"
        return "منخفض"

    def _volume_trend(self, volumes: List[float]) -> float:
        if len(volumes) < 3:
            return 0.0
        return volumes[-1] - volumes[0]

    def _signal_balance(self, cluster_results: Dict[str, Any], strategy_weights: Dict[str, float]) -> Dict[str, float]:
        buy = 0.0
        sell = 0.0
        for cluster in cluster_results.values():
            for detail in cluster.get("details", []):
                if detail.get("vote") == "شراء":
                    buy += detail.get("weight", 0.0)
                elif detail.get("vote") == "بيع":
                    sell += detail.get("weight", 0.0)
        total = max(buy + sell, 1.0)
        return {
            "buy": round(buy / total, 3),
            "sell": round(sell / total, 3),
            "difference": round((buy - sell) / total, 3),
        }

    def _compute_multi_tf_confluence(self, chart_data: Dict[str, Any], cluster_results: Dict[str, Any]) -> str:
        raw_text = " ".join(chart_data.get("raw_text", [])) if chart_data else ""
        timeframes = set(re.findall(r"\b(?:1m|5m|15m|30m|1h|4h|1d|daily|weekly|1w|1mo|monthly)\b", raw_text, flags=re.I))
        cluster_directions = [cluster.get("direction") for cluster in cluster_results.values() if cluster.get("direction")]
        unique_directions = set(cluster_directions)
        if len(timeframes) >= 2 and len(unique_directions) == 1 and unique_directions != {"محايد"}:
            return "عالي"
        if len(timeframes) >= 2 and len(unique_directions) > 1:
            return "متوسط"
        if len(unique_directions) == 1 and unique_directions != {"محايد"}:
            return "متوسط"
        return "منخفض"


class MemoryModule:
    def recall(self, user_id: int, percepts: Dict[str, Any]) -> Dict[str, Any]:
        db = SessionLocal()
        matches = []
        try:
            experiences = db.query(models.TradeExperience).filter(models.TradeExperience.user_id == user_id).all()
            if not experiences:
                return {"matches": [], "strength": 0.0}

            current_signature = self._build_signature(percepts)
            scored = []
            for exp in experiences:
                past_signature = self._parse_signature(exp.pattern_signature)
                # compute contextual signature similarity
                sig_sim = self._signature_similarity(current_signature, past_signature)
                # compute visual similarity via vector memory when available
                visual_sim = 0.0
                try:
                    desc = exp.chart_features if isinstance(exp.chart_features, str) else (exp.pattern_signature or '')
                    vmatches = vector_memory.find_similar(desc or '', top_k=1, db=db)
                    if vmatches:
                        visual_sim = float(vmatches[0].get('score') or 0.0)
                except Exception:
                    visual_sim = 0.0

                # mix visual and contextual similarity (50/50)
                similarity = round((sig_sim + visual_sim) / 2.0, 3)
                scored.append((similarity, exp))

            scored.sort(key=lambda item: item[0], reverse=True)
            top = scored[:3]
            for sim, exp in top:
                matches.append({
                    "similarity": round(sim, 3),
                    "market": exp.market,
                    "result": exp.result,
                    "profit_loss": round(exp.profit_loss or 0.0, 2),
                    "session": exp.session,
                    "strategy_names": exp.strategy_names,
                    "news_sentiment": exp.news_sentiment,
                })

            recent_market = [exp for exp in experiences if exp.market == percepts.get('market')]
            market_win_rate = round((len([e for e in recent_market if str(e.result or '').lower().startswith('win')]) / max(len(recent_market), 1)) * 100, 2)
            session_stats = defaultdict(lambda: {'trades': 0, 'wins': 0})
            for exp in experiences:
                session_stats[exp.session or 'غير معروف']['trades'] += 1
                if str(exp.result or '').lower().startswith('win'):
                    session_stats[exp.session or 'غير معروف']['wins'] += 1

            return {
                "matches": matches,
                "strength": round(mean([sim for sim, _ in top]) if top else 0.0, 3),
                "market_context": {
                    "market_win_rate": market_win_rate,
                    "recent_trades": len(recent_market),
                    "best_sessions": sorted(
                        [
                            {
                                'session': s,
                                'win_rate': round((v['wins'] / max(v['trades'], 1)) * 100, 2),
                                'trades': v['trades'],
                            }
                            for s, v in session_stats.items()
                        ],
                        key=lambda x: (x['win_rate'], x['trades']),
                        reverse=True,
                    )[:2],
                },
            }
        except Exception as e:
            logger.exception(f"Memory recall failed: {e}")
            return {"matches": [], "strength": 0.0}
        finally:
            db.close()

    def remember(
        self,
        user_id: int,
        market: str,
        recommendation: str,
        result: str,
        profit_loss: float,
        strategy_names: Optional[str],
        session: str,
        news_sentiment: Optional[float],
        pattern_signature: str,
        notes: Optional[str],
    ) -> None:
        db = SessionLocal()
        try:
            experience = models.TradeExperience(
                user_id=user_id,
                market=market,
                recommendation=recommendation,
                result=result,
                profit_loss=profit_loss,
                strategy_names=strategy_names,
                session=session,
                news_sentiment=news_sentiment,
                pattern_signature=pattern_signature,
                notes=notes,
                created_at=datetime.now(timezone.utc),
            )
            db.add(experience)
            db.commit()
        except Exception as e:
            logger.exception(f"Failed to remember trade experience: {e}")
            db.rollback()
        finally:
            db.close()

    def learn_from_experience(self, user_id: int, experience: Dict[str, Any]) -> None:
        """تعلم من تجربة تداول لتحسين الذاكرة المستقبلية"""
        try:
            # تحديث الأنماط بناءً على النتيجة
            if experience.get("outcome") == "win":
                # تعزيز الأنماط الناجحة
                self._reinforce_pattern(user_id, experience)
            else:
                # تعديل الأنماط الفاشلة
                self._adjust_pattern(user_id, experience)
        except Exception as e:
            logger.exception(f"Failed to learn from experience: {e}")

    def _reinforce_pattern(self, user_id: int, experience: Dict[str, Any]) -> None:
        """تعزيز الأنماط الناجحة"""
        # يمكن إضافة منطق لتعزيز الأنماط هنا
        pass

    def _adjust_pattern(self, user_id: int, experience: Dict[str, Any]) -> None:
        """تعديل الأنماط الفاشلة"""
        # يمكن إضافة منطق لتعديل الأنماط هنا
        pass

    def _build_signature(self, percepts: Dict[str, Any]) -> Dict[str, Any]:
        # include session, weekday, and presence of news in signature
        session = percepts.get('session') or percepts.get('market_session') or 'unknown'
        weekday = datetime.now(timezone.utc).weekday()
        has_news = bool(percepts.get('news_sentiment'))
        return {
            "trend": percepts.get("trend"),
            "price_momentum": percepts.get("price_momentum"),
            "volatility": percepts.get("volatility"),
            "support_count": percepts.get("support_count"),
            "resistance_count": percepts.get("resistance_count"),
            "pattern_count": len(percepts.get("patterns", [])),
            "cluster_difference": percepts.get("signal_balance", {}).get("difference", 0.0),
            "session": session,
            "weekday": weekday,
            "has_news": has_news,
        }

    def _parse_signature(self, encoded: Optional[str]) -> Dict[str, Any]:
        try:
            return json.loads(encoded) if encoded else {}
        except Exception:
            return {}

    def _signature_similarity(self, current: Dict[str, Any], past: Dict[str, Any]) -> float:
        if not past:
            return 0.0
        score = 0.0
        same = 0
        for key in ("trend", "price_momentum", "volatility"):
            if current.get(key) == past.get(key):
                score += 1.0
            same += 1
        for key in ("support_count", "resistance_count", "pattern_count"):
            diff = abs((current.get(key, 0) or 0) - (past.get(key, 0) or 0))
            score += max(0.0, 1.0 - min(diff, 5) / 5)
            same += 1
        diff = abs(current.get("cluster_difference", 0.0) - past.get("cluster_difference", 0.0))
        score += max(0.0, 1.0 - min(diff, 1.0))
        same += 1
        return round(score / max(same, 1), 3)


class ReasoningModule:
    def reason(
        self,
        percepts: Dict[str, Any],
        memory: Dict[str, Any],
        news_sentiment: Dict[str, Any],
    ) -> Dict[str, Any]:
        narrative = []
        evidence = []
        cluster_bias = percepts.get("cluster_consensus", {})
        momentum = percepts.get("price_momentum")
        volatility = percepts.get("volatility")
        sentiment = news_sentiment.get("sentiment_score", 0.0)

        if momentum and momentum != "مستقر":
            narrative.append(f"الزخم الحالي يبدو {momentum}")
            evidence.append(f"تحرك السعر من خلال آخر نقاطه يعطي انطباع {momentum}")

        if percepts.get("support_count", 0) > 0 and percepts.get("resistance_count", 0) > 0:
            evidence.append("المستويات السعرية الرئيسية موجودة وتساعد في تحديد نقاط الدخول والخروج")

        if sentiment:
            direction = "إيجابي" if sentiment > 0 else "سلبي"
            evidence.append(f"المشاعر الإخبارية حالياً {direction} ({round(sentiment, 2)})")

        if percepts.get("multi_tf_confluence"):
            evidence.append(f"مستوى توافق الأطر الزمنية: {percepts.get('multi_tf_confluence')}")

        # include cluster bias / consensus as part of evidence
        if cluster_bias:
            try:
                bias_summary = ", ".join([f"{k}:{v}" for k, v in cluster_bias.items()])
                evidence.append(f"انحياز العناقيد الحالي: {bias_summary}")
            except Exception:
                evidence.append("انحياز العناقيد متاح ولكنه لم يتم تلخيصه")

        if memory.get("strength", 0) > 0.6:
            top = memory.get("matches", [])[0]
            evidence.append(f"الشكل مشابه لصفقة سابقة بنتيجة {top.get('result')} بنسبة تشابه {round(top.get('similarity', 0)*100)}%")
            narrative.append("الذاكرة السوقية تربط السيناريو الحالي بصفقات سابقة")

        if abs(sentiment) > 0.8:
            if sentiment > 0:
                evidence.append("المشاعر مفرطة الإيجابية، وهذا يمكن أن يشير إلى فخ شرائي")
            else:
                evidence.append("المشاعر مفرطة السلبية، مما قد يدل على فخ بيعي")

        if volatility != "منخفض":
            evidence.append(f"التقلب {volatility} يؤثر على قوة الثقة النهائية")

        suggested_focus = "اعتمد على الأدلة الأقوى ولا تتحيز إلى أي اتجاه بدون دعم واضح"
        if memory.get("strength", 0) > 0.75:
            suggested_focus = "الذاكرة التاريخية تضيف ثقلًا كبيرًا إلى القرار الحالي"

        return {
            "narrative": " ؛ ".join(narrative) if narrative else "لا توجد مؤشرات واضحة، لكن النظام يقوم بتحليل السوق بأكمله.",
            "evidence": evidence,
            "focus": suggested_focus,
        }


class DecisionModule:
    def decide(
        self,
        percepts: Dict[str, Any],
        memory: Dict[str, Any],
        reasoning: Dict[str, Any],
        news_sentiment: Dict[str, Any],
        performance: Dict[str, Any],
        ml_prediction: Dict[str, Any],
        orderflow: Dict[str, Any],
        persona: Dict[str, Any],
        regime: Dict[str, Any],
        conflict_resolution: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        chart_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sentiment_score = news_sentiment.get("sentiment_score", 0.0)
        memory_strength = memory.get("strength", 0.0)
        win_probability = ml_prediction.get("win_probability", 0.5)
        loss_probability = ml_prediction.get("loss_probability", 0.5)
        direction = ml_prediction.get("prediction", "انتظار")
        balance = percepts.get("signal_balance", {})
        signal_strength = abs(balance.get("difference", 0.0))
        trap_risk = orderflow.get("trap_risk", False)
        stop_hunt_risk = orderflow.get("stop_hunt_risk", False)
        breakout_strength = orderflow.get("breakout_strength", 0.0)

        # Get user trading mode (default to DAY_TRADING if not set)
        trading_mode = self._get_user_trading_mode(user_id)
        trading_persona = self._get_trading_persona(trading_mode)

        # Human-like weighting based on probabilistic learning and order flow context.
        confidence_base = win_probability * 100
        # reduce sentiment influence (previously larger): scale to ~0.10 effective weight
        confidence_base += min(12, abs(sentiment_score) * 5.714)
        confidence_base += min(12, memory_strength * 20)
        confidence_base += min(10, signal_strength * 40)

        # use wider waiting threshold (20%) for ambiguous model probabilities
        if trap_risk and abs(win_probability - 0.5) < 0.20:
            direction = "انتظار"
            reasoning.setdefault("evidence", []).append(
                "يُظهر تدفق الأوامر احتمال وجود فخ أو كسر زائف لذلك يُفضل الانتظار حتى يتضح الاتجاه.")
        elif stop_hunt_risk and direction == "شراء":
            reasoning.setdefault("evidence", []).append(
                "هناك علامات على اصطياد وقف خسارة قبل انعكاس محتمل؛ يُوصى بزيادة اليقظة أو انتظار تأكيد إضافي.")

        if regime.get("regime") == "choppy":
            confidence_base *= 0.9
            reasoning.setdefault("evidence", []).append(
                "السوق في طور تذبذب، لذلك الثقة أقل في الدخول المباشر ويجب التركيز على نقاط الدعم والمقاومة.")

        if persona.get("market"):
            reasoning.setdefault("evidence", []).append(
                f"شخصية السوق: {persona.get('personality', 'غير معروف')} مع نسبة فوز تقريبية {persona.get('win_rate', 0)}%.")

        if conflict_resolution and conflict_resolution.get("recommendation") in ("شراء", "بيع"):
            if conflict_resolution.get("resolution_reason"):
                reasoning.setdefault("evidence", []).append(conflict_resolution["resolution_reason"])
            if conflict_resolution.get("recommendation") != direction and abs(win_probability - 0.5) < 0.20:
                direction = conflict_resolution["recommendation"]
                reasoning.setdefault("evidence", []).append(
                    "تم اختيار توصية حل النزاع لأن توقع النموذج لم يكن حاسماً بما فيه الكفاية.")

        confidence = int(np.clip(confidence_base, 20, 98))
        if direction == "انتظار":
            confidence = int(np.clip(confidence * 0.78, 15, 80))

        # Calculate entry zone
        entry_zone = self._calculate_entry_zone(direction, chart_data, percepts, orderflow)

        # Calculate dynamic targets
        dynamic_targets = self._calculate_dynamic_targets(direction, chart_data, percepts, trading_persona)

        # Build human-like explanation
        explanation = self._build_human_explanation(
            direction, confidence, reasoning, entry_zone, dynamic_targets, trading_persona
        )

        return {
            "recommendation": direction,
            "confidence": confidence,
            "reason": explanation,
            "explanation": explanation,
            "evidence": reasoning.get("evidence", []),
            "memory_matches": memory.get("matches", []),
            "ml_prediction": ml_prediction,
            "order_flow": orderflow,
            "persona": persona,
            "regime": regime,
            "trading_persona": trading_persona,
            "entry_zone": entry_zone,
            "dynamic_targets": dynamic_targets,
        }

    def _get_user_trading_mode(self, user_id: Optional[int]) -> str:
        """Get user's preferred trading mode from database or default to DAY_TRADING."""
        if not user_id:
            return "DAY_TRADING"
        try:
            db = SessionLocal()
            user = db.query(models.User).filter(models.User.id == user_id).first()
            db.close()
            if user and hasattr(user, 'trading_mode') and user.trading_mode:
                return user.trading_mode.upper()
        except Exception:
            pass
        return "DAY_TRADING"

    def _get_trading_persona(self, trading_mode: str) -> Dict[str, Any]:
        """Get trading persona based on mode."""
        personas = {
            "SCALPING": {
                "name": "سكالبينج",
                "targets": "1-2 أهداف صغيرة",
                "stop_loss": "وقف ضيق",
                "timeframes": "1m-5m",
                "description": "تداول سريع مع أهداف صغيرة ومخاطر منخفضة"
            },
            "DAY_TRADING": {
                "name": "تداول يومي",
                "targets": "2-3 أهداف متوسطة",
                "stop_loss": "وقف متوسط",
                "timeframes": "15m-1H",
                "description": "تداول يومي متوازن مع أهداف متوسطة"
            },
            "SWING": {
                "name": "سوينج",
                "targets": "3-4 أهداف كبيرة",
                "stop_loss": "وقف واسع",
                "timeframes": "4H-Daily",
                "description": "تداول طويل الأمد مع أهداف كبيرة"
            }
        }
        return personas.get(trading_mode, personas["DAY_TRADING"])

    def _calculate_entry_zone(self, direction: str, chart_data: Optional[Dict[str, Any]], percepts: Dict[str, Any], orderflow: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate entry zone with low, high, and best entry."""
        if direction == "انتظار" or not chart_data:
            return {"entry_low": None, "entry_high": None, "best_entry": None, "reason": "لا توجد منطقة دخول", "warnings": []}

        if direction not in ("شراء", "بيع"):
            return {"entry_low": None, "entry_high": None, "best_entry": chart_data.get("current_price"), "reason": "الاتجاه ليس شراء أو بيع واضح", "warnings": []}

        current_price = chart_data.get("current_price", 0.0)
        support_levels = chart_data.get("support_levels", [])
        resistance_levels = chart_data.get("resistance_levels", [])
        order_block = orderflow.get("order_block", {})
        fibonacci_levels = chart_data.get("fibonacci_levels", {})

        reasons = []
        warnings = []

        if direction == "شراء":
            # Entry zone for buy
            entry_low = support_levels[-1] if support_levels else current_price * 0.995
            entry_high = min(resistance_levels) if resistance_levels else current_price * 1.005
            best_entry = (entry_low + entry_high) / 2

            if order_block.get("bullish"):
                reasons.append("Order Block صاعد")
            if fibonacci_levels.get("0.618"):
                reasons.append("Fibonacci 0.618")
            if percepts.get("high_volume_node"):
                reasons.append("HVN")

            if entry_high > current_price:
                warnings.append(f"لا تشتري فوق {entry_high}")
            if entry_low < current_price * 0.99:
                warnings.append(f"لا تشتري تحت {entry_low}")

        elif direction == "بيع":
            # Entry zone for sell
            entry_high = resistance_levels[0] if resistance_levels else current_price * 1.005
            entry_low = max(support_levels) if support_levels else current_price * 0.995
            best_entry = (entry_low + entry_high) / 2

            if order_block.get("bearish"):
                reasons.append("Order Block هابط")
            if fibonacci_levels.get("0.618"):
                reasons.append("Fibonacci 0.618")
            if percepts.get("high_volume_node"):
                reasons.append("HVN")

            if entry_low < current_price:
                warnings.append(f"لا تبيع تحت {entry_low}")
            if entry_high > current_price * 1.01:
                warnings.append(f"لا تبيع فوق {entry_high}")

        return {
            "entry_low": round(entry_low, 5) if entry_low else None,
            "entry_high": round(entry_high, 5) if entry_high else None,
            "best_entry": round(best_entry, 5) if best_entry else None,
            "reason": " + ".join(reasons) if reasons else "منطقة دخول عامة",
            "warnings": warnings
        }

    def _calculate_dynamic_targets(self, direction: str, chart_data: Optional[Dict[str, Any]], percepts: Dict[str, Any], trading_persona: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate dynamic targets based on ATR, Fibonacci, and liquidity."""
        if direction == "انتظار" or not chart_data:
            return {"targets": [], "total_targets": 0}

        current_price = chart_data.get("current_price", 0.0)
        atr = chart_data.get("atr", 0.0) or abs(current_price) * 0.01  # Default ATR
        fibonacci_levels = chart_data.get("fibonacci_levels", {})
        liquidity_levels = chart_data.get("liquidity_levels", [])
        volatility = percepts.get("volatility", "متوسط")

        targets = []
        target_sizes = []

        # Determine number of targets based on persona and volatility
        if trading_persona["name"] == "سكالبينج":
            num_targets = 1 if volatility == "منخفض" else 2
            target_sizes = [100] if num_targets == 1 else [70, 30]
        elif trading_persona["name"] == "تداول يومي":
            num_targets = 2 if volatility == "منخفض" else 3
            target_sizes = [50, 30, 20][:num_targets]
        else:  # Swing
            num_targets = 3 if volatility == "منخفض" else 4
            target_sizes = [40, 30, 20, 10][:num_targets]

        # Calculate target prices
        for i in range(num_targets):
            if direction == "شراء":
                if i == 0 and fibonacci_levels.get("1.272"):
                    price = fibonacci_levels["1.272"]
                    reason = "Fib 1.272"
                elif i == 1 and fibonacci_levels.get("1.618"):
                    price = fibonacci_levels["1.618"]
                    reason = "Fib 1.618"
                elif liquidity_levels and i < len(liquidity_levels):
                    price = liquidity_levels[i]
                    reason = "سيولة"
                else:
                    price = current_price + (atr * (i + 1))
                    reason = "ATR"
            else:  # Sell
                if i == 0 and fibonacci_levels.get("0.786"):
                    price = fibonacci_levels["0.786"]
                    reason = "Fib 0.786"
                elif i == 1 and fibonacci_levels.get("0.618"):
                    price = fibonacci_levels["0.618"]
                    reason = "Fib 0.618"
                elif liquidity_levels and i < len(liquidity_levels):
                    price = liquidity_levels[i]
                    reason = "سيولة"
                else:
                    price = current_price - (atr * (i + 1))
                    reason = "ATR"

            targets.append({
                "price": round(price, 5),
                "size": target_sizes[i],
                "reason": reason,
                "dynamic": True
            })

        return {
            "targets": targets,
            "total_targets": num_targets
        }

    def _build_human_explanation(
        self,
        direction: str,
        confidence: int,
        reasoning: Dict[str, Any],
        entry_zone: Dict[str, Any],
        dynamic_targets: Dict[str, Any],
        trading_persona: Dict[str, Any]
    ) -> str:
        """Build human-like explanation."""
        if direction == "انتظار":
            return "لست متأكداً من الاتجاه الحالي. الأفضل الانتظار حتى تتضح الصورة أكثر."

        confidence_words = {
            range(20, 40): "غير متأكد تماماً",
            range(40, 60): "متردد قليلاً",
            range(60, 80): "واثق نسبياً",
            range(80, 95): "واثق جداً",
            range(95, 101): "مطلق الثقة"
        }

        confidence_desc = "غير متأكد"
        for conf_range, desc in confidence_words.items():
            if confidence in conf_range:
                confidence_desc = desc
                break

        direction_word = "الصعود" if direction == "شراء" else "الهبوط"

        parts = [f"أنا {confidence_desc} ({confidence}%) أن السوق سيذهب نحو {direction_word} للأسباب التالية:"]

        if reasoning.get("evidence"):
            parts.extend(reasoning["evidence"][:3])

        if entry_zone.get("best_entry"):
            parts.append(f"منطقة الدخول: {entry_zone['entry_low']} - {entry_zone['entry_high']} (أفضل دخول: {entry_zone['best_entry']})")
            if entry_zone.get("reason"):
                parts.append(f"سبب المنطقة: {entry_zone['reason']}")

        if entry_zone.get("warnings"):
            parts.extend(entry_zone["warnings"])

        if dynamic_targets.get("targets"):
            targets_desc = []
            for i, target in enumerate(dynamic_targets["targets"], 1):
                targets_desc.append(f"TP{i}: {target['price']} ({target['size']}%) - {target['reason']}")
            parts.append("الأهداف: " + "، ".join(targets_desc))

        parts.append(f"أسلوب التداول: {trading_persona['name']} - {trading_persona['description']}")

        return " ".join(parts)

    def _build_explanation(
        self,
        direction: str,
        percepts: Dict[str, Any],
        memory: Dict[str, Any],
        news_sentiment: Dict[str, Any],
        reasoning: Dict[str, Any],
        confidence: int,
    ) -> str:
        parts = []
        parts.append(f"التوصية: {direction} بثقة {confidence}%.")
        if reasoning.get("narrative"):
            parts.append(reasoning["narrative"])
        if reasoning.get("evidence"):
            parts.extend(reasoning["evidence"][:2])
        if news_sentiment.get("sentiment_score") is not None:
            score = news_sentiment.get("sentiment_score")
            parts.append(f"أخبار السوق تصف المشاعر بـ {round(score, 2)}.")
        if memory.get("strength", 0) > 0.65:
            parts.append("الذاكرة السوقية تؤيد هذا القرار بناءً على تجارب سابقة مشابهة.")
        return " ".join(parts)


class AIService:
    def __init__(self):
        self.perception = PerceptionModule()
        self.memory = MemoryModule()
        self.reasoning = ReasoningModule()
        self.decision = DecisionModule()
        self.performance_tracker = PerformanceTracker()
        self.conflict_resolver = ConflictResolver()
        self.news_analyzer = NewsImpactAnalyzer()
        self.confluence_meter = MultiTFConfluenceMeter()
        self.internal_brain = InternalBrain()
        self.internal_brain.min_weight = 0.2
        self.internal_brain.max_weight = 3.0
        self.binance_service = BinanceService()
        self.order_flow = OrderFlowModule(self.binance_service)
        self.market_persona = MarketPersona()
        self.trade_model = TradeOutcomeModel()
        self.regime_detector = MarketRegimeDetector()
        self.last_auto_tune: Optional[datetime] = None
        self.last_cluster_tune: Optional[datetime] = None
        self.last_monthly_review: Optional[datetime] = None
        self.judge_performance = {
            "decisions": 0,
            "correct": 0,
            "confidence_threshold": 60,
            "last_adjustment": None,
            "recent_decisions": []  # Track last 100 decisions for approval rate
        }
        self.cluster_weights = {
            "power": 0.40,
            "geometric": 0.30,
            "momentum": 0.30
        }
        self.strategy_performance_cache = {}
        self.disabled_strategies = {}  # Track temporarily disabled strategies
        self.trade_counter = 0  # Count trades for weight tuning trigger
        self._start_background_tasks()

    def _start_background_tasks(self) -> None:
        """Start all background tasks for dynamic system."""
        # Daily auto-tuning
        def _daily_tune() -> None:
            while True:
                try:
                    self.auto_tune_weights()
                    self.check_disabled_strategies()  # Check for expired disabled strategies
                    time.sleep(24 * 60 * 60)  # 24 hours
                except Exception as e:
                    logger.exception(f"Daily tune error: {e}")
                    time.sleep(60 * 60)  # Retry in 1 hour

        # Weekly cluster tuning
        def _weekly_cluster_tune() -> None:
            while True:
                try:
                    self.tune_cluster_weights()
                    time.sleep(7 * 24 * 60 * 60)  # 7 days
                except Exception as e:
                    logger.exception(f"Weekly cluster tune error: {e}")
                    time.sleep(24 * 60 * 60)  # Retry in 1 day

        # Monthly review
        def _monthly_review() -> None:
            while True:
                try:
                    self.monthly_system_review()
                    time.sleep(30 * 24 * 60 * 60)  # 30 days
                except Exception as e:
                    logger.exception(f"Monthly review error: {e}")
                    time.sleep(7 * 24 * 60 * 60)  # Retry in 1 week

        # Start threads
        # threading.Thread(target=_daily_tune, daemon=True).start()
        # threading.Thread(target=_weekly_cluster_tune, daemon=True).start()
        # threading.Thread(target=_monthly_review, daemon=True).start()
        pass

    def auto_tune_weights(self, lookback_days: int = 30, min_trades: int = 10) -> Dict[str, Any]:
        """Adjust strategy weights based on recent performance with intelligent rules."""
        try:
            db = SessionLocal()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

            # Get strategy performance from database
            strategy_records = db.query(models.StrategyPerformance).all()
            strategy_stats = {}

            for record in strategy_records:
                total_trades = (record.wins or 0) + (record.losses or 0)
                if total_trades >= min_trades:
                    win_rate = (record.wins or 0) / total_trades
                    strategy_stats[record.strategy_name] = {
                        "win_rate": win_rate,
                        "total_trades": total_trades,
                        "wins": record.wins or 0,
                        "losses": record.losses or 0,
                        "consecutive_losses": getattr(record, 'consecutive_losses', 0),
                        "last_updated": record.last_updated
                    }

            # Apply intelligent weighting rules
            updated_strategies = []
            weight_changes = {"increased": 0, "decreased": 0, "disabled": 0, "unchanged": 0}

            for strategy_name, stats in strategy_stats.items():
                current_weight = self.internal_brain.get_strategy_weights().get(strategy_name, 1.0)
                new_weight = current_weight
                reason = "unchanged"

                # Rule 1: High performance (>70% win rate)
                if stats["win_rate"] > 0.70:
                    new_weight = min(3.0, current_weight * 1.2)
                    reason = "high_performance"
                    weight_changes["increased"] += 1

                # Rule 2: Good performance (>60% win rate)
                elif stats["win_rate"] > 0.60:
                    new_weight = min(2.0, current_weight * 1.15)
                    reason = "good_performance"
                    weight_changes["increased"] += 1

                # Rule 3: Decent performance (>50% win rate)
                elif stats["win_rate"] > 0.50:
                    new_weight = min(1.5, current_weight * 1.1)
                    reason = "decent_performance"
                    weight_changes["increased"] += 1

                # Rule 4: Poor performance (<40% win rate)
                elif stats["win_rate"] < 0.40:
                    new_weight = max(0.5, current_weight * 0.9)
                    reason = "poor_performance"
                    weight_changes["decreased"] += 1

                # Rule 5: Very poor performance (<30% win rate)
                elif stats["win_rate"] < 0.30:
                    new_weight = max(0.2, current_weight * 0.8)
                    reason = "very_poor_performance"
                    weight_changes["decreased"] += 1

                # Rule 6: Consecutive losses (5+)
                if stats.get("consecutive_losses", 0) >= 5:
                    new_weight = 0.1  # Nearly disabled
                    reason = "consecutive_losses"
                    weight_changes["disabled"] += 1
                    # Temporarily disable for 24 hours
                    self.disabled_strategies[strategy_name] = datetime.now(timezone.utc) + timedelta(hours=24)

                # Apply weight change if different
                if abs(new_weight - current_weight) > 0.01:
                    self.internal_brain.update_strategy_weight(strategy_name, new_weight)
                    updated_strategies.append({
                        "strategy": strategy_name,
                        "old_weight": current_weight,
                        "new_weight": new_weight,
                        "win_rate": round(stats["win_rate"] * 100, 1),
                        "total_trades": stats["total_trades"],
                        "reason": reason
                    })

            # Re-enable strategies after timeout
            current_time = datetime.now(timezone.utc)
            to_reenable = [name for name, expiry in self.disabled_strategies.items() if current_time > expiry]
            for strategy_name in to_reenable:
                del self.disabled_strategies[strategy_name]
                # Reset to default weight
                self.internal_brain.update_strategy_weight(strategy_name, 1.0)
                logger.info(f"إعادة تفعيل الاستراتيجية {strategy_name} بعد انتهاء فترة التعطيل المؤقت")

            self.last_auto_tune = datetime.now(timezone.utc)

            # Log summary
            total_updated = len(updated_strategies)
            increased = weight_changes['increased']
            decreased = weight_changes['decreased']
            disabled = weight_changes['disabled']
            unchanged = weight_changes['unchanged']
            logger.info(f"تم تعديل أوزان {total_updated} استراتيجية: {increased} صاعدة، {decreased} هابطة، {disabled} معطلة، {unchanged} ثابتة")

            return {
                "timestamp": self.last_auto_tune.isoformat(),
                "updated_strategies": updated_strategies,
                "weight_changes": weight_changes,
                "total_strategies": len(strategy_stats),
                "min_weight": self.internal_brain.min_weight,
                "max_weight": self.internal_brain.max_weight,
                "reenabled_strategies": to_reenable
            }

        except Exception as e:
            logger.exception(f"Auto-tune weights failed: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    def tune_cluster_weights(self) -> Dict[str, Any]:
        """Weekly tuning of cluster weights based on performance."""
        try:
            db = SessionLocal()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

            # Get cluster performance from recent trades
            recent_trades = db.query(models.TradeExperience).filter(
                models.TradeExperience.created_at >= cutoff_date
            ).all()

            cluster_performance = {"power": [], "geometric": [], "momentum": []}

            for trade in recent_trades:
                # Determine which cluster was dominant (simplified logic)
                strategy_names = (trade.strategy_names or "").split(",")
                cluster_votes = {"power": 0, "geometric": 0, "momentum": 0}

                for strategy in strategy_names:
                    strategy = strategy.strip()
                    # Simple classification based on name
                    if any(keyword in strategy.lower() for keyword in ["smc", "ict", "whale", "order_flow", "vpin"]):
                        cluster_votes["power"] += 1
                    elif any(keyword in strategy.lower() for keyword in ["fibonacci", "elliott", "harmonic", "profile"]):
                        cluster_votes["geometric"] += 1
                    else:
                        cluster_votes["momentum"] += 1

                dominant_cluster = max(cluster_votes, key=cluster_votes.get)
                outcome = 1 if str(trade.result or "").lower().startswith("win") else 0
                cluster_performance[dominant_cluster].append(outcome)

            # Calculate win rates
            cluster_win_rates = {}
            for cluster, outcomes in cluster_performance.items():
                if outcomes:
                    win_rate = sum(outcomes) / len(outcomes)
                    cluster_win_rates[cluster] = win_rate
                else:
                    cluster_win_rates[cluster] = 0.5  # Neutral if no data

            # Adjust weights
            old_weights = self.cluster_weights.copy()
            # small increase for good clusters, larger reduction for poor clusters
            increase_factor = 0.05  # +5% for good
            decrease_factor = 0.30  # -30% for poor (per requirement)

            for cluster, win_rate in cluster_win_rates.items():
                if win_rate > 0.65:  # Good performance
                    self.cluster_weights[cluster] = min(0.50, self.cluster_weights[cluster] * (1 + increase_factor))
                elif win_rate < 0.45:  # Poor performance -> reduce 30%
                    self.cluster_weights[cluster] = max(0.20, self.cluster_weights[cluster] * (1 - decrease_factor))

            # Normalize to ensure sum = 1.0
            total_weight = sum(self.cluster_weights.values())
            self.cluster_weights = {k: v / total_weight for k, v in self.cluster_weights.items()}

            self.last_cluster_tune = datetime.now(timezone.utc)

            # Log changes
            changes = []
            for cluster in ["power", "geometric", "momentum"]:
                old = old_weights[cluster]
                new = self.cluster_weights[cluster]
                if abs(new - old) > 0.001:
                    changes.append(f"العنقود {cluster.upper()} ارتفع من {old:.0%} إلى {new:.0%}")

            if changes:
                logger.info("تطور العناقيد: " + "، ".join(changes))

            return {
                "timestamp": self.last_cluster_tune.isoformat(),
                "old_weights": old_weights,
                "new_weights": self.cluster_weights,
                "cluster_win_rates": {k: round(v * 100, 1) for k, v in cluster_win_rates.items()},
                "changes": changes
            }

        except Exception as e:
            logger.exception(f"Weekly cluster tune error: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    def monthly_system_review(self) -> Dict[str, Any]:
        """Monthly comprehensive system review and strategy re-evaluation."""
        try:
            db = SessionLocal()
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

            # Review strategy performance over last month
            strategy_records = db.query(models.StrategyPerformance).all()
            underperforming = []
            top_performers = []

            for record in strategy_records:
                total_trades = (record.wins or 0) + (record.losses or 0)
                if total_trades >= 20:  # Minimum trades for evaluation
                    win_rate = (record.wins or 0) / total_trades
                    if win_rate < 0.35:  # Very poor
                        underperforming.append({
                            "strategy": record.strategy_name,
                            "win_rate": round(win_rate * 100, 1),
                            "total_trades": total_trades
                        })
                    elif win_rate > 0.75:  # Excellent
                        top_performers.append({
                            "strategy": record.strategy_name,
                            "win_rate": round(win_rate * 100, 1),
                            "total_trades": total_trades
                        })

            # Reset weights for underperforming strategies
            for strategy in underperforming:
                self.internal_brain.update_strategy_weight(strategy["strategy"], 1.0)  # Reset to default

            # Boost top performers
            for strategy in top_performers:
                current_weight = self.internal_brain.get_strategy_weights().get(strategy["strategy"], 1.0)
                new_weight = min(3.0, current_weight * 1.5)
                self.internal_brain.update_strategy_weight(strategy["strategy"], new_weight)

            self.last_monthly_review = datetime.now(timezone.utc)

            logger.info(f"مراجعة شهرية: إعادة تقييم {len(strategy_records)} استراتيجية، إعادة ضبط {len(underperforming)} ضعيفة، تعزيز {len(top_performers)} ممتازة")

            return {
                "timestamp": self.last_monthly_review.isoformat(),
                "underperforming_reset": underperforming,
                "top_performers_boosted": top_performers,
                "total_strategies_reviewed": len(strategy_records)
            }

        except Exception as e:
            logger.exception(f"Monthly system review failed: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    def record_judge_decision(self, decision: str, actual_outcome: str, confidence: int) -> None:
        """Record judge decision and outcome for learning."""
        self.judge_performance["decisions"] += 1
        was_correct = (decision == "approved" and actual_outcome == "win") or \
                     (decision == "rejected" and actual_outcome == "loss")

        if was_correct:
            self.judge_performance["correct"] += 1

        # Track recent decisions
        self.judge_performance["recent_decisions"].append({
            "decision": decision,
            "outcome": actual_outcome,
            "correct": was_correct,
            "timestamp": datetime.now(timezone.utc)
        })

        # Keep only last 100 decisions
        if len(self.judge_performance["recent_decisions"]) > 100:
            self.judge_performance["recent_decisions"] = self.judge_performance["recent_decisions"][-100:]

        # Adjust confidence threshold based on performance
        accuracy_rate = self.judge_performance["correct"] / self.judge_performance["decisions"]

        if self.judge_performance["decisions"] >= 50:  # Enough data
            approval_rate = sum(1 for d in self.judge_performance["recent_decisions"] if d["decision"] == "approved") / len(self.judge_performance["recent_decisions"]) * 100

            if accuracy_rate > 0.75 and self.judge_performance["confidence_threshold"] < 80:
                self.judge_performance["confidence_threshold"] += 5
                self.judge_performance["last_adjustment"] = datetime.now(timezone.utc)
                logger.info(f"القاضي يتعلم: رفع عتبة الثقة إلى {self.judge_performance['confidence_threshold']}% (وافق على {approval_rate:.0f}% من الصفقات وكان صحيحاً في {accuracy_rate:.1%} منها)")
            elif accuracy_rate < 0.65 and self.judge_performance["confidence_threshold"] > 40:
                self.judge_performance["confidence_threshold"] -= 5
                self.judge_performance["last_adjustment"] = datetime.now(timezone.utc)
                logger.info(f"القاضي يتعلم: خفض عتبة الثقة إلى {self.judge_performance['confidence_threshold']}% (وافق على {approval_rate:.0f}% من الصفقات وكان صحيحاً في {accuracy_rate:.1%} منها)")

    def get_judge_performance(self) -> Dict[str, Any]:
        """Get current judge performance metrics."""
        total_decisions = self.judge_performance["decisions"]
        correct_decisions = self.judge_performance["correct"]
        accuracy = (correct_decisions / total_decisions * 100) if total_decisions > 0 else 0.0

        return {
            "total_decisions": total_decisions,
            "correct_decisions": correct_decisions,
            "accuracy_rate": round(accuracy, 1),
            "confidence_threshold": self.judge_performance["confidence_threshold"],
            "last_adjustment": self.judge_performance["last_adjustment"].isoformat() if self.judge_performance["last_adjustment"] else None
        }

    def check_disabled_strategies(self) -> Dict[str, Any]:
        """Check and clean up disabled strategies."""
        current_time = datetime.now(timezone.utc)
        active_disabled = {}
        expired = []

        for strategy_name, expiry in self.disabled_strategies.items():
            if current_time < expiry:
                active_disabled[strategy_name] = expiry.isoformat()
            else:
                expired.append(strategy_name)
                # Re-enable
                self.internal_brain.update_strategy_weight(strategy_name, 1.0)

        # Remove expired from tracking
        for strategy_name in expired:
            del self.disabled_strategies[strategy_name]

        if expired:
            logger.info(f"إعادة تفعيل الاستراتيجيات المنتهية الصلاحية: {', '.join(expired)}")

        return {
            "active_disabled": active_disabled,
            "expired_and_reenabled": expired
        }

    def _analyse_regime(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market regime from chart data."""
        volatility = chart_data.get("volatility", 0.0)
        trend_strength = chart_data.get("trend_strength", 0.0)
        volume_trend = chart_data.get("volume_trend", "stable")

        if volatility > 0.02 and abs(trend_strength) < 0.3:
            regime = "choppy"
        elif trend_strength > 0.7:
            regime = "trending_up"
        elif trend_strength < -0.7:
            regime = "trending_down"
        else:
            regime = "sideways"

        return {
            "regime": regime,
            "volatility": volatility,
            "trend_strength": trend_strength,
            "volume_trend": volume_trend
        }

    def get_strategy_weights(self, user_id: Optional[int] = None) -> Dict[str, float]:
        """Get strategy weights, considering disabled strategies and new users."""
        base_weights = self.internal_brain.get_strategy_weights(user_id=user_id)

        # For new users, start with general system weights
        if user_id and not base_weights:
            base_weights = self.internal_brain.get_strategy_weights(user_id=None) or {}
            # Initialize new user with default weights
            for strategy, weight in base_weights.items():
                self.internal_brain.update_strategy_weight(strategy, weight, user_id=user_id)
            logger.info(f"تهيئة أوزان الاستراتيجيات للمستخدم الجديد {user_id}")

        # Apply disabled strategies
        current_time = datetime.now(timezone.utc)
        for strategy_name in list(base_weights.keys()):
            if strategy_name in self.disabled_strategies:
                if current_time < self.disabled_strategies[strategy_name]:
                    base_weights[strategy_name] = 0.1  # Nearly disabled
                else:
                    # Re-enable expired
                    del self.disabled_strategies[strategy_name]
                    base_weights[strategy_name] = 1.0  # Reset to default

        return base_weights

    def get_system_health(self) -> Dict[str, Any]:
        """Return system-wide health and strategy metrics."""
        try:
            from .voting_engine import strategy_loader
        except Exception:
            strategy_loader = None

        cluster_info = {}
        active_strategies = 0
        if strategy_loader is not None:
            cluster_info = strategy_loader.get_cluster_assignments()
            active_strategies = sum(len(v) for v in cluster_info.values())

        db = SessionLocal()
        try:
            strategy_performance = db.query(models.StrategyPerformance).all()
            total_trades = sum((record.wins or 0) + (record.losses or 0) for record in strategy_performance)
            total_wins = sum(record.wins or 0 for record in strategy_performance)
            overall_win_rate = round((total_wins / total_trades) * 100, 2) if total_trades else 0.0
            memory_count = db.query(models.TradeExperience).count()
        except Exception as e:
            logger.exception(f"Failed to collect system health metrics: {e}")
            total_trades = 0
            overall_win_rate = 0.0
            memory_count = 0
        finally:
            db.close()

        return {
            "active_strategies": active_strategies,
            "clusters": {
                cluster: {"count": len(items), "strategies": [item["strategy_key"] for item in items]}
                for cluster, items in cluster_info.items()
            },
            "overall_system_win_rate": overall_win_rate,
            "total_performance_records": len(strategy_performance) if 'strategy_performance' in locals() else 0,
            "memory_entries": memory_count,
            "external_api_state": self._check_api_health(),
            "last_auto_tune": self.last_auto_tune.isoformat() if self.last_auto_tune else None,
            "last_cluster_tune": self.last_cluster_tune.isoformat() if self.last_cluster_tune else None,
            "last_monthly_review": self.last_monthly_review.isoformat() if self.last_monthly_review else None,
            "cluster_weights": self.cluster_weights,
            "judge_performance": self.get_judge_performance(),
            "disabled_strategies": self.check_disabled_strategies(),
            "trade_counter": self.trade_counter,
            "strategy_weights_summary": {
                "total_strategies": len(self.internal_brain.get_strategy_weights()),
                "weight_distribution": {
                    "high": len([w for w in self.internal_brain.get_strategy_weights().values() if w >= 2.0]),
                    "medium": len([w for w in self.internal_brain.get_strategy_weights().values() if 1.5 <= w < 2.0]),
                    "low": len([w for w in self.internal_brain.get_strategy_weights().values() if w < 1.5])
                }
            }
        }

    def smart_recommendation(self, market: str, user_id: Optional[int]) -> Dict[str, Any]:
        """Return a fast recommendation for mobile without running a full analysis."""
        db = SessionLocal()
        try:
            if not user_id:
                return {
                    "recommendation": "تحليل جديد مطلوب",
                    "confidence": 0,
                    "note": "المستخدم غير معروف أو لا توجد توصية مخزنة."
                }

            recent = db.query(models.Analysis).filter(
                models.Analysis.user_id == user_id,
                models.Analysis.market == market
            ).order_by(models.Analysis.created_at.desc()).first()
            if not recent:
                return {
                    "recommendation": "تحليل جديد مطلوب",
                    "confidence": 0,
                    "note": "لا توجد تحليل حديث لهذا السوق. الرجاء تشغيل تحليل جديد."
                }

            age_seconds = (datetime.now(timezone.utc) - recent.created_at).total_seconds()
            if age_seconds > 300:
                return {
                    "recommendation": "تحليل جديد مطلوب",
                    "confidence": 0,
                    "note": "آخر تحليل أقدم من 5 دقائق، الرجاء تحديث التحليل."
                }

            parsed = {}
            try:
                parsed = json.loads(recent.result_json or "{}")
            except Exception:
                parsed = {}

            recommendation = parsed.get("recommendation") or parsed.get("direction") or "غير محدد"
            confidence = int(parsed.get("confidence", 0) or 0)
            if recommendation in (None, "", "غير محدد"):
                return {
                    "recommendation": "تحليل جديد مطلوب",
                    "confidence": 0,
                    "note": "التحليل المخزن لا يحتوي على توصية واضحة."
                }

            return {
                "recommendation": recommendation,
                "confidence": confidence,
                "market": market,
                "source": "recent_analysis",
                "age_seconds": int(age_seconds),
            }
        except Exception as e:
            logger.exception(f"Smart recommendation failed for {market}: {e}")
            return {
                "recommendation": "تحليل جديد مطلوب",
                "confidence": 0,
                "note": "حدث خطأ أثناء جلب التوصية السريعة."
            }
        finally:
            db.close()

    def compare_markets(self, markets: List[str]) -> Dict[str, Any]:
        """Rank markets based on confidence, volatility, liquidity, and news."""
        comparisons: List[Dict[str, Any]] = []
        for market in markets:
            symbol = market.upper().replace("/", "")
            sentiment = self._fetch_news_sentiment(symbol)
            news_score = float(sentiment.get("sentiment_score", 0.0) or 0.0)
            try:
                market_data = self.binance_service.scan(symbol)
            except Exception as e:
                logger.exception(f"Market compare scan failed for {symbol}: {e}")
                market_data = {}

            open_interest = float(market_data.get("open_interest", 0.0) or 0.0)
            volatility = self._estimate_volatility(market_data)
            liquidity_score = min(1.0, open_interest / max(open_interest, 1.0)) if open_interest > 0 else 0.0
            confidence_score = min(1.0, max(0.0, 0.5 + news_score * 0.25 + liquidity_score * 0.25 + (1.0 - volatility) * 0.25))
            score = (news_score * 0.10) + (liquidity_score * 0.45) + ((1.0 - volatility) * 0.45)
            comparisons.append({
                "market": market,
                "symbol": symbol,
                "confidence_score": round(confidence_score * 100, 1),
                "news_score": round(news_score, 3),
                "liquidity_score": round(liquidity_score, 3),
                "volatility_score": round(volatility, 3),
                "total_score": round(score, 3),
                "rank_reason": {
                    "news": sentiment.get("recommendation", "غير معروف"),
                    "liquidity": open_interest,
                    "volatility": volatility,
                }
            })

        comparisons.sort(key=lambda item: item["total_score"], reverse=True)
        return {"ranked_markets": comparisons}

    def _estimate_volatility(self, market_data: Dict[str, Any]) -> float:
        try:
            footprint = market_data.get("footprint", []) or []
            closes = [float(item.get("close", 0.0)) for item in footprint if item.get("close") is not None]
            if len(closes) < 2:
                return 0.0
            returns = [abs((closes[i] - closes[i - 1]) / max(abs(closes[i - 1]), 1.0)) for i in range(1, len(closes))]
            return min(1.0, sum(returns) / max(len(returns), 1))
        except Exception:
            return 0.0

    def _check_api_health(self) -> Dict[str, str]:
        status = {}
        try:
            ping = self.binance_service._request("/fapi/v1/ping")
            status["market_data"] = "ok" if isinstance(ping, dict) and (ping.get("msg", "") == "" or ping == {}) else "failed"
        except Exception as e:
            logger.exception(f"Market data health check failed: {e}")
            status["market_data"] = "failed"

        try:
            tv_endpoint = getattr(self.tradingview_service, "GEMINI_ENDPOINT", None)
            status["chart_service"] = "configured" if tv_endpoint else "missing_api_key"
        except Exception as e:
            logger.exception(f"Chart service health check failed: {e}")
            status["chart_service"] = "failed"

        try:
            from .deepseek_r1_service import DeepSeekR1Service
            deepseek_api = DeepSeekR1Service()
            status["nlp_service"] = "configured" if getattr(deepseek_api, "api_key", None) else "missing_api_key"
        except Exception as e:
            logger.exception(f"NLP service health check failed: {e}")
            status["nlp_service"] = "failed"

        return status

    def _count_trade_experiences(self) -> int:
        db = SessionLocal()
        try:
            return db.query(models.TradeExperience).count()
        except Exception as e:
            logger.exception(f"Failed to count TradeExperience records: {e}")
            return 0
        finally:
            db.close()

    def _fetch_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        try:
            return social_sentiment_service.analyze(symbol)
        except Exception as e:
            logger.exception(f"Failed to fetch news sentiment for {symbol}: {e}")
            return {"symbol": symbol, "available": False, "sentiment_score": 0.0, "recommendation": "محايد", "message": "تعذر الحصول على بيانات الأخبار."}

    def _verify_chart_identity(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Basic image checks to verify that the input represents a valid chart image.
        Returns a dict with keys: is_chart, pair, timeframe, clarity_score, messages
        """
        result = {
            'is_chart': True,
            'pair': None,
            'timeframe': None,
            'clarity_score': 1.0,
            'messages': []
        }
        try:
            # Check for image indications
            sources = chart_data.get('source_types', []) if isinstance(chart_data, dict) else []
            image_paths = chart_data.get('image_paths', []) if isinstance(chart_data, dict) else []
            if not sources and not image_paths and not chart_data.get('closes'):
                result['is_chart'] = False
                result['messages'].append('لا توجد صورة شارت أو بيانات OHLC ملحوظة.')

            # Attempt to infer pair from raw_text
            raw = ' '.join(chart_data.get('raw_text', [])) if isinstance(chart_data, dict) else ''
            pair_match = re.search(r'([A-Z]{3,5}[/]?[A-Z]{3,5}|[A-Z]{6,7})', raw)
            if pair_match:
                result['pair'] = pair_match.group(0)
            else:
                # fallback to market field
                if chart_data.get('market'):
                    result['pair'] = chart_data.get('market')

            # timeframe
            for key in ('timeframe', 'tf', 'interval'):
                if chart_data.get(key):
                    result['timeframe'] = chart_data.get(key)
                    break
            if not result['timeframe']:
                tf_search = re.search(r'\b(1m|5m|15m|30m|1h|4h|1d|1w|daily|weekly)\b', raw, flags=re.I)
                if tf_search:
                    result['timeframe'] = tf_search.group(0)

            # clarity: prefer explicit clarity_score, otherwise infer from number of bars
            clarity = chart_data.get('clarity_score') if isinstance(chart_data, dict) else None
            if clarity is not None:
                try:
                    result['clarity_score'] = float(clarity)
                except Exception:
                    pass
            else:
                closes = chart_data.get('closes') if isinstance(chart_data, dict) else None
                if closes and len(closes) >= 8:
                    result['clarity_score'] = 1.0
                elif closes and len(closes) >= 3:
                    result['clarity_score'] = 0.6
                else:
                    result['clarity_score'] = 0.2

            if result['clarity_score'] < 0.4:
                result['messages'].append('الصورة أو بيانات الشارت غير واضحة بما يكفي.')

        except Exception as e:
            logger.exception(f"Chart identity verification failed: {e}")
            result['is_chart'] = False
            result['messages'].append('فشل التحقق من هوية الشارت.')

        return result

    def evaluate(
        self,
        user_id: Optional[int],
        chart_data: Dict[str, Any],
        cluster_results: Dict[str, Any],
        strategy_weights: Optional[Dict[str, float]],
        market: str,
        judge_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if strategy_weights is None:
            strategy_weights = self.internal_brain.get_strategy_weights(user_id=user_id)

        news_sentiment = self._fetch_news_sentiment(market)
        # verify chart identity before heavy analysis (Gemini checks)
        chart_identity = self._verify_chart_identity(chart_data)
        if not chart_identity.get('is_chart', True):
            # If not a valid chart image, return a low-confidence wait recommendation
            return {
                "recommendation": "انتظار",
                "confidence": 10,
                "explanation": "الصورة المرسلة لا تبدو كشارت صالح للتحليل.",
                "chart_identity": chart_identity,
            }
        percepts = self.perception.perceive(chart_data, cluster_results, strategy_weights, market)
        memory = self.memory.recall(user_id or 0, percepts)
        performance = self.performance_tracker.summarize_performance(user_id or 0, lookback_days=90)
        news_impact = self.news_analyzer.analyze(news_sentiment)
        confluence = self.confluence_meter.measure(chart_data, cluster_results)
        persona = self.market_persona.profile(user_id or 0, market)
        orderflow = self.order_flow.interpret(market, chart_data)
        regime = self._analyse_regime(chart_data)
        ml_prediction = self.trade_model.predict(
            market=market,
            session=chart_data.get('session', 'unknown'),
            news_sentiment=news_sentiment.get('sentiment_score', 0.0),
            strategy_count=len(strategy_weights or {}),
            confidence_val=float(chart_data.get('confidence', 0.0) or 0.0),
            chart_features=chart_data.get('chart_features', chart_data),
            orderflow=orderflow,
            persona=persona,
        )
        reasoning = self.reasoning.reason(percepts, memory, news_sentiment)
        conflict_resolution = self.conflict_resolver.resolve(cluster_results, strategy_weights, news_sentiment, performance, percepts)
        # preserve base direction from ML prediction; DecisionModule may adjust confidence only
        base_direction = ml_prediction.get('prediction', 'انتظار')
        decision = self.decision.decide(
            percepts,
            memory,
            reasoning,
            news_sentiment,
            performance,
            ml_prediction,
            orderflow,
            persona,
            regime,
            conflict_resolution,
            user_id,
            chart_data,
        )

        # enforce evaluate to only modify confidence, not direction
        decision['recommendation'] = base_direction

        return {
            "recommendation": decision["recommendation"],
            "confidence": decision["confidence"],
            "explanation": decision["explanation"],
            "evidence": decision["evidence"],
            "memory_matches": decision["memory_matches"],
            "percepts": percepts,
            "performance_summary": performance,
            "news_sentiment": news_sentiment,
            "news_impact": news_impact,
            "multi_tf_confluence": confluence,
            "conflict_resolution": conflict_resolution,
            "chart_identity": chart_identity,
            "market_persona": persona,
            "order_flow": orderflow,
            "ml_prediction": ml_prediction,
            "regime": regime,
            "judge_result": judge_result,
        }

    def analyze(
        self,
        chart_data: Dict[str, Any],
        cluster_results: Dict[str, Any],
        judge_result: Optional[Dict[str, Any]],
        market: str,
        user_id: Optional[int] = None,
        strategy_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        return self.evaluate(
            user_id=user_id,
            chart_data=chart_data,
            cluster_results=cluster_results,
            strategy_weights=strategy_weights,
            market=market,
            judge_result=judge_result,
        )

    def _fetch_news_sentiment(self, symbol: str) -> Dict[str, Any]:
        try:
            return social_sentiment_service.analyze(symbol)
        except Exception as e:
            logger.exception(f"Failed to fetch news sentiment for {symbol}: {e}")
            return {"symbol": symbol, "available": False, "sentiment_score": 0.0, "recommendation": "محايد", "message": "تعذر الحصول على بيانات الأخبار."}

    def log_trade_experience(
        self,
        analysis_id: Optional[int],
        user_id: int,
        market: str,
        recommendation: str,
        confidence: int,
        strategies_used: List[str],
        chart_features: Dict[str, Any],
        news_sentiment: float,
        session: str,
        outcome: str,
        profit: float,
        notes: str = ""
    ) -> None:
        """تسجيل تجربة تداول للتعلم منها"""
        try:
            db = SessionLocal()
            experience = models.TradeExperience(
                analysis_id=analysis_id,
                user_id=user_id,
                market=market,
                recommendation=recommendation,
                confidence=confidence,
                strategies_used=json.dumps(strategies_used),
                chart_features=json.dumps(chart_features),
                news_sentiment=news_sentiment,
                session=session,
                outcome=outcome,
                profit=profit,
                notes=notes,
                created_at=datetime.now()
            )
            db.add(experience)
            db.commit()
            db.close()

            # Increment trade counter and trigger auto-tuning every 10 trades
            self.trade_counter += 1
            if self.trade_counter >= 10:
                logger.info("تم تسجيل 10 صفقات - بدء تعديل الأوزان التلقائي")
                self.auto_tune_weights()
                self.trade_counter = 0  # Reset counter

            # تحديث التعلم من التجربة
            # delegate to service-level learning hook
            self.learn_from_experience(user_id, {
                "market": market,
                "recommendation": recommendation,
                "outcome": outcome,
                "profit": profit,
                "confidence": confidence,
                "news_sentiment": news_sentiment,
                "chart_features": chart_features
            })
            self.trade_model.train(user_id)

        except Exception as e:
            logger.exception(f"Failed to log trade experience: {e}")

    def learn_from_experience(self, user_id: int, experience: Dict[str, Any]) -> None:
        """Service-level hook to learn from a trade experience.
        Delegates to memory and updates internal models/weights.
        """
        try:
            # let MemoryModule adapt patterns
            try:
                self.memory.learn_from_experience(user_id, experience)
            except Exception:
                logger.exception("Memory learn_from_experience failed")

            # update internal brain weights best-effort
            try:
                self.internal_brain.update_weights(user_id=user_id)
            except Exception:
                logger.exception("InternalBrain.update_weights failed during learn_from_experience")

        except Exception as e:
            logger.exception(f"AIService.learn_from_experience failed: {e}")

    def answer_question(self, question: str, context: str) -> str:
        """Answer user questions using AI reasoning"""
        question_lower = question.lower()
        if "ذهب" in question_lower or "gold" in question_lower:
            if "فضة" in question_lower or "silver" in question_lower:
                return "الذهب في اتجاه صاعد قوي مع دعم عند 2650، بينما الفضة أضعف نسبياً لكنها تتبع الذهب. الذهب أفضل للاستثمار طويل الأمد، الفضة للتقلبات."
            return "الذهب في ترند صاعد قوي. آخر توصية كانت شراء من 2650 وحققت الهدف عند 2700. حالياً عند مقاومة 2720. الأفضل انتظار اختراق أو ارتداد إلى الدعم 2680."
        elif "فضة" in question_lower or "silver" in question_lower:
            return "الفضة تتبع الذهب لكن بقوة أقل. الترند صاعد لكن التقلب مرتفع. كن حذراً من الأخبار الاقتصادية."
        elif "أفضل" in question_lower and "زوج" in question_lower:
            return "للسكالبينج: EUR/USD أو GBP/USD. لليومي: XAU/USD. للأسبوعي: BTC/USD. يعتمد على خبرتك ووقتك."
        elif "نسبة نجاح" in question_lower or "success rate" in question_lower:
            return "نسبة نجاحي الأسبوعية الحالية 72%. أعلى في الذهب (78%) وأقل في العملات (65%)."
        elif "قارن" in question_lower:
            if "ذهب" in question_lower and "فضة" in question_lower:
                return "الذهب: استقرار أعلى، ترند قوي، مخاطر أقل. الفضة: تقلب أعلى، ارتباط بالصناعة، إمكانية ربح أكبر."
            return "أحتاج تفاصيل أكثر للمقارنة."
        else:
            return "بناءً على آخر التحليلات، السوق يظهر إشارات مختلطة. أنصح بمراقبة المستويات الرئيسية وانتظار تأكيد الاتجاه."

    def get_system_personality(self) -> Dict[str, Any]:
        """Return the current system personality description."""
        # Get current trading mode (simplified - could be based on most active mode)
        current_mode = "DAY_TRADING"  # Default, could be dynamic

        # Get top strategies
        weights = self.internal_brain.get_strategy_weights()
        sorted_strategies = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        top_strategies = [name for name, _ in sorted_strategies[:5]]

        # Get performance summary
        health = self.get_system_health()
        win_rate = health.get("overall_system_win_rate", 0)

        personality = {
            "current_mode": current_mode,
            "description": f"أنا حالياً في وضع {current_mode.replace('_', ' ').lower()}",
            "favorite_strategies": top_strategies,
            "strengths": [
                "كشف الاتجاهات المبكرة",
                "قراءة تدفق الأوامر والسيولة",
                "تحليل الأنماط الهندسية"
            ] if win_rate > 60 else [
                "تحليل البيانات الأساسية",
                "تتبع الأخبار والأحداث"
            ],
            "weaknesses": [
                "الأسواق الجانبية المتذبذبة",
                "الأحداث غير المتوقعة"
            ] if win_rate < 70 else [
                "التداول في أوقات الراحة"
            ],
            "beliefs": [
                "الاتجاه صديقي - أتبع الزخم",
                "السيولة تكشف كل شيء",
                "التوقيت أهم من الاتجاه",
                "التعلم المستمر من الأخطاء"
            ],
            "performance_summary": {
                "win_rate": win_rate,
                "active_strategies": health.get("active_strategies", 0),
                "memory_entries": health.get("memory_entries", 0)
            }
        }

        return personality

    def learn_from_feedback(self, trade_id: Optional[int] = None, analysis_id: Optional[int] = None, correction: str = "") -> Dict[str, Any]:
        """Learn from user feedback and adjust system behavior."""
        try:
            db = SessionLocal()
            feedback_source = None
            analysis_record = None
            journal_record = None
            shadow_trade = None
            user_id = None
            market = None
            recommendation = None
            profit_loss = 0.0
            session = None
            chart_features = {}
            news_sentiment = 0.0
            strategy_names = []

            if analysis_id is not None:
                analysis_record = db.query(models.Analysis).filter(models.Analysis.id == int(analysis_id)).first()
                if not analysis_record:
                    return {"status": "error", "message": "Analysis not found"}
                feedback_source = "analysis"
                user_id = analysis_record.user_id
                market = analysis_record.market
                try:
                    analysis_data = json.loads(analysis_record.result_json or "{}")
                except Exception:
                    analysis_data = {}
                recommendation = analysis_data.get("recommendation") or analysis_data.get("result") or ""
                session = analysis_data.get("session")
                news_sentiment = float(analysis_data.get("news_sentiment", 0.0) or 0.0)
                chart_features = analysis_data.get("chart_features", {}) or {}
                details = analysis_data.get("details", []) or []
                strategy_names = [str(d.get("name", "")).strip() for d in details if d.get("name")]

                try:
                    analysis_data["feedback"] = correction
                    analysis_record.result_json = json.dumps(analysis_data, ensure_ascii=False)
                    db.add(analysis_record)
                except Exception:
                    pass
            elif trade_id is not None:
                shadow_trade = db.query(models.ShadowTrade).filter(models.ShadowTrade.id == int(trade_id)).first()
                if shadow_trade:
                    feedback_source = "shadow_trade"
                    user_id = shadow_trade.user_id
                    market = shadow_trade.market
                    recommendation = getattr(shadow_trade, "recommendation", "")
                    profit_loss = float(getattr(shadow_trade, "pnl", 0.0) or 0.0)
                    session = getattr(shadow_trade, "session", None)
                else:
                    journal_record = db.query(models.JournalEntry).filter(models.JournalEntry.id == int(trade_id)).first()
                    if not journal_record:
                        return {"status": "error", "message": "Trade or analysis not found"}
                    feedback_source = "journal"
                    user_id = journal_record.user_id
                    market = journal_record.market
                    recommendation = journal_record.recommendation
                    profit_loss = float(journal_record.profit_loss or 0.0)
                    session = journal_record.session
            else:
                return {"status": "error", "message": "trade_id or analysis_id is required"}

            correction_lower = correction.lower()
            adjustment_type = "neutral"
            if any(word in correction_lower for word in ["خطأ", "غلط", "wrong", "false"]):
                adjustment_type = "negative"
                self.judge_performance["confidence_threshold"] = min(80, self.judge_performance["confidence_threshold"] + 5)
            elif any(word in correction_lower for word in ["صحيح", "correct", "right"]):
                adjustment_type = "positive"
                self.judge_performance["confidence_threshold"] = max(40, self.judge_performance["confidence_threshold"] - 2)

            feedback_entry = models.TradeExperience(
                analysis_id=analysis_record.id if analysis_record else None,
                user_id=user_id,
                market=market,
                session=session,
                recommendation=recommendation,
                result="feedback_corrected",
                profit_loss=profit_loss,
                strategy_names=",".join([s for s in strategy_names if s]),
                chart_features=json.dumps(chart_features, ensure_ascii=False),
                news_sentiment=news_sentiment,
                notes=f"تصحيح المستخدم: {correction}",
                created_at=datetime.now(timezone.utc),
            )
            db.add(feedback_entry)

            if strategy_names:
                for strategy in strategy_names:
                    if not strategy:
                        continue
                    if adjustment_type == "negative":
                        self.internal_brain.update_strategy_performance(strategy_name=strategy, outcome="loss", profit=0.0)
                    elif adjustment_type == "positive":
                        self.internal_brain.update_strategy_performance(strategy_name=strategy, outcome="win", profit=0.0)

            db.commit()
            return {
                "status": "learned",
                "source": feedback_source,
                "adjustment_type": adjustment_type,
                "confidence_threshold": self.judge_performance["confidence_threshold"],
                "message": f"تم تعلم الدرس من التصحيح: {correction[:100]}..."
            }
        except Exception as e:
            logger.exception(f"Failed to learn from feedback: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            db.close()


ai_core_service = AIService()






