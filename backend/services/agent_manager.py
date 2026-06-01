import os
import time
import logging
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from .risk_manager_agent import RiskManagerAgent
from .performance_analyst import PerformanceAnalyst
from .mistake_learner import MistakeLearner
from .news_calendar_agent import NewsCalendarAgent
from .psychology_agent import PsychologyAgent
from .sync_backup_agent import SyncBackupAgent
from .hidden_opportunity import HiddenOpportunity
from .smart_zones import SmartZones
from .timing_agent import TimingAgent
from .trade_followup import TradeFollowup
from .library_agent import LibraryAgent
from .challenge_agent import ChallengeAgent
from .correlation_agent import CorrelationAgent
from .liquidity_flow import LiquidityFlow
from .complex_pattern import ComplexPattern
from .radar_agent import RadarAgent
from .golden_trade import GoldenTrade
from .recycle_agent import RecycleAgent
from .brainstorm_agent import BrainstormAgent
from .advanced_protection import AdvancedProtection
from .research_agent import ResearchAgent

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.ai/v1/analyze")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL")


class AgentError(Exception):
    pass


class AgentBase:
    def __init__(self, name: str, role_prompt: str):
        self.name = name
        self.role_prompt = role_prompt

    def build_prompt(self, data: Dict[str, Any]) -> str:
        data_snippet = self._summarize_data(data)
        prompt = (
            f"You are {self.name}. Role: {self.role_prompt}.\n"
            f"Given the unified market data below, provide:\n"
            f"- signal: one of [buy, sell, neutral]\n"
            f"- confidence: number 0-100\n"
            f"- short textual report explaining your decision\n\n"
            f"Data:\n{data_snippet}\n\nRespond in JSON or plain text containing Signal, Confidence, Report."
        )
        return prompt

    def _summarize_data(self, data: Dict[str, Any]) -> str:
        try:
            # Keep a short summary to avoid huge prompts
            keys = list(data.keys())[:10]
            summary_lines = []
            for k in keys:
                v = data.get(k)
                summary_lines.append(f"{k}: {repr(v)[:300]}")
            return "\n".join(summary_lines)
        except Exception:
            return str(data)

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self.build_prompt(data)
        try:
            return self._call_deepseek(prompt)
        except Exception as e:
            logger.exception("Agent %s external model failed, trying fallbacks", self.name)
            try:
                return self._fallback(prompt)
            except Exception:
                logger.exception("Agent %s fallback also failed", self.name)
                # When all remote APIs and fallbacks fail, never produce a random decision.
                # Return a neutral, zero-confidence result with a clear message in Arabic.
                return {"agent": self.name, "signal": "neutral", "confidence": 0, "report": "التحليل غير متاح حالياً"}

# Optional footprint/bookmap analyzers (best-effort import)
try:
    from .footprint_service import FootprintChartAnalyzer, BookmapDOMReader  # type: ignore
