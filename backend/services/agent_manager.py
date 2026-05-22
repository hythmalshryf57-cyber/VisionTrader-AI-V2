import os
import time
import logging
import random
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-046971017e5f4efbb60a6408a056e478")
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
            logger.exception("Agent %s DeepSeek failed, trying fallbacks", self.name)
            try:
                return self._fallback(prompt)
            except Exception:
                logger.exception("Agent %s fallback also failed", self.name)
                return self._heuristic_response()

    def _call_deepseek(self, prompt: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "max_tokens": 400}
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise AgentError(f"DeepSeek API error {resp.status_code}: {resp.text}")
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
            conf = random.randint(30, 70)
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

    def _heuristic_response(self) -> Dict[str, Any]:
        signal = random.choice(["buy", "sell", "neutral"])
        conf = random.randint(20, 60)
        report = f"Heuristic fallback by {self.name}: signal={signal}, confidence={conf}"
        return {"agent": self.name, "signal": signal, "confidence": conf, "report": report}


AGENT_DEFINITIONS = [
    ("Trend Agent", "determine the overall market trend based on price/time series"),
    ("Structure Agent", "analyze highs and lows, support/resistance structure"),
    ("Volatility Agent", "measure recent volatility and implied volatility signals"),
    ("Correlation Agent", "analyze correlation between instruments and markets"),
    ("SR Agent", "identify key support and resistance levels") ,
    ("Volume Agent", "analyze traded volume patterns and spikes"),
    ("OrderFlow Agent", "assess order flow imbalance and large orders presence"),
    ("Liquidity Agent", "assess market liquidity and spread behaviour"),
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
    ("News Agent", "assess impact of recent news and events on the market"),
    ("Sentiment Agent", "analyse social and market sentiment signals"),
    ("Adaptation Agent", "suggest weight adjustments to agents based on historical accuracy and market regime changes"),
]


class AgentManager:
    def __init__(self, agents: List[AgentBase] = None):
        if agents is None:
            self.agents = [AgentBase(name, prompt) for name, prompt in AGENT_DEFINITIONS]
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
        # send to orchestrator if configured
        try:
            self._send_to_orchestrator(aggregated)
        except Exception:
            logger.exception("Failed to send to orchestrator")

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

        # simple ensemble: score buy as +1, sell -1, neutral 0 weighted by confidence
        score = 0.0
        for a, s in signals.items():
            w = confidences.get(a, 0) / 100.0
            if s == "buy":
                score += 1.0 * w
            elif s == "sell":
                score -= 1.0 * w

        final_signal = "neutral"
        if score > 0.3:
            final_signal = "buy"
        elif score < -0.3:
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
        if not ORCHESTRATOR_URL:
            logger.info("Orchestrator URL not set; skipping send")
            return
        try:
            headers = {"Content-Type": "application/json"}
            r = requests.post(ORCHESTRATOR_URL, json=payload, headers=headers, timeout=10)
            if r.status_code >= 400:
                raise AgentError(f"Orchestrator returned {r.status_code}: {r.text}")
            logger.info("Sent payload to orchestrator: %s", ORCHESTRATOR_URL)
        except Exception:
            logger.exception("Failed to send to orchestrator")


def example_usage():
    # simple example for local testing
    manager = AgentManager()
    sample_data = {"symbol": "BTCUSD", "prices": [60000, 60200, 60100], "volume": [100, 150, 120], "news": []}
    out = manager.run(sample_data)
    print(out)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
