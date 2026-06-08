"""'
═══════════════════════════════════════════════════════════
HYBRID STRATEGY – VisionTrader AI (Local Fallback Engine)
═══════════════════════════════════════════════════════════
Generated : 2026-05-22 23:28:45 UTC
Engine    : Local Fallback (DeepSeek API unavailable)

Merged from two strategies using signal voting:
  - Strategy A
  - Strategy B
"""'

# ─── Strategy A ─────────────────────────────────────────────
"""
# SMC London Session Strategy V3 (Top Performer)
# Win Rate: 68%, Sharpe: 1.9
"""

def generate_signal(price, ob_high, ob_low, session_hour):
    """Order Block based signal with session filter."""
    # Session filter removed to allow analysis at any hour
    
    # The following line is removed to eliminate the session hour check
    # if session_hour not in range(7, 12):
    #     return "NEUTRAL", None
    stop_loss_pct = 1.2
    if ob_low <= price <= ob_high:
        return "BUY", price * (1 - stop_loss_pct / 100)
    return "NEUTRAL", None

# ─── Voting Helper ───────────────────────────────────────────
# BUY + BUY = BUY  |  SELL + SELL = SELL  |  else = NEUTRAL
def hybrid_signal(signal_a: str, signal_b: str) -> str:
    """Resolve signals from both strategies via voting."""
    a, b = signal_a.upper().strip(), signal_b.upper().strip()
    return a if a == b else "NEUTRAL"

# ─── Strategy B ─────────────────────────────────────────────
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

# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═# ═