except Exception:
    FootprintChartAnalyzer = None
    BookmapDOMReader = None

    def _call_deepseek(self, prompt: str) -> Dict[str, Any]:
        if not DEEPSEEK_API_KEY:
            raise AgentError("External model API key not configured")
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "max_tokens": 400}
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise AgentError(f"External model API error {resp.status_code}: {resp.text}")
        try:
            data = resp.json()
        except Exception:
            text = resp.text
            return self._parse_freeform_response(text)

        # Expect structured response
        for key in ("signal", "Signal"):
            if key in data:
                signal = data.get(key)
                confidence = data.get("confidence") or data.get("Confidence") or data.get("score") or 50
                report = data.get("report") or data.get("Report") or data.get("explanation") or str(data)
                return {"agent": self.name, "signal": str(signal).lower(), "confidence": int(float(confidence)), "report": str(report)}

        # Try to extract from text fields in the response
        if isinstance(data, dict):
            text = data.get("text") or data.get("choices") and str(data.get("choices")) or str(data)
            return self._parse_freeform_response(text)

        return self._heuristic_response()

    def _parse_freeform_response(self, text: str) -> Dict[str, Any]:
        # Simple parsing heuristics
        lower = text.lower()
        if "buy" in lower and "sell" not in lower:
            signal = "buy"
        elif "sell" in lower and "buy" not in lower:
            signal = "sell"
        else:
            signal = "neutral"
        # try find a number for confidence
        import re

        m = re.search(r"(confidence|score)[^0-9]*(\d{1,3})", lower)
        if m:
            conf = int(m.group(2))
        else:
            # Do not invent confidence — default to 0 when not provided.
            conf = 0
        report = text.strip()[:1000]
        return {"agent": self.name, "signal": signal, "confidence": conf, "report": report}

    def _fallback(self, prompt: str) -> Dict[str, Any]:
        # Try OpenRouter
        if OPENROUTER_API_KEY:
            try:
                url = os.getenv("OPENROUTER_URL", "https://api.openrouter.ai/v1/chat/completions")
                headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
                payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "max_tokens": 400}
                r = requests.post(url, json=payload, headers=headers, timeout=15)
                if r.status_code == 200:
                    return self._parse_freeform_response(r.text)
            except Exception:
                logger.exception("OpenRouter fallback failed for %s", self.name)

        # Try Gemini (if key present) - best-effort
        if GEMINI_API_KEY:
            try:
                gem_url = os.getenv("GEMINI_URL", "https://gemini.api.fake/v1/respond")
                headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
                payload = {"prompt": prompt, "max_output_tokens": 400}
                r = requests.post(gem_url, json=payload, headers=headers, timeout=15)
                if r.status_code == 200:
                    return self._parse_freeform_response(r.text)
            except Exception:
                logger.exception("Gemini fallback failed for %s", self.name)

        raise AgentError("No fallback available or all fallbacks failed")

    # NOTE: Removed heuristic/random fallback to ensure no random trading signals are produced.


