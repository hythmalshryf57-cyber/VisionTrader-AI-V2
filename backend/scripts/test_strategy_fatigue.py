import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.strategy_fatigue import strategy_fatigue
from services.internal_brain import InternalBrain

DUMMY_STRATEGY_NAME = "demo_fatigue_strategy"
DUMMY_STRATEGY_PATH = ROOT / "strategies" / f"{DUMMY_STRATEGY_NAME}.py"


def ensure_dummy_strategy():
    DUMMY_STRATEGY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DUMMY_STRATEGY_PATH.exists():
        DUMMY_STRATEGY_PATH.write_text(
            """# Demo strategy used for Strategy Fatigue test

def generate_signal(price, **kwargs):
    if price > kwargs.get('high', price):
        return 'SELL', price * 0.99
    if price < kwargs.get('low', price):
        return 'BUY', price * 1.01
    return 'NEUTRAL', None
""",
            encoding="utf-8",
        )
        print(f"Created dummy strategy file: {DUMMY_STRATEGY_PATH}")


if __name__ == "__main__":
    ensure_dummy_strategy()
    print("\n=== Strategy Fatigue Test ===\n")
    print("InternalBrain has strategy_fatigue:", hasattr(InternalBrain(), "strategy_fatigue"))

    print("\nCalculating fatigue for:", DUMMY_STRATEGY_NAME)
    fatigue = strategy_fatigue.calculate_fatigue(DUMMY_STRATEGY_NAME)
    print("calculate_fatigue result:")
    print(json.dumps(fatigue, indent=2, ensure_ascii=False))

    print("\nDetecting early warning:")
    warning = strategy_fatigue.detect_early_warning(DUMMY_STRATEGY_NAME)
    print(json.dumps(warning, indent=2, ensure_ascii=False))

    print("\nShould freeze:", strategy_fatigue.should_freeze(DUMMY_STRATEGY_NAME))

    print("\nRunning proactive evolution:")
    result = strategy_fatigue.proactive_evolution(DUMMY_STRATEGY_NAME)
    print(json.dumps(result, indent=2, ensure_ascii=False))
