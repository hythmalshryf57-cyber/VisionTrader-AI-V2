"""
# Momentum Strategy V1 (Original - Failed)
# Simple momentum breakout strategy
"""

def generate_signal(price, high_20, low_20, atr, session_hour=None):
    """Generate BUY/SELL/NEUTRAL signal based on momentum breakout."""
    stop_loss_pct = 2.0  # 2% stop loss
    entry_tolerance = 0.5  # 0.5% tolerance

    if price > high_20:
        return "BUY", price * (1 - stop_loss_pct / 100)
    elif price < low_20:
        return "SELL", price * (1 + stop_loss_pct / 100)
    return "NEUTRAL", None
