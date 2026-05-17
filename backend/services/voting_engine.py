from typing import Any, Dict, List, Optional
import os
import importlib
import inspect
import logging
import threading
import time
from datetime import datetime, timedelta
from .internal_brain import InternalBrain
from .deepseek_r1_service import DeepSeekR1Service
from .calendar_service import CalendarService
from .data_adapter import DataAdapter
from .ai_core import ai_core_service
import models

logger = logging.getLogger(__name__)

class DynamicStrategyLoader:
    """Loader that discovers strategy classes dynamically from backend/strategies."""

    CLUSTER_KEYWORDS = {
        "power": [
            "smc", "ict", "whale", "liquidation", "vsa", "volume_spread", "order_flow",
            "tape_reading", "footprint", "composite", "operator", "vpin", "toxicity",
            "depth", "market_depth", "dom", "time_and_sales", "absorption", "delta",
            "crypto_whales", "order_flow_tape_reading", "vpin_toxicity", "liquidation_heatmap",
            "market_making", "hft_simulation", "options_flow", "composite_operator_tracking",
        ],
        "geometric": [
            "elliott", "wave", "fibonacci", "fib", "harmonic", "gartley", "butterfly",
            "wyckoff", "market_profile", "profile", "auction", "supply_demand",
            "gann", "pitchfork", "andrews", "xabcd", "crab", "bat", "shark",
            "price_range", "volume_profile", "vwap", "poc", "fair_value",
            "elliott_wave", "fibonacci", "harmonic_patterns", "market_profile",
            "support_resistance", "auction_market_theory", "wyckoff",
        ],
        "momentum": [
            "rsi", "macd", "stochastic", "bollinger", "moving_average", "ma_cross",
            "mean_reversion", "price_action", "pin_bar", "engulfing", "doji",
            "cci", "momentum", "adx", "atr", "ichimoku", "parabolic_sar",
            "divergence", "convergence", "trend", "breakout",
            "bollinger", "rsi", "macd", "stochastic", "moving_averages", "mean_reversion",
            "candlestick_patterns", "chaos_fractal_theory", "dynamic_price_action",
            "regime_detector", "currency_strength", "intermarket", "seasonality",
            "time_sessions", "fear_greed_aggregator", "social_sentiment",
        ],
    }

    FALLBACK_KEYWORDS = {
        "momentum": ["price", "volume", "volatility", "momentum", "oscillator", "rsi", "macd"],
        "power": ["structure", "market structure", "order flow", "liquidity", "whale", "smc", "ict"],
        "geometric": ["support", "resistance", "fibonacci", "fib", "profile", "vwap", "poc", "fair value", "levels", "supply", "demand"],
    }

    def __init__(self, strategies_dir: Optional[str] = None, scan_interval_seconds: int = 300):
        self.strategies_dir = strategies_dir or os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "strategies"))
        self.scan_interval_seconds = scan_interval_seconds
        self.last_scan = datetime.min
        self.loaded_strategies: Dict[str, Dict[str, Any]] = {}
        self.failed_strategies: List[str] = []
        self.cluster_map: Dict[str, List[str]] = {
            "power": [],
            "geometric": [],
            "momentum": []
        }
        self._lock = threading.Lock()
        self._auto_reload_started = False
        self._load_all()

    def _read_file_text(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().lower()
        except Exception:
            return ""

    def _normalize_text(self, *values: str) -> str:
        return " ".join([str(v or "") for v in values]).lower()

    def _scan_strategy_files(self) -> List[str]:
        files: List[str] = []
        for root, _, filenames in os.walk(self.strategies_dir):
            for filename in filenames:
                if filename.endswith(".py") and filename != "__init__.py":
                    files.append(os.path.join(root, filename))
        return files

    def _import_module(self, module_name: str):
        module_paths = [f"strategies.{module_name}", f"backend.strategies.{module_name}"]
        for path in module_paths:
            try:
                return importlib.import_module(path)
            except Exception:
                continue
        self.failed_strategies.append(module_name)
        logger.warning(f"Failed to import strategy module: {module_name}")
        return None

    def _classify_strategy(self, class_name: str, description: str, file_name: str, file_text: str) -> str:
        haystack = self._normalize_text(class_name, description, file_name, file_text)
        scores = {cluster: 0 for cluster in self.CLUSTER_KEYWORDS}
        for cluster, keywords in self.CLUSTER_KEYWORDS.items():
            for keyword in keywords:
                scores[cluster] += haystack.count(keyword)

        if any(score > 0 for score in scores.values()):
            best_cluster = max(scores, key=scores.get)
            logger.debug("Strategy %s classified to '%s' with scores: %s", class_name, best_cluster, scores)
            return best_cluster

        fallback = {cluster: 0 for cluster in self.FALLBACK_KEYWORDS}
        for cluster, keywords in self.FALLBACK_KEYWORDS.items():
            for keyword in keywords:
                fallback[cluster] += haystack.count(keyword)
        if any(value > 0 for value in fallback.values()):
            best_fallback = max(fallback, key=fallback.get)
            logger.debug("Strategy %s classified to '%s' (fallback) with scores: %s", class_name, best_fallback, fallback)
            return best_fallback

        logger.debug("Strategy %s defaulted to 'momentum' cluster", class_name)
        return "momentum"

    def _load_all(self) -> None:
        logger.info("Starting dynamic strategy discovery from %s", self.strategies_dir)
        discovered = {}
        self.failed_strategies = []
        files = self._scan_strategy_files()
        logger.info("Found %d Python files in strategies directory", len(files))
        for file_path in files:
            rel_path = os.path.relpath(file_path, self.strategies_dir)
            module_name = rel_path.replace(os.path.sep, ".")[:-3]
            module = self._import_module(module_name)
            if not module:
                continue

            text = self._read_file_text(file_path)
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if cls.__module__ != module.__name__:
                    continue
                if not name.lower().endswith("strategy"):
                    continue
                description = inspect.getdoc(cls) or ""
                cluster = self._classify_strategy(name, description, module_name, text)
                key = f"{module_name}.{name}"
                discovered[key] = {
                    "module": module_name,
                    "class_name": name,
                    "cluster": cluster,
                    "description": description,
                    "file": file_path,
                }
                logger.info("Strategy %s classified to cluster '%s' (file: %s)", key, cluster, file_path)

        with self._lock:
            self.loaded_strategies = discovered
            self.cluster_map = {
                "power": [key for key, info in discovered.items() if info["cluster"] == "power"],
                "geometric": [key for key, info in discovered.items() if info["cluster"] == "geometric"],
                "momentum": [key for key, info in discovered.items() if info["cluster"] == "momentum"],
            }
            self.last_scan = datetime.utcnow()

        logger.info("Discovered %d strategy classes across all clusters.", len(discovered))
        for cluster_name, keys in self.cluster_map.items():
            logger.info("Cluster '%s' contains %d strategies: %s", cluster_name, len(keys), [k.split('.')[-1] for k in keys])
        if self.failed_strategies:
            logger.warning("Failed to load %d strategy modules: %s", len(self.failed_strategies), self.failed_strategies)

    def refresh_if_needed(self, force: bool = False) -> None:
        if force or (datetime.utcnow() - self.last_scan).total_seconds() >= self.scan_interval_seconds:
            self._load_all()

    def load_for_cluster(self, cluster: str) -> List[Any]:
        self.refresh_if_needed()
        instances: List[Any] = []
        with self._lock:
            keys = list(self.cluster_map.get(cluster, []))
        for key in keys:
            strategy_info = self.loaded_strategies.get(key)
            if not strategy_info:
                continue
            module = self._import_module(strategy_info["module"])
            if not module:
                continue
            try:
                clazz = getattr(module, strategy_info["class_name"])
                instances.append(clazz())
            except Exception as e:
                logger.exception("Failed to instantiate strategy %s: %s", key, e)
                self.failed_strategies.append(key)
        return instances

    def get_cluster_assignments(self) -> Dict[str, List[Dict[str, Any]]]:
        self.refresh_if_needed()
        with self._lock:
            return {
                cluster: [
                    {
                        "strategy_key": key,
                        "module": info["module"],
                        "class_name": info["class_name"],
                        "description": info["description"],
                    }
                    for key, info in self.loaded_strategies.items()
                    if info["cluster"] == cluster
                ]
                for cluster in ("power", "geometric", "momentum")
            }

    def get_all_strategy_keys(self) -> List[str]:
        self.refresh_if_needed()
        with self._lock:
            return list(self.loaded_strategies.keys())

    def get_health(self) -> Dict[str, Any]:
        self.refresh_if_needed()
        with self._lock:
            return {
                "total_discovered": len(self.loaded_strategies),
                "clusters": {cluster: len(keys) for cluster, keys in self.cluster_map.items()},
                "failed_loads": self.failed_strategies[:],
                "last_scan": self.last_scan.isoformat(),
            }

    def start_auto_reload(self) -> None:
        if self._auto_reload_started:
            return
        self._auto_reload_started = True

        def _reload_loop() -> None:
            while True:
                try:
                    self.refresh_if_needed(force=True)
                except Exception as e:
                    logger.exception("Strategy auto-reload failed: %s", e)
                time.sleep(self.scan_interval_seconds)

        thread = threading.Thread(target=_reload_loop, daemon=True)
        thread.start()


strategy_loader = DynamicStrategyLoader()
strategy_loader.start_auto_reload()


class EnvironmentFilter:
    """طبقة 1: فلتر البيئة - يفحص الظروف السوقية قبل التصويت"""

    def __init__(self):
        self.calendar_service = CalendarService()
        # internal brain can provide historical/session stats such as win_rate
        self.internal_brain = InternalBrain()

    def check_environment(self, market: str) -> Dict:
        """يفحص البيئة السوقية باستخدام توقيت GMT (UTC) ويُرجع أحد النتائج:
        'proceed', 'proceed_warn', 'suspend'
        - يستخدم أحداث التقويم بتوقيت UTC
        - يتحقق من يوم الأسبوع (اثنين صباحًا، جمعة مساءً => تحذير)
        - يتحقق من معدل الفوز للزوج في الجلسة الحالية ويُصدر تحذير إذا كان < 40%
        """
        issues: List[str] = []

        # فحص التقويم الاقتصادي (نفترض أن التواريخ تُرجع/تُقارن بالـ UTC)
        upcoming_events = self.calendar_service.get_upcoming_events(hours=4)
        high_impact_events = [e for e in upcoming_events if e.get('impact') == 'high']

        if high_impact_events:
            next_event = min(high_impact_events, key=lambda x: x.get('time_until', timedelta(hours=24)))
            time_until = next_event.get('time_until', timedelta(hours=24))

            if time_until < timedelta(minutes=15):
                issues.append("High impact news in less than 15 minutes")
            elif time_until < timedelta(hours=1):
                issues.append("High impact news within 1 hour")

        # توقيت الجلسة اعتمادًا على GMT/UTC
        utc_now = datetime.utcnow()
        utc_hour = utc_now.hour
        weekday = utc_now.weekday()  # Monday=0 .. Sunday=6

        # جلسات تقريبية حسب UTC ساعات
        if 0 <= utc_hour < 8:
            session = 'asia'
        elif 7 <= utc_hour < 16:
            session = 'europe'
        else:
            session = 'america'

        # أيام الأسبوع خاصة: الاثنين صباحًا و الجمعة مساءً => تحذير
        if weekday == 0 and utc_hour < 12:
            issues.append('Monday morning session - caution')
        if weekday == 4 and utc_hour >= 18:
            issues.append('Friday evening session - caution')

        # فحص أداء الزوج في الجلسة الحالية (إذا كانت الخاصية متاحة في internal_brain)
        try:
            win_rate = None
            if hasattr(self.internal_brain, 'get_pair_win_rate'):
                win_rate = self.internal_brain.get_pair_win_rate(market.upper(), session)
            elif hasattr(self.internal_brain, 'pair_win_rate'):
                win_rate = getattr(self.internal_brain, 'pair_win_rate')(market.upper(), session)

            if isinstance(win_rate, (int, float)):
                if win_rate < 40:
                    issues.append(f'Low session win_rate {win_rate}% for {market} in {session}')
        except Exception:
            # إذا فشل الحصول على الإحصائيات، نتابع بدونها
            pass

        # الخروج بثلاث حالات
        if any('High impact' in i for i in issues):
            recommendation = 'suspend'
        elif issues:
            recommendation = 'proceed_warn'
        else:
            recommendation = 'proceed'

        return {
            'recommendation': recommendation,
            'issues': issues,
            'utc_now': utc_now.isoformat(),
            'session': session
        }

class StrategyClusterBase:
    def _is_strategy_applicable(self, strategy, market: str) -> bool:
        """فلتر بسيط: استراتيجيات المخصصة للعمل مع crypto/forex لا تُستخدم على أنماط سوقية مختلفة"""
        try:
            m = market.upper()
            is_crypto_market = any(suf in m for suf in ('USDT', 'BTC', 'ETH', 'BNB', 'SOL', 'ADA'))
            is_forex_market = any(sym in m for sym in ('USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF')) and not is_crypto_market

            # If strategy declares attributes, prefer them
            if hasattr(strategy, 'crypto_only') and getattr(strategy, 'crypto_only'):
                return is_crypto_market
            if hasattr(strategy, 'forex_only') and getattr(strategy, 'forex_only'):
                return is_forex_market

            # Check module or class name hints
            mod = getattr(strategy.__class__, '__module__', '') or ''
            name = strategy.__class__.__name__.lower()
            modname = mod.lower()
            if 'crypto' in name or 'crypto' in modname or 'chain' in modname:
                return is_crypto_market
            if 'forex' in name or 'fx' in modname or 'currency' in modname:
                return is_forex_market

            # otherwise assume applicable
            return True
        except Exception:
            return True
    def _load_strategies(self, strategy_names: List[str]) -> List:
        loaded = []
        for name in strategy_names:
            try:
                module_name, class_name = name.split('.')
                module = importlib.import_module(f"strategies.{module_name}")
                strategy_class = getattr(module, class_name)
                loaded.append(strategy_class())
            except Exception as e:
                logger.exception(f"Failed to load strategy {name}: {e}")
        return loaded

    def _invoke_strategy(self, strategy, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            signature = inspect.signature(strategy.analyze)
            parameters = list(signature.parameters.values())
            if len(parameters) == 1:
                return strategy.analyze(chart_data)

            kwargs = {}
            for parameter in parameters:
                name = parameter.name
                if name in chart_data:
                    kwargs[name] = chart_data[name]

            if kwargs:
                return strategy.analyze(**kwargs)

            if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters):
                return strategy.analyze(**chart_data)

            positional = []
            for key in ('opens', 'highs', 'lows', 'closes', 'volumes', 'timestamps'):
                if key in chart_data:
                    positional.append(chart_data[key])
            return strategy.analyze(*positional)
        except Exception as e:
            logger.exception(f"Strategy invocation failed for {strategy.__class__.__name__}: {e}")
            raise

    def _strategy_weight(self, strategy_name: str, confidence: int, strategy_weights: Dict[str, float]) -> float:
        base_weight = max(0.1, strategy_weights.get(strategy_name, 1.0))
        return base_weight * max(0.2, min(1.0, confidence / 100.0))

    def _analyze_strategy(self, strategy, chart_data: Dict[str, Any], strategy_weights: Dict[str, float]) -> Dict[str, Any]:
        entry = {
            'strategy': strategy.__class__.__name__,
            'vote': 'بيانات غير كافية',
            'confidence': 0,
            'weight': strategy_weights.get(strategy.__class__.__name__, 1.0),
            'reason': ''
        }
        try:
            result = self._invoke_strategy(strategy, chart_data)
            if not isinstance(result, dict):
                raise ValueError('Strategy result must be a dictionary')

            recommendation = result.get('recommendation') or result.get('direction') or result.get('signal')
            confidence = int(result.get('confidence', result.get('score', 0))) if isinstance(result.get('confidence', result.get('score', 0)), (int, float)) else 0
            if not recommendation:
                entry['reason'] = 'استراتيجية لم تعطِ توصية واضحة'
                return entry

            entry['vote'] = recommendation
            entry['confidence'] = confidence
            entry['weight'] = self._strategy_weight(entry['strategy'], confidence, strategy_weights)
            entry['reason'] = result.get('reason', result.get('analysis', ''))
            entry['raw_result'] = result
        except Exception as e:
            entry['reason'] = f'فشل الاستراتيجية: {e}'
        return entry


class ClusterVoting:
    """طبقة 2: نظام العناقيد - يقسم الاستراتيجيات إلى 3 عناقيد"""

    def __init__(self):
        self.power_cluster = PowerCluster()
        self.geometric_cluster = GeometricCluster()
        self.momentum_cluster = MomentumCluster()

    def vote_clusters(self, chart_data: Dict[str, Any], market: str, strategy_weights: Dict[str, float]) -> Dict:
        """تصويت العناقيد الثلاثة"""
        power_result = self.power_cluster.analyze(chart_data, market, strategy_weights)
        geometric_result = self.geometric_cluster.analyze(chart_data, market, strategy_weights)
        momentum_result = self.momentum_cluster.analyze(chart_data, market, strategy_weights)

        return {
            "power": power_result,
            "geometric": geometric_result,
            "momentum": momentum_result
        }

class PowerCluster(StrategyClusterBase):
    """عنقود القوة - وزن 40% - أين تذهب الأموال الكبيرة؟"""

    def __init__(self):
        self.cluster_name = "power"
        self.strategies = []
        self._refresh_strategies()

    def _refresh_strategies(self) -> None:
        try:
            self.strategies = strategy_loader.load_for_cluster(self.cluster_name)
            logger.info("Refreshed %s cluster with %d strategies", self.cluster_name, len(self.strategies))
        except Exception as e:
            logger.exception("Failed to refresh PowerCluster strategies: %s", e)
            self.strategies = []

    def analyze(self, chart_data: Dict[str, Any], market: str, strategy_weights: Dict[str, float]) -> Dict:
        """تحليل عنقود القوة"""
        self._refresh_strategies()
        votes = {"شراء": 0.0, "بيع": 0.0, "محايد": 0.0}
        total_weight = 0.0
        details = []

        for strategy in self.strategies:
            # تطبيق فلتر نوع السوق (crypto vs forex)
            if not self._is_strategy_applicable(strategy, market):
                continue
            entry = self._analyze_strategy(strategy, chart_data, strategy_weights)
            vote = entry['vote'] if entry['vote'] in ("شراء", "بيع", "محايد") else "محايد"
            votes[vote] += entry['weight']
            total_weight += entry['weight']
            details.append(entry)

        if total_weight == 0:
            return {"direction": "محايد", "confidence": 0, "details": details, "scores": {"buy": 0.0, "sell": 0.0, "neutral": 1.0}}

        buy_score = votes["شراء"] / total_weight
        sell_score = votes["بيع"] / total_weight
        neutral_score = votes["محايد"] / total_weight

        # عتبة إعلان اتجاه العنقود: 60%
        max_score = max(buy_score, sell_score, neutral_score)
        if max_score < 0.6:
            direction = "محايد"
            confidence = int(max_score * 100)
        else:
            if buy_score == max_score:
                direction = "شراء"
                confidence = int(buy_score * 100)
            elif sell_score == max_score:
                direction = "بيع"
                confidence = int(sell_score * 100)
            else:
                direction = "محايد"
                confidence = int(neutral_score * 100)

        return {
            "direction": direction,
            "confidence": confidence,
            "details": details,
            "scores": {"buy": round(buy_score, 3), "sell": round(sell_score, 3), "neutral": round(neutral_score, 3)}
        }

class GeometricCluster(StrategyClusterBase):
    """عنقود الهندسة - وزن 30% - تحديد الأهداف والوقف بدقة"""

    def __init__(self):
        self.cluster_name = "geometric"
        self.strategies = []
        self._refresh_strategies()

    def _refresh_strategies(self) -> None:
        try:
            self.strategies = strategy_loader.load_for_cluster(self.cluster_name)
        except Exception as e:
            logger.exception("Failed to refresh GeometricCluster strategies: %s", e)
            self.strategies = []

    def analyze(self, chart_data: Dict[str, Any], market: str, strategy_weights: Dict[str, float]) -> Dict:
        """تحليل عنقود الهندسة"""
        self._refresh_strategies()
        votes = {"شراء": 0.0, "بيع": 0.0, "محايد": 0.0}
        total_weight = 0.0
        details = []
        targets: List[Any] = []
        stops: List[Any] = []

        for strategy in self.strategies:
            if not self._is_strategy_applicable(strategy, market):
                continue
            entry = self._analyze_strategy(strategy, chart_data, strategy_weights)
            vote = entry['vote'] if entry['vote'] in ("شراء", "بيع", "محايد") else "محايد"
            votes[vote] += entry['weight']
            total_weight += entry['weight']
            details.append(entry)

            if isinstance(entry.get('raw_result'), dict):
                raw_result = entry['raw_result']
                if 'targets' in raw_result and isinstance(raw_result['targets'], list):
                    targets.extend(raw_result['targets'])
                if 'stop_loss' in raw_result:
                    stops.append(raw_result['stop_loss'])

        if total_weight == 0:
            return {"direction": "محايد", "confidence": 0, "details": details, "targets": [], "stops": [], "scores": {"buy": 0.0, "sell": 0.0, "neutral": 1.0}}

        buy_score = votes["شراء"] / total_weight
        sell_score = votes["بيع"] / total_weight
        neutral_score = votes["محايد"] / total_weight

        max_score = max(buy_score, sell_score, neutral_score)
        if max_score < 0.6:
            direction = "محايد"
            confidence = int(max_score * 100)
        else:
            if buy_score == max_score:
                direction = "شراء"
                confidence = int(buy_score * 100)
            elif sell_score == max_score:
                direction = "بيع"
                confidence = int(sell_score * 100)
            else:
                direction = "محايد"
                confidence = int(neutral_score * 100)

        return {
            "direction": direction,
            "confidence": confidence,
            "details": details,
            "targets": targets[:3],
            "stops": stops[:1] if stops else [],
            "scores": {"buy": round(buy_score, 3), "sell": round(sell_score, 3), "neutral": round(neutral_score, 3)}
        }

class MomentumCluster(StrategyClusterBase):
    """عنقود الزخم - وزن 30% - توقيت الدخول"""

    def __init__(self):
        self.cluster_name = "momentum"
        self.strategies = []
        self._refresh_strategies()

    def _refresh_strategies(self) -> None:
        try:
            self.strategies = strategy_loader.load_for_cluster(self.cluster_name)
        except Exception as e:
            logger.exception("Failed to refresh MomentumCluster strategies: %s", e)
            self.strategies = []

    def analyze(self, chart_data: Dict[str, Any], market: str, strategy_weights: Dict[str, float]) -> Dict:
        """تحليل عنقود الزخم"""
        self._refresh_strategies()
        votes = {"شراء": 0.0, "بيع": 0.0, "محايد": 0.0}
        total_weight = 0.0
        details = []
        timing_signals: List[Any] = []

        for strategy in self.strategies:
            if not self._is_strategy_applicable(strategy, market):
                continue
            entry = self._analyze_strategy(strategy, chart_data, strategy_weights)
            vote = entry['vote'] if entry['vote'] in ("شراء", "بيع", "محايد") else "محايد"
            votes[vote] += entry['weight']
            total_weight += entry['weight']
            details.append(entry)

            if isinstance(entry.get('raw_result'), dict) and 'timing' in entry['raw_result']:
                timing_signals.append(entry['raw_result']['timing'])

        if total_weight == 0:
            return {"direction": "محايد", "confidence": 0, "details": details, "timing": [], "scores": {"buy": 0.0, "sell": 0.0, "neutral": 1.0}}

        buy_score = votes["شراء"] / total_weight
        sell_score = votes["بيع"] / total_weight
        neutral_score = votes["محايد"] / total_weight

        max_score = max(buy_score, sell_score, neutral_score)
        if max_score < 0.6:
            direction = "محايد"
            confidence = int(max_score * 100)
        else:
            if buy_score == max_score:
                direction = "شراء"
                confidence = int(buy_score * 100)
            elif sell_score == max_score:
                direction = "بيع"
                confidence = int(sell_score * 100)
            else:
                direction = "محايد"
                confidence = int(neutral_score * 100)

        return {
            "direction": direction,
            "confidence": confidence,
            "details": details,
            "timing": timing_signals,
            "scores": {"buy": round(buy_score, 3), "sell": round(sell_score, 3), "neutral": round(neutral_score, 3)}
        }

class InternalBrainJudge:
    """طبقة 3: القاضي - DeepSeek R1 يراجع النتائج أو يستخدم منطق داخلي عند الحاجة"""

    def __init__(self):
        self.deepseek = DeepSeekR1Service()

    def judge(self, cluster_results: Dict, market: str) -> Dict:
        """القاضي يراجع نتائج العناقيد"""
        context = f"""
        سوق: {market}
        نتائج العناقيد:

        عنقود القوة (40%): {cluster_results['power']['direction']} - ثقة {cluster_results['power']['confidence']}%
        عنقود الهندسة (30%): {cluster_results['geometric']['direction']} - ثقة {cluster_results['geometric']['confidence']}%
        عنقود الزخم (30%): {cluster_results['momentum']['direction']} - ثقة {cluster_results['momentum']['confidence']}%

        هل هناك تناقض منطقي؟ هل النتائج متسقة؟ أي عنقود يجب أن يحصل على فيتو؟
        """

        try:
            judgment = self.deepseek.analyze_consensus(context)
            if judgment.get("use_internal_judge") or not judgment.get("approved", False):
                return self._internal_judge(cluster_results, judgment)

            if judgment.get("veto", False):
                return {
                    "approved": False,
                    "veto": True,
                    "veto_reason": judgment.get("veto_reason", "تعارض في العقل الاستراتيجي"),
                    "confidence_boost": 0,
                    "notes": judgment.get("notes", "DeepSeek رفض القرار")
                }

            return {
                "approved": True,
                "confidence_boost": int(judgment.get("confidence_boost", 0)),
                "notes": judgment.get("notes", "DeepSeek approved cluster consensus")
            }

        except Exception as e:
            logger.exception(f"Internal brain judge failed: {e}")
            return self._internal_judge(cluster_results, {
                "notes": f"DeepSeek unavailable: {e}",
                "approved": False,
                "confidence_boost": 0
            })

    def _internal_judge(self, cluster_results: Dict, basis: Dict = None) -> Dict:
        basis = basis or {}
        directions = [cluster_results['power']['direction'], cluster_results['geometric']['direction'], cluster_results['momentum']['direction']]
        confidences = [cluster_results['power']['confidence'], cluster_results['geometric']['confidence'], cluster_results['momentum']['confidence']]
        valid_votes = [d for d in directions if d in ('شراء', 'بيع')]
        unique_votes = set(valid_votes)
        average_confidence = sum(confidences) / max(len(confidences), 1)

        # Give priority to power cluster when it is clearly stronger
        power_dir = cluster_results['power']['direction']
        power_conf = cluster_results['power']['confidence']
        other_conf = max(cluster_results['geometric']['confidence'], cluster_results['momentum']['confidence'])
        if power_dir in ('شراء', 'بيع') and power_conf > other_conf + 10:
            return {
                'approved': True,
                'lean': True,
                'preferred_cluster': 'power',
                'confidence_boost': min(12, int((power_conf - other_conf) * 0.2)),
                'notes': f'Internal judge leans toward power cluster ({power_dir}) with priority.'
            }

        if len(unique_votes) == 1 and valid_votes:
            return {
                'approved': True,
                'confidence_boost': min(15, int(average_confidence * 0.2)),
                'notes': f'Internal judge: all clusters تدعم {valid_votes[0]} بمتوسط ثقة {int(average_confidence)}%'.strip()
            }

        if len(unique_votes) == 2:
            buy_score = sum(confidences[i] for i, d in enumerate(directions) if d == 'شراء')
            sell_score = sum(confidences[i] for i, d in enumerate(directions) if d == 'بيع')
            if abs(buy_score - sell_score) < 15:
                return {
                    'approved': False,
                    'veto': True,
                    'veto_reason': 'تناقض قوي بين عنقود القوة والزخم/الهندسة.',
                    'confidence_boost': 0,
                    'notes': 'Internal judge detected inconsistent cluster consensus.'
                }
            dominant = 'شراء' if buy_score > sell_score else 'بيع'
            boost = min(10, int(abs(buy_score - sell_score) * 0.1))
            return {
                'approved': True,
                'confidence_boost': boost,
                'notes': f'Internal judge يميل نحو {dominant} بسبب دعم أكبر من الكتل.'
            }

        return {
            'approved': False,
            'veto': True,
            'veto_reason': 'النتائج غير متسقة للغاية ولا يمكن اتخاذ قرار موثوق.',
            'confidence_boost': 0,
            'notes': 'Internal judge رفض القرار؛ توصية لتأجيل أو إعادة التقييم.'
        }

class DecisionMatrix:
    """طبقة 4: مصفوفة القرار"""

    def calculate_final_score(self, cluster_results: Dict, judge_result: Dict) -> Dict:
        """حساب النتيجة النهائية"""

        power_weight = 0.4
        geometric_weight = 0.3
        momentum_weight = 0.3

        # حساب النتيجة المرجحة
        # normalize scores to -1..1 range before weighting
        power_score = (self._direction_to_score(cluster_results['power']['direction']) * cluster_results['power']['confidence'] / 100.0) / 100.0
        geometric_score = (self._direction_to_score(cluster_results['geometric']['direction']) * cluster_results['geometric']['confidence'] / 100.0) / 100.0
        momentum_score = (self._direction_to_score(cluster_results['momentum']['direction']) * cluster_results['momentum']['confidence'] / 100.0) / 100.0

        final_score = (power_score * power_weight) + (geometric_score * geometric_weight) + (momentum_score * momentum_weight)

        # تطبيق boost من القاضي
        confidence_boost = judge_result.get("confidence_boost", 0)
        final_score += confidence_boost / 100.0

        # تحديد التوصية النهائية باستخدام thresholds الجديدة 0.35/0.15
        if final_score > 0.35:
            recommendation = "شراء"
            strength = "قوي"
        elif final_score > 0.15:
            recommendation = "شراء"
            strength = "حذر"
        elif final_score > -0.15:
            recommendation = "انتظار"
            strength = "محايد"
        elif final_score > -0.35:
            recommendation = "بيع"
            strength = "حذر"
        else:
            recommendation = "بيع"
            strength = "قوي"

        # حساب الثقة النهائية مع حد أدنى 40% وحد أقصى 95%
        confidence = int(min(95, max(40, abs(final_score) * 100)))

        return {
            "recommendation": recommendation,
            "strength": strength,
            "confidence": int(confidence),
            "final_score": round(final_score, 2),
            "cluster_scores": {
                "power": round(power_score, 2),
                "geometric": round(geometric_score, 2),
                "momentum": round(momentum_score, 2)
            },
            "judge_approved": judge_result.get("approved", True),
            "judge_notes": judge_result.get("notes", "")
        }

    def _direction_to_score(self, direction: str) -> float:
        """تحويل الاتجاه إلى نقاط"""
        if direction == "شراء":
            return 100
        elif direction == "بيع":
            return -100
        else:
            return 0

class VotingEngine:
    """المحرك الرئيسي للتصويت المتقدم"""

    def __init__(self):
        self.environment_filter = EnvironmentFilter()
        self.cluster_voting = ClusterVoting()
        self.brain_judge = InternalBrainJudge()
        self.decision_matrix = DecisionMatrix()
        self.internal_brain = InternalBrain()
        self.calendar_service = CalendarService()
        self.data_adapter = DataAdapter()

    def analyze(self, visual_context: List[Dict], market: str = "XAUUSD", user_id: Optional[int] = None) -> Dict:
        """التحليل الكامل بالنظام الجديد مع الذكاء الاصطناعي"""

        # الحصول على تفضيلات المستخدم
        trading_mode = "day"  # default
        if user_id:
            from database import SessionLocal
            db = SessionLocal()
            try:
                user_prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == user_id).first()
                if user_prefs:
                    trading_mode = user_prefs.trading_mode
            finally:
                db.close()

        env_check = self.environment_filter.check_environment(market)
        # handle suspend immediately; proceed_warn allows continuing but with issues flagged
        if env_check.get('recommendation') == 'suspend':
            return {
                "recommendation": "تعليق",
                "confidence": 0,
                "reason": "البيئة السوقية غير مناسبة",
                "issues": env_check.get('issues', []),
                "environment_filter": env_check,
                "market": market,
                "timestamp": datetime.utcnow().isoformat()
            }

        unified_data = self.data_adapter.normalize_input(visual_context, market)
        if not unified_data["valid"]:
            return {
                "recommendation": "بيانات غير كافية",
                "confidence": 0,
                "reason": "لم يتمكن النظام من توحيد بيانات السوق بشكل كافٍ.",
                "issues": unified_data.get("issues", []),
                "data_quality": unified_data.get("quality_score", 0),
                "market": market,
                "timestamp": datetime.now().isoformat()
            }

        strategy_weights = self.internal_brain.get_strategy_weights(user_id=user_id)
        cluster_results = self.cluster_voting.vote_clusters(unified_data["chart_data"], market, strategy_weights)

        judge_result = self.brain_judge.judge(cluster_results, market)
        final_decision = self.decision_matrix.calculate_final_score(cluster_results, judge_result)

        # استخدام الذكاء الاصطناعي للتحليل النهائي
        ai_analysis = ai_core_service.analyze(
            chart_data=unified_data["chart_data"],
            cluster_results=cluster_results,
            judge_result=judge_result,
            market=market,
            user_id=user_id,
            strategy_weights=strategy_weights
        )

        # فحص الشروط للتوصية عالية الدقة
        confidence = ai_analysis["confidence"]
        if confidence < 60:
            return {
                "recommendation": "لا توجد فرصة واضحة حالياً",
                "confidence": confidence,
                "reason": "الثقة أقل من 60%",
                "market": market,
                "timestamp": datetime.utcnow().isoformat()
            }

        # عد الاستراتيجيات المتفقة كنسبة مئوية بدلاً من حد ثابت
        agreeing_count = 0
        total_count = 0
        for cluster in cluster_results.values():
            if isinstance(cluster, dict):
                for d in cluster.get('details', []):
                    total_count += 1
                    if d.get('vote') == ai_analysis.get('recommendation'):
                        agreeing_count += 1

        if total_count == 0:
            return {
                "recommendation": "لا توجد فرصة واضحة حالياً",
                "confidence": confidence,
                "reason": "لا توجد استراتيجيات صالحة للتقييم",
                "market": market,
                "timestamp": datetime.utcnow().isoformat()
            }

        agreeing_ratio = agreeing_count / total_count
        # نطلب على الأقل 60% من الاستراتيجيات أن توافق
        if agreeing_ratio < 0.6:
            return {
                "recommendation": "لا توجد فرصة واضحة حالياً",
                "confidence": confidence,
                "reason": f"نسبة الاتفاق منخفضة: {agreeing_ratio:.2f}",
                "market": market,
                "timestamp": datetime.utcnow().isoformat()
            }

        # فحص الأخبار عالية التأثير
        upcoming_events = self.calendar_service.get_upcoming_events(hours=4)
        high_impact_events = [e for e in upcoming_events if e.get('impact') == 'high']
        if high_impact_events:
            next_event = min(high_impact_events, key=lambda x: x.get('time_until', timedelta(hours=24)))
            time_until = next_event.get('time_until', timedelta(hours=24))
            if time_until < timedelta(hours=1):
                return {
                    "recommendation": "لا توجد فرصة واضحة حالياً",
                    "confidence": confidence,
                    "reason": "أخبار عالية التأثير قريبة",
                    "market": market,
                    "timestamp": datetime.now().isoformat()
                }

        result = {
            "recommendation": ai_analysis["recommendation"],
            "strength": ai_analysis.get("strength", final_decision["strength"]),
            "confidence": ai_analysis["confidence"],
            "final_score": ai_analysis.get("final_score", final_decision["final_score"]),
            "reason": ai_analysis["reason"],
            "explanation": ai_analysis.get("explanation", ""),
            "cluster_breakdown": {
                "power": cluster_results["power"],
                "geometric": cluster_results["geometric"],
                "momentum": cluster_results["momentum"]
            },
            "judge_result": judge_result,
            "ai_analysis": ai_analysis,
            "environment_status": "stable",
            "data_quality": unified_data.get("quality_score", 0),
            "issues": unified_data.get("issues", []),
            "market": market,
            "timestamp": datetime.now().isoformat()
        }

        if cluster_results["geometric"].get("targets"):
            result["targets"] = cluster_results["geometric"]["targets"]
        if cluster_results["geometric"].get("stops"):
            result["stop_loss"] = cluster_results["geometric"]["stops"][0]
        if cluster_results["momentum"].get("timing"):
            result["timing_signals"] = cluster_results["momentum"]["timing"]

        # تخصيص حسب وضع التداول
        result["trading_mode"] = trading_mode
        if trading_mode == "scalping":
            result["timeframes"] = ["1m", "5m"]
            result["target_type"] = "small"
            result["stop_type"] = "tight"
        elif trading_mode == "day":
            result["timeframes"] = ["15m", "1H"]
            result["target_type"] = "medium"
            result["stop_type"] = "medium"
        elif trading_mode == "swing":
            result["timeframes"] = ["4H", "Daily"]
            result["target_type"] = "wide"
            result["stop_type"] = "wide"

        return result

voting_engine = VotingEngine()
