from services.agent_manager import TemporalAuditAgent, AgentManager

agent = TemporalAuditAgent()
manager = AgentManager(agents=[agent])

# Scenario 1: agreement across many frames (buy)
unified_data_agree = {
    "timeframe_signals": {
        "1m": {"signal": "buy", "confidence": 40},
        "5m": {"signal": "buy", "confidence": 50},
        "15m": {"signal": "buy", "confidence": 60},
        "1h": {"signal": "buy", "confidence": 55},
        "4h": {"signal": "buy", "confidence": 70},
        "1d": {"signal": "neutral", "confidence": 30}
    }
}

# Scenario 2: conflict 4h (sell) vs many short frames (buy)
unified_data_conflict = {
    "timeframe_signals": {
        "1m": {"signal": "buy", "confidence": 40},
        "5m": {"signal": "buy", "confidence": 45},
        "15m": {"signal": "buy", "confidence": 50},
        "1h": {"signal": "neutral", "confidence": 30},
        "4h": {"signal": "sell", "confidence": 80},
        "1d": {"signal": "sell", "confidence": 60}
    }
}

print("--- Agreement Scenario ---")
print(manager.run(unified_data_agree))
print('\n--- Conflict Scenario ---')
print(manager.run(unified_data_conflict))