class LiquidityAgent(AgentBase):
    """Agent specialized in measuring order book depth, spread, and instantaneous
    volume vs average. Uses an external reasoning service with local heuristics
    as fallback.
    """
    def __init__(self):
        super().__init__("Liquidity Agent", "assess market liquidity, spread and slippage risk")

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Extract best-effort features from provided unified_data
        try:
            order_book = data.get("order_book") or {}
            bids = order_book.get("bids", []) if isinstance(order_book, dict) else []
            asks = order_book.get("asks", []) if isinstance(order_book, dict) else []
        except Exception:
            bids, asks = [], []

        def depth_at_levels(entries, levels=5):
            try:
                return sum(float(e[1]) for e in entries[:levels]) if entries else 0.0
            except Exception:
                return 0.0

        bid_depth = depth_at_levels(bids, levels=5)
        ask_depth = depth_at_levels(asks, levels=5)
        total_depth = bid_depth + ask_depth

        # spread
        try:
            best_bid = float(bids[0][0]) if bids else None
            best_ask = float(asks[0][0]) if asks else None
            spread = (best_ask - best_bid) if best_bid is not None and best_ask is not None else None
        except Exception:
            spread = None

        spread_history = data.get("spread_history") or []
        recent_trades = data.get("recent_trades") or []
        try:
            recent_volume = sum(float(t.get("size", t[1] if isinstance(t, (list, tuple)) and len(t) > 1 else 0)) for t in recent_trades)
        except Exception:
            recent_volume = 0.0

        avg_volume = data.get("avg_volume") or (sum(data.get("volume", [])) / max(1, len(data.get("volume", [])))) if data.get("volume") else None
        volume_ratio = None
        if avg_volume and avg_volume > 0:
            volume_ratio = recent_volume / float(avg_volume)

        # basic low-liquidity/time checks
        is_weekend = False
        try:
            ts = data.get("timestamp")
            if ts:
                import datetime as _dt
                dt = _dt.datetime.utcfromtimestamp(int(ts)) if isinstance(ts, (int, float)) else _dt.datetime.utcnow()
                is_weekend = dt.weekday() >= 5
        except Exception:
            is_weekend = False

        upcoming_news = data.get("upcoming_news") or []
        news_soon = False
        try:
            # upcoming_news can be a list of dicts with 'minutes_to' key
            for n in upcoming_news:
                m = n.get("minutes_to") if isinstance(n, dict) else None
                if m is not None and int(m) <= 30:
                    news_soon = True
                    break
        except Exception:
            news_soon = False

        # Fallback heuristics thresholds
        low_depth_threshold = float(os.getenv("LIQUIDITY_LOW_DEPTH", "50"))
        high_spread_threshold = float(os.getenv("LIQUIDITY_HIGH_SPREAD", "0.005"))
        low_volume_ratio_threshold = float(os.getenv("LIQUIDITY_LOW_VOLUME_RATIO", "0.6"))

        low_depth = (total_depth is not None and total_depth < low_depth_threshold)
        high_spread = (spread is not None and best_bid and best_ask and (spread / max(1.0, best_bid)) > high_spread_threshold)
        low_volume = (volume_ratio is not None and volume_ratio < low_volume_ratio_threshold)

        slippage_risk = low_depth or high_spread or low_volume or news_soon or is_weekend

        # Build prompt for external reasoning service with features
        features = {
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "total_depth": total_depth,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "spread_history": spread_history[-10:],
            "recent_volume": recent_volume,
            "avg_volume": avg_volume,
            "volume_ratio": volume_ratio,
            "slippage_risk": slippage_risk,
            "news_soon": news_soon,
            "is_weekend": is_weekend,
        }

        prompt = (
            f"You are Liquidity Agent. Given the following liquidity features, decide whether market is safe for execution."
            f"Provide signal [buy/sell/neutral], confidence 0-100 and a short report.\\nFeatures:\\n{json.dumps(features, default=str)}"
        )

        # Try DeepSeek first (AgentBase has helper)
        try:
            raw = self._call_deepseek(prompt)
            # Ensure keys normalized
            signal = raw.get("signal") or raw.get("Signal") or str(raw.get("agent_signal") or "neutral")
            conf = int(raw.get("confidence") or raw.get("Confidence") or raw.get("score") or 0)
            report = raw.get("report") or raw.get("Report") or raw.get("explanation") or str(raw)
            signal = str(signal).lower()
        except Exception:
            logger.exception("LiquidityAgent external model failed, using local heuristics")
            # Local heuristic
            if slippage_risk:
                signal = "neutral"
                conf = 20
                report = "Low liquidity or high spread detected; avoid new positions."
            else:
                # if volume high and spread small favor trend in data
                if volume_ratio and volume_ratio > 1.2 and spread is not None and spread / max(1.0, best_bid or 1) < high_spread_threshold:
                    signal = "buy"
                    conf = 70
                    report = "Sufficient liquidity and volume — execution risk acceptable."
                else:
                    signal = "neutral"
                    conf = 50
                    report = "Liquidity appears average; proceed with caution."

        # If low liquidity, reduce confidence or set neutral
        if slippage_risk:
            conf = max(0, min(100, int(conf * 0.4)))
            if conf < 30:
                signal = "neutral"
                report = f"Liquidity concern lowered confidence to {conf}. {report}"

        # Compose final report with additional notes
        notes = f"LiquidityAgent summary: depth={total_depth}, spread={spread}, recent_vol={recent_volume}, vol_ratio={volume_ratio}, slippage_risk={slippage_risk}. {report}"

        return {"agent": self.name, "signal": signal, "confidence": int(conf), "report": notes}


