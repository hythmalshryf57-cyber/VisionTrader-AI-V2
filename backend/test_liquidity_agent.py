from services.agent_manager import LiquidityAgent, AgentManager
import time

agent = LiquidityAgent()
manager = AgentManager(agents=[agent])

# build sample unified_data
unified_data = {
    "symbol": "BTCUSD",
    "order_book": {
        "bids": [[60000, 0.5], [59990, 1.0], [59980, 2.0], [59970, 1.5], [59960, 3.0]],
        "asks": [[60010, 0.4], [60020, 0.8], [60030, 1.2], [60040, 0.9], [60050, 2.5]]
    },
    "spread_history": [0.002, 0.003, 0.0025, 0.0022],
    "recent_trades": [{"price":60005, "size":1.2}, {"price":60003, "size":0.8}],
    "volume": [100,120,150,130],
    "avg_volume": 200,
    "timestamp": int(time.time()),
    "upcoming_news": [{"minutes_to": 120}],
}

out = manager.run(unified_data)
print(out)
