    """
    ═══════════════════════════════════════════════════════════
    HYBRID STRATEGY – VisionTrader AI (Local Fallback Engine)
    ═══════════════════════════════════════════════════════════
    Generated : 2026-05-22 21:45:54 UTC
    Engine    : Local Fallback (DeepSeek API unavailable)

    Merged from two strategies using signal voting:
    - Strategy A: first file
    - Strategy B: second file
    """

    # ─── Strategy A ────────────────────────────────────────────
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


    # ─── Strategy B (integrated below with voting logic) ───────
    # Signal voting: final signal = majority of A + B
    # If A says BUY and B says BUY  → BUY
    # If A says SELL and B says SELL → SELL
    # Otherwise → NEUTRAL (conflict resolution)

    def hybrid_signal(signal_a: str, signal_b: str) -> str:
        """Resolve signals from both strategies."""
        a, b = signal_a.upper().strip(), signal_b.upper().strip()
        if a == b:
            return a
        return "NEUTRAL"

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

    # ═══════════════════════════════════════════════════════════