class TemporalAuditAgent(AgentBase):
    """Agent that audits signals across multiple timeframes, reducing
    false positives from noisy short timeframes and ensuring alignment.
    """
    def __init__(self):
        super().__init__("Temporal Audit Agent", "ensure multi-timeframe signal alignment and reduce timeframe noise")

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Expect data to include 'timeframe_signals': { '1m': {'signal':'buy','confidence':...}, ... }
        tfs = data.get("timeframe_signals") or {}
        if not isinstance(tfs, dict) or len(tfs) == 0:
            # Nothing to audit; attempt DeepSeek or fallback neutral
            try:
                return self._call_deepseek(self.build_prompt(data))
            except Exception:
                return {"agent": self.name, "signal": "neutral", "confidence": 20, "report": "No timeframe signals provided."}

        # Normalize signals and confidences
        counts = {"buy": 0, "sell": 0, "neutral": 0}
        total_conf = {"buy": 0.0, "sell": 0.0, "neutral": 0.0}
        tf_entries = []
        for tf, info in tfs.items():
            sig = None
            conf = 0
            if isinstance(info, dict):
                sig = str(info.get("signal") or info.get("Signal") or "neutral").lower()
                try:
                    conf = float(info.get("confidence") or info.get("Confidence") or info.get("conf") or 0)
                except Exception:
                    conf = 0
            else:
                # maybe simple tuple/list
                try:
                    sig = str(info[0]).lower()
                    conf = float(info[1])
                except Exception:
                    sig = "neutral"
                    conf = 0
            if sig not in counts:
                sig = "neutral"
            counts[sig] += 1
            total_conf[sig] += conf
            tf_entries.append((tf, sig, conf))

        # Determine agreement: require at least 3 timeframes agreeing
        agree_signal = max(counts.items(), key=lambda x: x[1])[0]
        agree_count = counts[agree_signal]

        # Check major conflict: 4h vs 15m
        sig_4h = None
        sig_15m = None
        for tf, sig, conf in tf_entries:
            if str(tf).lower().startswith("4h") or tf == "4h":
                sig_4h = sig
            if str(tf).lower().endswith("15m") or tf == "15m":
                sig_15m = sig

        conflict_4h_15m = (sig_4h and sig_15m and sig_4h != sig_15m and sig_4h != "neutral" and sig_15m != "neutral")

        # Base confidence from average of agreeing signals
        base_conf = 0
        if agree_count > 0:
            base_conf = int(total_conf[agree_signal] / max(1, agree_count))
        else:
            base_conf = 30

        # Weight scaling: more agreeing frames => higher weight
        weight_multiplier = 1.0 + max(0, (agree_count - 3)) * 0.1
        conf = int(max(0, min(100, base_conf * weight_multiplier)))

        report_lines = [f"Temporal audit across {len(tf_entries)} frames; agreement: {agree_signal} ({agree_count} frames)"]
        for tf, sig, c in sorted(tf_entries):
            report_lines.append(f"{tf}: {sig} ({c})")

        if conflict_4h_15m:
            conf = int(conf * 0.5)
            report_lines.append("Conflict between 4h and 15m detected — reducing confidence.")

        # Reduce false positives from small frames: if agreement mostly from <1h frames but 4h neutral, be cautious
        long_frame_support = any(str(tf).lower().startswith("4h") or str(tf).lower().startswith("1d") or str(tf).lower().startswith("daily") for tf, _, _ in tf_entries)
        small_frame_majority = agree_count >= 3 and all((not str(tf).lower().startswith("4h") and not str(tf).lower().startswith("1d") for tf, _, _ in tf_entries if _ == agree_signal))
        if small_frame_majority and not long_frame_support:
            conf = int(conf * 0.6)
            report_lines.append("Agreement mostly on small timeframes without long-term support — lowering confidence.")

        # If agreement less than 3, force neutral or low confidence
        signal = agree_signal
        if agree_count < 3:
            # attempt DeepSeek if available to reason across frames
            try:
                raw = self._call_deepseek(self.build_prompt({"timeframe_entries": tf_entries}))
                signal = raw.get("signal") or signal
                conf = int(raw.get("confidence") or conf)
                report_lines.append("External model refined decision used.")
            except Exception:
                report_lines.append("Insufficient agreement across timeframes; recommendation weakened.")
                if agree_count == 0:
                    signal = "neutral"
                    conf = max(10, conf // 2)

        # Compose final report
        report = "; ".join(report_lines)
        # Enforce bounds
        conf = max(0, min(100, int(conf)))
        if conflict_4h_15m and conf < 30:
            signal = "neutral"

        return {"agent": self.name, "signal": signal, "confidence": conf, "report": report}


class ManipulationDetector(AgentBase):
    """Detect common market manipulation patterns: spoofing, layering, iceberg orders, stop-hunting.
    Uses DeepSeek with fallbacks; when manipulation detected it reduces confidence or cancels recommendation.
    Returns: signal, confidence, report, manipulation_detected
    """
    def __init__(self):
        super().__init__("Market Manipulation Detector", "detect spoofing, layering, iceberg orders and stop-hunting from orderbook and trade events")

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Extract data sources (order_events is optional stream of add/remove orders)
        order_book = data.get("order_book") or {}
        bids = order_book.get("bids", []) if isinstance(order_book, dict) else []
        asks = order_book.get("asks", []) if isinstance(order_book, dict) else []
        order_events = data.get("order_events") or []  # list of {action:add/remove, side, price, size, ts}
        recent_trades = data.get("recent_trades") or []
        price_moves = data.get("price_moves") or []  # list of price snapshots or deltas

        manipulation = False
        reasons = []

        # Heuristic: Spoofing => quick add of large order then removal
        try:
            spoof_events = 0
            for ev in order_events:
                action = str(ev.get("action") or "").lower()
                size = float(ev.get("size") or ev.get("quantity") or 0)
                if action == "add" and size > 0:
                    # lookahead for quick remove of large order
                    for ev2 in order_events:
                        if ev2 is ev:
                            continue
                        if str(ev2.get("action") or "").lower() == "remove" and abs(float(ev2.get("price",0)) - float(ev.get("price",0))) < 1e-8 and float(ev2.get("size") or 0) >= size and abs((ev2.get("ts") or 0) - (ev.get("ts") or 0)) < 120:
                            spoof_events += 1
                            break
            if spoof_events >= 1:
                manipulation = True
                reasons.append(f"spoofing_candidates={spoof_events}")
        except Exception:
            pass

        # Heuristic: Layering => many small orders on same side at staggered prices
        try:
            def count_layers(entries):
                prices = [float(e[0]) for e in entries[:20]]
                # detect sequence of increasing/decreasing prices
                diffs = [prices[i+1]-prices[i] for i in range(len(prices)-1)]
                ups = sum(1 for d in diffs if d>0)
                downs = sum(1 for d in diffs if d<0)
                return ups, downs
            bid_ups, bid_downs = count_layers(bids) if bids else (0,0)
            ask_ups, ask_downs = count_layers(asks) if asks else (0,0)
            if (bid_ups >= 4 and sum(float(e[1]) for e in bids[:5]) < 100) or (ask_downs >=4 and sum(float(e[1]) for e in asks[:5]) < 100):
                manipulation = True
                reasons.append("layering_pattern")
        except Exception:
            pass

        # Heuristic: Iceberg detection => average trade size much larger than visible top levels
        try:
            avg_trade = 0.0
            if recent_trades:
                avg_trade = sum(float(t.get("size") or (t[1] if isinstance(t,(list,tuple)) and len(t)>1 else 0)) for t in recent_trades) / max(1, len(recent_trades))
            visible_depth = (sum(float(e[1]) for e in bids[:3]) + sum(float(e[1]) for e in asks[:3])) / 6.0 if (bids or asks) else 0.0
            if visible_depth>0 and avg_trade > visible_depth * 3.0:
                manipulation = True
                reasons.append("iceberg_suspected")
        except Exception:
            pass

        # Heuristic: Stop-hunting => price_moves include fast spikes reaching many small stops
        try:
            rapid_moves = 0
            for m in price_moves:
                # m may be dict {'delta':..., 'duration':...} or numeric
                if isinstance(m, dict):
                    delta = abs(float(m.get('delta') or 0))
                    dur = float(m.get('duration') or 0)
                    if dur < 120 and delta > 0.01:  # >1% in under 2 minutes
                        rapid_moves += 1
                else:
                    # fallback: numeric deltas
                    try:
                        if abs(float(m)) > 0.02:
                            rapid_moves += 1
                    except Exception:
                        pass
            if rapid_moves >= 1:
                manipulation = True
                reasons.append(f"rapid_moves={rapid_moves}")
        except Exception:
            pass

        # Build prompt for external reasoning service
        features = {
            "spoof_candidates": len([e for e in order_events if str(e.get('action') or '').lower() == 'add' and float(e.get('size') or 0) > 0]),
            "top_bid_depth": sum(float(e[1]) for e in bids[:5]) if bids else 0.0,
            "top_ask_depth": sum(float(e[1]) for e in asks[:5]) if asks else 0.0,
            "avg_trade_size": avg_trade,
            "recent_trade_count": len(recent_trades),
            "price_move_events": len(price_moves),
            "heuristic_flags": reasons,
        }

        prompt = (
            f"You are Market Manipulation Detector. Given the following market features, determine whether manipulation is present (spoofing, layering, iceberg, stop-hunting). Return signal [buy/sell/neutral], confidence 0-100, report and manipulation_detected boolean.\\nFeatures:\n{json.dumps(features, default=str)}"
        )

        try:
            raw = self._call_deepseek(prompt)
            signal = raw.get('signal') or raw.get('Signal') or 'neutral'
            conf = int(raw.get('confidence') or raw.get('Confidence') or raw.get('score') or 50)
            report = raw.get('report') or raw.get('Report') or str(raw)
            manipulation_flag = bool(raw.get('manipulation_detected') or raw.get('manipulation') or False)
        except Exception:
            logger.exception("ManipulationDetector external model failed, using heuristics")
            # Default heuristic decision: neutral unless manipulation true
            signal = 'neutral'
            conf = 60
            report = 'Heuristic analysis: ' + (', '.join(reasons) if reasons else 'no clear manipulation detected')
            manipulation_flag = manipulation

        # If manipulation detected by heuristics or remote, reduce confidence or cancel recommendation
        if manipulation_flag or manipulation:
            # reduce confidence by 30% relative
            conf = max(0, int(conf * 0.7))
            report = (report if report else '') + f"; Manipulation detected: {manipulation_flag or manipulation}. Reasons: {reasons}"
            # if severe heuristics flags present, set neutral
            if manipulation:
                signal = 'neutral'

        return {"agent": self.name, "signal": signal, "confidence": conf, "report": report, "manipulation_detected": bool(manipulation_flag or manipulation)}


class FootprintAgent(AgentBase):
    def __init__(self):
        super().__init__("Footprint Agent", "analyze footprint trade imbalances and cumulative delta")
        self.analyzer = FootprintChartAnalyzer() if FootprintChartAnalyzer else None

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.analyzer:
            return {"agent": self.name, "signal": "neutral", "confidence": 0, "report": "Footprint analyzer unavailable"}
        trades = data.get("recent_trades") or data.get("trades") or []
        try:
            for t in trades:
                if isinstance(t, dict):
                    price = t.get("price") or t.get("p") or t.get("price")
                    qty = t.get("qty") or t.get("q") or t.get("size") or t.get("quantity")
                    side = t.get("side") or ("buy" if t.get("isBuyerMaker") is False else "sell" if "isBuyerMaker" in t else None)
                elif isinstance(t, (list, tuple)):
                    price = t[0] if len(t) > 0 else None
                    qty = t[1] if len(t) > 1 else None
                    side = t[2] if len(t) > 2 else None
                else:
                    continue
                if price is None or qty is None:
                    continue
                try:
                    self.analyzer.ingest_trade(float(price), float(qty), side)
                except Exception:
                    continue
            res = self.analyzer.analyze()
            return {"agent": self.name, "signal": res.get("signal", "neutral"), "confidence": res.get("confidence", 0), "report": res.get("description", "")}
        except Exception as e:
            logger.exception("FootprintAgent error: %s", e)
            return {"agent": self.name, "signal": "neutral", "confidence": 0, "report": "error running footprint agent"}


class BookmapAgent(AgentBase):
    def __init__(self):
        super().__init__("Bookmap Agent", "analyze DOM / orderbook for walls, hidden liquidity and stop-hunts")
        self.reader = BookmapDOMReader() if BookmapDOMReader else None

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.reader:
            return {"agent": self.name, "signal": "neutral", "confidence": 0, "report": "Bookmap analyzer unavailable"}
        order_book = data.get("order_book") or {}
        bids = order_book.get("bids", []) if isinstance(order_book, dict) else []
        asks = order_book.get("asks", []) if isinstance(order_book, dict) else []
        try:
            self.reader.ingest_snapshot(bids, asks)
            res = self.reader.analyze()
            return {"agent": self.name, "signal": res.get("signal", "neutral"), "confidence": res.get("confidence", 0), "report": res.get("description", "")}
        except Exception as e:
            logger.exception("BookmapAgent error: %s", e)
            return {"agent": self.name, "signal": "neutral", "confidence": 0, "report": "error running bookmap agent"}


AGENT_DEFINITIONS = [
    ("Trend Agent", "determine the overall market trend based on price/time series"),
    ("Structure Agent", "analyze highs and lows, support/resistance structure"),
    ("Volatility Agent", "measure recent volatility and implied volatility signals"),
    ("Correlation Agent", "analyze correlation between instruments and markets"),
    ("SR Agent", "identify key support and resistance levels") ,
    ("Volume Agent", "analyze traded volume patterns and spikes"),
    ("OrderFlow Agent", "assess order flow imbalance and large orders presence"),
    ("Footprint Agent", "analyze footprint trade imbalances and cumulative delta"),
    ("Bookmap Agent", "analyze DOM / orderbook for walls, hidden liquidity and stop-hunts"),
    ("Liquidity Agent", "assess market liquidity and spread behaviour"),
    ("Manipulation Detector", "detect market manipulation patterns like spoofing, layering, iceberg, stop-hunting"),
    ("Momentum Agent", "measure momentum indicators and velocity of price moves"),
    ("Divergence Agent", "detect divergences between price and indicators"),
    ("Strength Agent", "compute strength and sustainability of moves"),
    ("Candlestick Agent", "detect candlestick patterns and reversals"),
    ("Harmonic Agent", "identify harmonic patterns like AB=CD, Gartley"),
    ("Elliott Agent", "detect Elliott wave structures and counts"),
    ("Price Pattern Agent", "detect flags, pennants, triangles and channels"),
    ("Long-term Agent", "analyse long term timeframe (weekly/monthly) context"),
    ("Medium-term Agent", "analyse medium term timeframe (daily/4h) context"),
    ("Short-term Agent", "analyse short term timeframe (intraday/1h/15m) context"),
    ("Temporal Audit Agent", "verify multi-timeframe alignment and reduce false signals from timeframe noise"),
    ("News Agent", "assess impact of recent news and events on the market"),
    ("Sentiment Agent", "analyse social and market sentiment signals"),
    ("Adaptation Agent", "suggest weight adjustments to agents based on historical accuracy and market regime changes"),
]

BUILTIN_AGENT_CLASSES = [
    RiskManagerAgent,
    PerformanceAnalyst,
    MistakeLearner,
    NewsCalendarAgent,
    PsychologyAgent,
    SyncBackupAgent,
    HiddenOpportunity,
    SmartZones,
    TimingAgent,
    TradeFollowup,
    LibraryAgent,
    ChallengeAgent,
    CorrelationAgent,
    LiquidityFlow,
    ComplexPattern,
    RadarAgent,
    GoldenTrade,
    RecycleAgent,
    BrainstormAgent,
    AdvancedProtection,
    ResearchAgent,
    LiquidityAgent,
    ManipulationDetector,
    FootprintAgent,
    BookmapAgent,
    TemporalAuditAgent,
]


class AgentManager:
    def __init__(self, agents: List[AgentBase] = None):
        if agents is None:
            self.agents = [cls() for cls in BUILTIN_AGENT_CLASSES]
        else:
            self.agents = agents

    def run(self, unified_data: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
        results = {}
        futures = []
        with ThreadPoolExecutor(max_workers=min(8, len(self.agents))) as ex:
            for ag in self.agents:
                futures.append(ex.submit(self._safe_analyze, ag, unified_data))
            for fut in as_completed(futures, timeout=timeout):
                try:
                    res = fut.result()
                    results[res.get("agent")] = res
                except Exception as e:
                    logger.exception("Agent future failed: %s", e)

        aggregated = self._aggregate(results)
        aggregated["order_book"] = unified_data.get("order_book")
        aggregated["recent_trades"] = unified_data.get("recent_trades")
        aggregated["market"] = unified_data.get("market")
        aggregated["quality_score"] = unified_data.get("quality_score")
        orchestrator_result = None
        try:
            orchestrator_result = self._send_to_orchestrator(aggregated)
        except Exception:
            logger.exception("Failed to send to orchestrator")
        if orchestrator_result:
            aggregated["orchestrator"] = orchestrator_result
        return aggregated

    def _safe_analyze(self, agent: AgentBase, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return agent.analyze(data)
        except Exception:
            logger.exception("Agent %s crashed during analyze", agent.name)
            return {"agent": agent.name, "signal": "neutral", "confidence": 0, "report": "error in agent"}

    def _aggregate(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        reports = []
        signals = {}
        confidences = {}
        for name, res in results.items():
            reports.append({"agent": name, "report": res.get("report")})
            sig = res.get("signal", "neutral")
            conf = int(res.get("confidence", 0))
            signals[name] = sig
            confidences[name] = conf

        # Try loading InternalBrain for dynamic weights
        try:
            from .internal_brain import InternalBrain
            brain = InternalBrain()
        except ImportError:
            brain = None

        # ensemble: score buy as +1, sell -1, neutral 0 weighted by confidence AND dynamic weight
        score = 0.0
        for a, s in signals.items():
            w = confidences.get(a, 0) / 100.0
            
            dynamic_weight = 1.0
            if brain:
                dynamic_weight = brain.get_agent_dynamic_weight(a, default_weight=1.0)
                
            if s == "buy":
                score += (1.0 * w * dynamic_weight)
            elif s == "sell":
                score -= (1.0 * w * dynamic_weight)

        final_signal = "neutral"
        if score > 0.5:  # Slightly increased threshold due to dynamic weights
            final_signal = "buy"
        elif score < -0.5:
            final_signal = "sell"

        avg_conf = int((sum(confidences.values()) / max(1, len(confidences))))

        payload = {
            "agents": results,
            "reports": reports,
            "signals": signals,
            "confidences": confidences,
            "ensemble": {"signal": final_signal, "score": score, "avg_confidence": avg_conf},
            "timestamp": int(time.time()),
        }
        return payload

    def _send_to_orchestrator(self, payload: Dict[str, Any]):
        # Prefer remote orchestrator if configured
        if ORCHESTRATOR_URL:
            try:
                headers = {"Content-Type": "application/json"}
                r = requests.post(ORCHESTRATOR_URL, json=payload, headers=headers, timeout=10)
                if r.status_code >= 400:
                    raise AgentError(f"Orchestrator returned {r.status_code}: {r.text}")
                logger.info("Sent payload to orchestrator: %s", ORCHESTRATOR_URL)
                try:
                    return r.json()
                except Exception:
                    return None
            except Exception:
                logger.exception("Failed to send to orchestrator URL %s; will attempt local orchestrator fallback", ORCHESTRATOR_URL)

        # Fallback: if no ORCHESTRATOR_URL or remote failed, run local Orchestrator
        try:
            from .orchestrator import Orchestrator
            orch = Orchestrator()
            market_data = {
                "ensemble": payload.get("ensemble"),
                "signals": payload.get("signals"),
                "confidences": payload.get("confidences"),
                "timestamp": payload.get("timestamp"),
                "order_book": payload.get("order_book"),
                "recent_trades": payload.get("recent_trades"),
                "market": payload.get("market"),
                "quality_score": payload.get("quality_score")
            }
            # payload['agents'] is a dict of agent_name -> result; orchestrator expects list of reports
            agent_reports = []
            agents_obj = payload.get("agents")
            if isinstance(agents_obj, dict):
                agent_reports = list(agents_obj.values())
            else:
                agent_reports = payload.get("reports", [])

            orch_result = orch.orchestrate(market_data, agent_reports)
            logger.info("Local orchestrator executed; thesis: %s", orch_result.get("thesis"))
            return orch_result
        except Exception:
            logger.exception("Failed to execute local orchestrator fallback")
            return None


def example_usage():
    # simple example for local testing
    manager = AgentManager()
    sample_data = {"symbol": "BTCUSD", "prices": [60000, 60200, 60100], "volume": [100, 150, 120], "news": []}
    out = manager.run(sample_data)
    print(out)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
