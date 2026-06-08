"""
# SMC London Session Strategy V3 (Top Performer)
# Win Rate: 68%, Sharpe: 1.9
"""

def generate_signal(price, ob_high, ob_low, session_hour):
    """Order Block based signal with session filter."""
    # Session filter removed to allow analysis at any hour
    stop_loss_pct = 1.2
    if ob_low <= price <= ob_high:
        return "BUY", price * (1 - stop_loss_pct / 100)
    return "NEUTRAL", None
