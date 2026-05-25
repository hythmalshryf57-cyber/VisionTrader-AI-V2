import os
import sys
import time
import logging
import random
import requests
from typing import Any, Dict, List, Optional

# Fix Arabic/Unicode output on Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-046971017e5f4efbb60a6408a056e478")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/analyze")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

CLUSTER_WEIGHTS_DEFAULT = {
    "Power": 40,
    "Geometric": 30,
    "Momentum": 30,
}


class OrchestratorError(Exception):
    pass


class MarketThesisGenerator:
    def __init__(self, api_key: str = DEEPSEEK_API_KEY, api_url: str = DEEPSEEK_API_URL):
        self.api_key = api_key
        self.api_url = api_url

    def generate(self, agent_reports: List[Dict[str, Any]], win_rate: float = 50.0) -> str:
        prompt = self._build_prompt(agent_reports, win_rate)
        try:
            return self._call_deepseek(prompt)
        except Exception:
            logger.exception("DeepSeek thesis generation failed")
            return self._fallback_thesis(agent_reports)

    def _build_prompt(self, reports: List[Dict[str, Any]], win_rate: float = 50.0) -> str:
        summary = []
        for report in reports[:21]:
            name = report.get("agent") or report.get("name") or "unknown"
            signal = report.get("signal", "neutral")
            confidence = report.get("confidence", 0)
            text = report.get("report", "")
            summary.append(f"- {name}: signal={signal}, confidence={confidence}, report={text}")

        # Injecting recent win rate context
        performance_context = f"The system's recent win rate is {win_rate}%. "
        if win_rate < 40.0:
            performance_context += "Performance is currently POOR. The market might be hostile. Adopt a highly defensive and conservative thesis."
        elif win_rate > 60.0:
            performance_context += "Performance is currently STRONG. The market is favorable. Adopt a confident and trend-following thesis."
        else:
            performance_context += "Performance is NEUTRAL. Stick to standard analysis."

        return (
            "You are a market thesis generator. Review the following 21 agent reports and determine the overall market condition.\n"
            f"{performance_context}\n"
            "Create a short market thesis in Arabic or English touching on trend, liquidity, risk regime, and recommended cluster bias.\n"
            "Example: 'السوق اليوم: اتجاه صاعد + سيولة منخفضة ← استراتيجيات Momentum أفضل'.\n\n"
            "Reviews:\n"
            + "\n".join(summary)
            + "\n\nRespond with a concise thesis statement."
        )

    def _call_deepseek(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "max_tokens": 200}
        response = requests.post(self.api_url, json=payload, headers=headers, timeout=15)
        if response.status_code != 200:
            raise OrchestratorError(f"DeepSeek error {response.status_code}: {response.text}")
        try:
            body = response.json()
            if isinstance(body, dict):
                if "text" in body:
                    return str(body["text"]).strip()
                if "output" in body:
                    return str(body["output"]).strip()
            return response.text.strip()
        except Exception:
            return response.text.strip()

    def _fallback_thesis(self, reports: List[Dict[str, Any]]) -> str:
        buy_count = sum(1 for r in reports if str(r.get("signal", "neutral")).lower() == "buy")
        sell_count = sum(1 for r in reports if str(r.get("signal", "neutral")).lower() == "sell")
        neutral_count = sum(1 for r in reports if str(r.get("signal", "neutral")).lower() == "neutral")
        if buy_count > sell_count + 3:
            return "السوق اليوم: اتجاه صاعد + سيولة معتدلة ← استراتيجيات Momentum أفضل"
        if sell_count > buy_count + 3:
            return "السوق اليوم: اتجاه هابط + تباين مرتفع ← استراتيجيات Risk-off أفضل"
        return "السوق اليوم: حالة محايدة + تقلب معتدل ← التكتيكات قصيرة المدى مناسبة"


class WeightCalculator:
    def __init__(self, base_weights: Optional[Dict[str, int]] = None):
        self.base_weights = base_weights or CLUSTER_WEIGHTS_DEFAULT.copy()

    def calculate(self, thesis: str) -> Dict[str, int]:
        weights = self.base_weights.copy()
        lower = thesis.lower()
        if "momentum" in lower or "اتجاه صاعد" in lower or "صعود" in lower:
            weights["Momentum"] = min(100, weights.get("Momentum", 30) + 30)
            weights["Power"] = max(0, weights.get("Power", 40) - 15)
            weights["Geometric"] = max(0, weights.get("Geometric", 30) - 15)
        if "risk-off" in lower or "هبوط" in lower or "تباين مرتفع" in lower:
            weights["Power"] = min(100, weights.get("Power", 40) + 10)
            weights["Geometric"] = max(0, weights.get("Geometric", 30) - 15)
            weights["Momentum"] = max(0, weights.get("Momentum", 30) - 5)
        if "محايدة" in lower or "جاهزية" in lower or "sideways" in lower:
            weights["Power"] = min(100, weights.get("Power", 40) + 5)
            weights["Geometric"] = max(0, weights.get("Geometric", 30) + 5)
            weights["Momentum"] = max(0, weights.get("Momentum", 30) - 10)

        total = sum(weights.values())
        if total == 0:
            return {k: 33 for k in weights}
        normalized = {k: max(0, int(round(v * 100.0 / total))) for k, v in weights.items()}
        diff = 100 - sum(normalized.values())
        if diff != 0:
            normalized["Momentum"] = max(0, normalized.get("Momentum", 0) + diff)
        return normalized


