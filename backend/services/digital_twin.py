import random
import numpy as np

class DigitalTwinService:
    def __init__(self, historical_data=None):
        self.historical_data = historical_data if historical_data else [random.uniform(1.0, 1.1) for _ in range(100)]
        self.volatility = np.std(self.historical_data) / np.mean(self.historical_data)

    def generate_scenarios(self, current_price, level):
        """
        Generates 3 scenarios: A (Respect), B (Break), C (Fakeout)
        """
        scenarios = {
            "Scenario A": self._simulate_respect(current_price, level),
            "Scenario B": self._simulate_break(current_price, level),
            "Scenario C": self._simulate_fakeout(current_price, level)
        }
        
        # Monte Carlo Simulation to assign probabilities
        probs = self._run_monte_carlo(current_price, level)
        for i, key in enumerate(scenarios.keys()):
            scenarios[key]["probability"] = probs[i]
            
        return scenarios

    def _simulate_respect(self, price, level):
        is_above = price > level
        entry = level + (0.0005 if is_above else -0.0005)
        tp = entry + (0.0050 if is_above else -0.0050)
        sl = level - (0.0015 if is_above else -0.0015)
        return {"entry": round(entry, 5), "sl": round(sl, 5), "tp": round(tp, 5), "desc": "Price respects the level and reverses."}

    def _simulate_break(self, price, level):
        is_above = price > level
        # If price is above, break means going below
        entry = level - 0.0005 if is_above else level + 0.0005
        tp = entry - 0.0050 if is_above else entry + 0.0050
        sl = level + 0.0015 if is_above else level - 0.0015
        return {"entry": round(entry, 5), "sl": round(sl, 5), "tp": round(tp, 5), "desc": "Price breaks the level and continues."}

    def _simulate_fakeout(self, price, level):
        is_above = price > level
        # Price fake breaks then reverses
        entry = level + (0.0002 if is_above else -0.0002)
        tp = entry + (0.0060 if is_above else -0.0060)
        sl = level - (0.0010 if is_above else 0.0010)
        return {"entry": round(entry, 5), "sl": round(sl, 5), "tp": round(tp, 5), "desc": "Price fake breaks (Stop Hunt) then reverses."}

    def _run_monte_carlo(self, price, level, iterations=100):
        counts = [0, 0, 0] # A, B, C
        for _ in range(iterations):
            path_end = price * (1 + np.random.normal(0, self.volatility))
            if abs(path_end - level) < (price * 0.001): # Respect/Fakeout
                if random.random() > 0.7:
                    counts[2] += 1 # Fakeout
                else:
                    counts[0] += 1 # Respect
            else:
                counts[1] += 1 # Break
        
        total = sum(counts)
        return [round((c/total)*100, 1) for c in counts]
