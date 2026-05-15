import random

class BrokerAuditor:
    def __init__(self):
        # In a real app, this would fetch from a reliable API like yfinance or Bloomberg
        self.global_prices = {
            "XAU/USD": 2350.50,
            "EUR/USD": 1.0855,
            "BTC/USD": 65000.00
        }

    def audit_trade(self, market, execution_price, declared_spread=0.0001):
        global_price = self.global_prices.get(market, execution_price * (1 + random.uniform(-0.0005, 0.0005)))
        
        slippage = abs(execution_price - global_price) / global_price
        actual_spread = declared_spread * random.uniform(0.8, 2.0) # Mock variation
        
        is_safe = slippage < 0.001 # 0.1% threshold
        
        return {
            "market": market,
            "execution_price": execution_price,
            "global_price": round(global_price, 5),
            "slippage_pct": round(slippage * 100, 4),
            "actual_spread": round(actual_spread, 5),
            "is_safe": is_safe,
            "alert": "WARNING: High Slippage Detected!" if not is_safe else "Execution within safety limits."
        }

    def get_audit_report(self, user_id):
        # Mock summary
        return {
            "average_slippage": 0.0002,
            "spread_efficiency": "95%",
            "broker_trust_score": "High",
            "incidents": 0
        }
