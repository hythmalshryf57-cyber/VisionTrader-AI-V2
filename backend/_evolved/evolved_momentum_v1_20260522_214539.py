    """
    ═══════════════════════════════════════════════════════════
    EVOLVED STRATEGY – VisionTrader AI (Local Fallback Engine)
    ═══════════════════════════════════════════════════════════
    Generated : 2026-05-22 21:45:39 UTC
    Failure   : استراتيجية تداول خلال ساعات سيولة منخفضة أدت إلى drawdown 8.4%
    Failed At : 2025-05-10 02:30 UTC
    Engine    : Local Fallback (DeepSeek API unavailable)

    Improvements Applied:
        # تم تضييق الوقف بسبب drawdown مرتفع في الاستراتيجية الأصلية
    # تم إضافة فلتر جلسة لتجنب الدخول في أوقات السيولة المنخفضة

    """

# ─── مُستلهم من 2 استراتيجيات ناجحة ──────────────────
# - تعلمنا من: SMC London Session Strategy V3 (Top Performer)
# - تعلمنا من: RSI Mean Reversion V2 (Top Performer)

    # ─── Original strategy code (evolved below) ───────────────
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


    # ═══ EVOLVED ADDITIONS ════════════════════════════════════
    # ─── فلتر الجلسة (Session Filter) ───────────────────────
import datetime as _dt
_now_h = _dt.datetime.utcnow().hour
_ALLOWED_SESSIONS = list(range(7, 12)) + list(range(13, 17))  # London + NY
if _now_h not in _ALLOWED_SESSIONS:
    # خارج الجلسات الرئيسية - لا تدخل
    signal = 'NEUTRAL'
# ─────────────────────────────────────────────────────────

    stop_loss_pct = max(stop_loss_pct * 0.8, 0.5)  # تقليل الوقف بسبب drawdown مرتفع

    # ═══════════════════════════════════════════════════════════