class AnalyzerAgent:
    def review(self, thesis: str, agent_reports: List[Dict[str, Any]], market_data: Dict[str, Any]) -> Dict[str, Any]:
        recommendation = self._infer_recommendation(thesis, agent_reports)
        comment = f"Analyzer reviewed thesis and recommends {recommendation}."
        return {"decision": recommendation, "comment": comment}

    def _infer_recommendation(self, thesis: str, agent_reports: List[Dict[str, Any]]) -> str:
        if any("sell" in str(r.get("signal", "")).lower() for r in agent_reports) and thesis.lower().find("buy") == -1:
            return "review-sell"
        return "confirm"


class RiskAgent:
    def decide(self, thesis: str, agent_reports: List[Dict[str, Any]], market_data: Dict[str, Any]) -> Dict[str, Any]:
        volatility = self._extract_volatility(market_data)
        size = 1.0
        risk_pct = 1.5
        comment = "Default risk allocation."
        if volatility and volatility > 2.0:
            size = 0.6
            risk_pct = 1.0
            comment = "High volatility detected; reducing risk size."
        elif volatility and volatility < 1.0:
            size = 1.2
            risk_pct = 2.0
            comment = "Low volatility detected; increasing size slightly."
        return {"position_size": round(size, 2), "risk_pct": round(risk_pct, 2), "comment": comment}

    def _extract_volatility(self, market_data: Dict[str, Any]) -> Optional[float]:
        value = market_data.get("volatility") or market_data.get("vol") or market_data.get("volatility_index")
        try:
            return float(value)
        except Exception:
            return None


class ExecutionAgent:
    def plan(self, thesis: str, recommendation: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        price = float(market_data.get("price") or market_data.get("last_price") or 0)
        if price <= 0:
            return {"entry": None, "stop": None, "targets": [], "comment": "Insufficient price data for execution."}

        if recommendation == "confirm":
            entry = price
            stop = round(price * 0.985, 2)
            targets = [round(price * 1.01, 2), round(price * 1.02, 2)]
        else:
            entry = price
            stop = round(price * 1.015, 2)
            targets = [round(price * 0.99, 2), round(price * 0.98, 2)]

        comment = "Generated entry, stop, and targets based on thesis and recommendation."
        return {"entry": entry, "stop": stop, "targets": targets, "comment": comment}


class DeliberationLoop:
    def __init__(self):
        self.analyzer = AnalyzerAgent()
        self.risk = RiskAgent()
        self.executor = ExecutionAgent()

    def run(self, thesis: str, weight_map: Dict[str, int], market_data: Dict[str, Any], agent_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        analysis = self.analyzer.review(thesis, agent_reports, market_data)
        risk_plan = self.risk.decide(thesis, agent_reports, market_data)
        execution = self.executor.plan(thesis, analysis.get("decision", "confirm"), market_data)
        return {
            "analysis": analysis,
            "risk": risk_plan,
            "execution": execution,
            "weights": weight_map,
        }


class Orchestrator:
    def __init__(self):
        self.thesis_generator = MarketThesisGenerator()
        self.weight_calculator = WeightCalculator()
        self.deliberation = DeliberationLoop()

    def orchestrate(self, market_data: Dict[str, Any], agent_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            from .internal_brain import InternalBrain
            brain = InternalBrain()
            win_rate = brain.get_dynamic_win_rate_floor()  # Fetching baseline
            # Get actual daily success rate
            summary = brain.get_daily_learning_summary()
            if summary.get("total_events", 0) > 0:
                win_rate = summary.get("success_rate", win_rate)
        except Exception:
            win_rate = 50.0

        thesis = self.thesis_generator.generate(agent_reports, win_rate)
        weights = self.weight_calculator.calculate(thesis)
        deliberation_result = self.deliberation.run(thesis, weights, market_data, agent_reports)
        final_signal = deliberation_result["analysis"]["decision"]
        return {
            "thesis": thesis,
            "weights": weights,
            "final_recommendation": final_signal,
            "targets": deliberation_result["execution"]["targets"],
            "stop": deliberation_result["execution"]["stop"],
            "entry": deliberation_result["execution"]["entry"],
            "market_data": market_data,
            "agent_reports": agent_reports,
            "deliberation": deliberation_result,
            "timestamp": int(time.time()),
        }


def example_usage():
    orchestrator = Orchestrator()
    market_data = {"price": 128.5, "volatility": 1.2, "symbol": "AAPL"}
    reports = [
        {"agent": f"Agent {i+1}", "signal": random.choice(["buy", "sell", "neutral"]), "confidence": random.randint(40, 90), "report": "Sample report."}
        for i in range(21)
    ]
    result = orchestrator.orchestrate(market_data, reports)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
