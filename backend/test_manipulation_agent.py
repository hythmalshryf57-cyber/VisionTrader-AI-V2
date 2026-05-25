from services.agent_manager import ManipulationDetector, AgentManager

agent = ManipulationDetector()
manager = AgentManager(agents=[agent])

# Scenario 1: spoofing events
unified_spoof = {
    "order_book": {
        "bids": [[100.0, 10], [99.9, 8], [99.8, 5]],
        "asks": [[100.5, 12], [100.6, 15], [100.7, 20]]
    },
    "order_events": [
        {"action": "add", "side": "sell", "price": 100.5, "size": 500, "ts": 1000},
        {"action": "remove", "side": "sell", "price": 100.5, "size": 500, "ts": 1050}
    ],
    "recent_trades": [[100.2, 1], [100.3, 2]],
    "price_moves": [{"delta": 0.015, "duration": 30}]
}

# Scenario 2: clean market
unified_clean = {
    "order_book": {
        "bids": [[100.0, 100], [99.9, 80], [99.8, 50]],
        "asks": [[100.5, 120], [100.6, 110], [100.7, 90]]
    },
    "order_events": [
        {"action": "add", "side": "sell", "price": 101.0, "size": 10, "ts": 2000},
    ],
    "recent_trades": [[100.2, 5], [100.3, 2], [100.4, 1]],
    "price_moves": [{"delta": 0.001, "duration": 600}]
}

print('--- Spoof Scenario ---')
print(manager.run(unified_spoof))
print('\n--- Clean Scenario ---')
print(manager.run(unified_clean))
