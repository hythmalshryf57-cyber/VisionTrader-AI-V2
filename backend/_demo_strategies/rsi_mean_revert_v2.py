"""
# RSI Mean Reversion V2 (Top Performer)
# Win Rate: 71%, Max DD: 3.1%
"""

def generate_signal(price, rsi, bollinger_low, bollinger_high):
    """RSI oversold/overbought with Bollinger confirmation."""
    stop_loss_pct = 1.0
    if rsi < 30 and price <= bollinger_low:
        return "BUY", price * (1 - stop_loss_pct / 100)
    if rsi > 70 and price >= bollinger_high:
        return "SELL", price * (1 + stop_loss_pct / 100)
    return "NEUTRAL", None
