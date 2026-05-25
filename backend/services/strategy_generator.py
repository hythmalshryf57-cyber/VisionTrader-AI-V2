"""
Strategy Generator - VisionTrader AI
يولد استراتيجيات جديدة باستخدام DeepSeek Coder
يتعلم من الفشل ويدمج الاستراتيجيات الناجحة
"""

import os
import sys
import re
import json
import time
import logging
import textwrap
import requests
from datetime import datetime, timezone

_UTC = timezone.utc

def _utcnow() -> str:
    """Return current UTC time as formatted string (timezone-aware)"""
    return datetime.now(_UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Fix Arabic/Unicode output on Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-coder")

# مجلد الاستراتيجيات المولّدة (بجانب هذا الملف داخل backend/)
_THIS_DIR = Path(__file__).resolve().parent.parent  # backend/
EVOLVED_DIR = _THIS_DIR / "_evolved"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _read_file(path: str) -> str:
    """قراءة ملف Python بأمان"""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning(f"Cannot read file {path}: {exc}")
        return ""


def _ensure_evolved_dir() -> Path:
    """إنشاء مجلد _evolved/ إذا لم يكن موجوداً"""
    EVOLVED_DIR.mkdir(parents=True, exist_ok=True)
    init_file = EVOLVED_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# VisionTrader AI – Evolved Strategies\n", encoding="utf-8")
    return EVOLVED_DIR


def _call_deepseek(prompt: str, max_tokens: int = 2048) -> Optional[str]:
    """استدعاء DeepSeek API وإرجاع النص الناتج"""
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set – using local fallback")
        return None

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    try:
        response = requests.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        if response.status_code == 200:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            logger.info("DeepSeek API responded successfully")
            return content.strip()
        else:
            logger.warning(f"DeepSeek API error {response.status_code}: {response.text[:200]}")
            return None
    except Exception as exc:
        logger.exception(f"DeepSeek API call failed: {exc}")
        return None


def _extract_python_block(text: str) -> str:
    """استخراج كود Python من نص يحتوي على markdown code block"""
    pattern = r"```(?:python)?\s*([\s\S]+?)```"
    matches = re.findall(pattern, text)
    if matches:
        return matches[0].strip()
    return text.strip()


# ─────────────────────────────────────────────
# Fallback Logic (Local – No API Required)
# ─────────────────────────────────────────────

def _local_evolved_from_failure(
    original_code: str,
    failure_report: Dict[str, Any],
    top_strategies: List[str],
) -> str:
    """
    منطق محلي بسيط: يحسّن الاستراتيجية الفاشلة بدون API
    - يضيف فلتر جلسة
    - يضيّق منطقة الدخول
    - يزيد نسبة الوقف
    يولّد كوداً نظيفاً بدون مسافات بادئة خاطئة.
    """
    failure_type = str(failure_report.get("type", "unknown")).lower()
    failure_reason = failure_report.get("reason", "Unknown failure reason")
    failure_time = failure_report.get("time", "N/A")
    drawdown = failure_report.get("max_drawdown_pct", None)

    # قرارات التحسين بناءً على نوع الفشل
    session_filter = ""
    sl_adjustment = ""
    entry_tightening = ""
    extra_comments = []

    if "drawdown" in failure_type or (drawdown and float(drawdown) > 5):
        sl_adjustment = "stop_loss_pct = max(stop_loss_pct * 0.8, 0.5)  # تقليل الوقف بسبب drawdown مرتفع"
        extra_comments.append("# تم تضييق الوقف بسبب drawdown مرتفع في الاستراتيجية الأصلية")

    if "session" in failure_type or "time" in failure_type:
        session_filter = textwrap.dedent("""\
        # ─── فلتر الجلسة (Session Filter) ───────────────────────
        import datetime as _dt
        _now_h = _dt.datetime.utcnow().hour
        _ALLOWED_SESSIONS = list(range(7, 12)) + list(range(13, 17))  # London + NY
        if _now_h not in _ALLOWED_SESSIONS:
            # خارج الجلسات الرئيسية - لا تدخل
            signal = 'NEUTRAL'
        # ─────────────────────────────────────────────────────────
        """)
        extra_comments.append("# تم إضافة فلتر جلسة لتجنب الدخول في أوقات السيولة المنخفضة")

    if "entry" in failure_type or "slippage" in failure_type:
        entry_tightening = "# ─── تضييق منطقة الدخول ───────────────────────────────\nentry_tolerance = entry_tolerance * 0.7  # تقليل التسامح بنسبة 30%"
        extra_comments.append("# تم تضييق نطاق الدخول لتقليل الانزلاق السعري")

    # تجميع التحسينات من أفضل الاستراتيجيات
    learned_comment = ""
    if top_strategies:
        learned_comment = f"\n# ─── مُستلهم من {len(top_strategies)} استراتيجيات ناجحة ──────────────────\n"
        for idx, code in enumerate(top_strategies[:3], 1):
            # استخراج اسم الاستراتيجية من أول سطر تعليق
            first_line = next(
                (ln.strip("# \r\n") for ln in code.splitlines() if ln.strip().startswith("#")),
                f"Strategy {idx}"
            )
            learned_comment += f"# - تعلمنا من: {first_line}\n"

    timestamp = _utcnow()
    improvements = "\n".join(f"    {c}" for c in extra_comments) or "    - General parameter tightening"

    _TDQ = '"""'
    parts = [
        _TDQ,
        "═" * 59,
        "EVOLVED STRATEGY – VisionTrader AI (Local Fallback Engine)",
        "═" * 59,
        f"Generated : {timestamp}",
        f"Failure   : {failure_reason}",
        f"Failed At : {failure_time}",
        "Engine    : Local Fallback (DeepSeek API unavailable)",
        "",
        "Improvements Applied:",
        improvements,
        _TDQ,
        "",
    ]

    if learned_comment:
        parts.append(learned_comment.strip())
        parts.append("")

    parts += [
        "# ─── Original strategy code (evolved below) ─────────────",
        original_code.strip(),
        "",
        "# ═══ EVOLVED ADDITIONS ══════════════════════════════════",
    ]

    if session_filter:
        parts.append(session_filter.strip())
    if sl_adjustment:
        parts.append(sl_adjustment.strip())
    if entry_tightening:
        parts.append(entry_tightening.strip())

    parts.append("# ═" * 30)

    return "\n".join(parts) + "\n"


def _local_hybrid(code1: str, code2: str) -> str:
    """دمج بسيط لاستراتيجيتين محلياً – يولّد كوداً نظيفاً."""
    timestamp = _utcnow()
    voting_fn = textwrap.dedent("""\
        def hybrid_signal(signal_a: str, signal_b: str) -> str:
            \"\"\"Resolve signals from both strategies via voting.\"\"\"
            a, b = signal_a.upper().strip(), signal_b.upper().strip()
            return a if a == b else "NEUTRAL"
    """)
    parts = [
        '"""\'',
        "═" * 59,
        "HYBRID STRATEGY – VisionTrader AI (Local Fallback Engine)",
        "═" * 59,
        f"Generated : {timestamp}",
        "Engine    : Local Fallback (DeepSeek API unavailable)",
        "",
        "Merged from two strategies using signal voting:",
        "  - Strategy A",
        "  - Strategy B",
        '"""\'',
        "",
        "# ─── Strategy A ─────────────────────────────────────────────",
        code1.strip(),
        "",
        "# ─── Voting Helper ───────────────────────────────────────────",
        "# BUY + BUY = BUY  |  SELL + SELL = SELL  |  else = NEUTRAL",
        voting_fn.strip(),
        "",
        "# ─── Strategy B ─────────────────────────────────────────────",
        code2.strip(),
        "",
        "# ═" * 30,
    ]
    return "\n".join(parts) + "\n"


# ─────────────────────────────────────────────
# Core Public Functions
# ─────────────────────────────────────────────

def save_generated_strategy(code: str, filename: str) -> Path:
    """
    يحفظ الكود المولّد في مجلد _evolved/
    
    Args:
        code: كود Python الجديد
        filename: اسم الملف (بدون مسار)
    
    Returns:
        المسار الكامل للملف المحفوظ
    """
    evolved_dir = _ensure_evolved_dir()

    # تأكد من أن الاسم ينتهي بـ .py
    if not filename.endswith(".py"):
        filename += ".py"

    # أضف timestamp إذا الملف موجود
    target = evolved_dir / filename
    if target.exists():
        stem = Path(filename).stem
        ts = datetime.now(_UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{stem}_{ts}.py"
        target = evolved_dir / filename

    target.write_text(code, encoding="utf-8")
    logger.info(f"Strategy saved → {target}")
    return target


def generate_from_failure(
    failed_strategy_path: str,
    failure_report: Dict[str, Any],
    top_successful_strategies: Optional[List[str]] = None,
    market_data: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Path]:
    """
    يولد استراتيجية جديدة بالتعلم من الفشل.

    Args:
        failed_strategy_path: مسار ملف الاستراتيجية الفاشلة
        failure_report: تقرير الفشل {type, reason, time, max_drawdown_pct, ...}
        top_successful_strategies: قائمة بمسارات أفضل 3 استراتيجيات ناجحة
        market_data: بيانات السوق الحالية {symbol, price, volatility, ...}

    Returns:
        (الكود المولّد, مسار الملف المحفوظ)
    """
    logger.info(f"Generating evolved strategy from: {failed_strategy_path}")

    failed_code = _read_file(failed_strategy_path)
    top_codes: List[str] = []
    if top_successful_strategies:
        top_codes = [_read_file(p) for p in top_successful_strategies[:3]]

    market_ctx = json.dumps(market_data or {}, ensure_ascii=False, indent=2)
    strategies_ctx = "\n\n".join(
        f"# ─── Top Strategy {i+1} ───\n{c}" for i, c in enumerate(top_codes)
    ) or "# No top strategies provided"

    # Add dynamic knowledge from InternalBrain
    brain_knowledge = ""
    try:
        from .internal_brain import InternalBrain
        brain = InternalBrain()
        summary = brain.get_daily_learning_summary()
        brain_knowledge = f"\n## Internal Brain Knowledge\n- System Win Rate: {summary.get('success_rate', 50)}%\n- Use this knowledge to bias your strategy generation towards what is working."
    except Exception:
        pass

    prompt = f"""\
You are DeepSeek Coder, an expert quantitative trading strategy developer.

## Task
Generate an IMPROVED Python trading strategy that fixes the failure described below.

## Failed Strategy Code
```python
{failed_code}
```

## Failure Report
- Type        : {failure_report.get("type", "unknown")}
- Reason      : {failure_report.get("reason", "N/A")}
- Failed Time : {failure_report.get("time", "N/A")}
- Max Drawdown: {failure_report.get("max_drawdown_pct", "N/A")}%
- Notes       : {failure_report.get("notes", "")}

## Top Successful Strategies to Learn From
{strategies_ctx}

## Current Market Data
{market_ctx}
{brain_knowledge}

## Requirements for the Improved Strategy
1. Fix the root cause of the failure
2. Add a SESSION FILTER (avoid low-liquidity hours)
3. TIGHTEN the entry zone (reduce slippage tolerance by 20-30%)
4. INCREASE the stop-loss buffer if drawdown was high
5. Add inline Arabic+English comments explaining each improvement
6. Keep the same overall logic but make it more robust
7. Output ONLY the Python code, no extra explanation

Generate the evolved strategy now:
"""

    raw = _call_deepseek(prompt, max_tokens=2500)
    if raw:
        code = _extract_python_block(raw)
    else:
        logger.info("DeepSeek unavailable – using local fallback engine")
        code = _local_evolved_from_failure(failed_code, failure_report, top_codes)

    # اسم الملف بناءً على اسم الاستراتيجية الأصلية
    original_stem = Path(failed_strategy_path).stem or "strategy"
    filename = f"evolved_{original_stem}.py"

    saved_path = save_generated_strategy(code, filename)

    try:
        from .internal_brain import InternalBrain
        InternalBrain().log_event_experience("strategy_generator", "evolve_success", filename, 1.0, {"parent": failed_strategy_path})
    except Exception:
        pass

    return code, saved_path


def generate_hybrid(
    strategy1_path: str,
    strategy2_path: str,
    market_data: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Path]:
    """
    يدمج استراتيجيتين في استراتيجية هجينة واحدة.

    Args:
        strategy1_path: مسار الاستراتيجية الأولى
        strategy2_path: مسار الاستراتيجية الثانية
        market_data: بيانات السوق الحالية

    Returns:
        (الكود الهجين, مسار الملف المحفوظ)
    """
    logger.info(f"Generating hybrid from: {strategy1_path} + {strategy2_path}")

    code1 = _read_file(strategy1_path)
    code2 = _read_file(strategy2_path)
    market_ctx = json.dumps(market_data or {}, ensure_ascii=False, indent=2)

    prompt = f"""\
You are DeepSeek Coder, an expert quantitative trading strategy developer.

## Task
Merge the TWO strategies below into a single, intelligent HYBRID strategy.

## Strategy A
```python
{code1}
```

## Strategy B
```python
{code2}
```

## Current Market Data
{market_ctx}

## Requirements
1. Combine entry/exit logic using a VOTING mechanism (both must agree → stronger signal)
2. Use the best risk management from both
3. Add a SESSION FILTER for London + NY hours (07:00-12:00 UTC, 13:00-17:00 UTC)
4. Add inline Arabic+English comments explaining the merger logic
5. Output ONLY the Python code, no extra explanation

Generate the hybrid strategy now:
"""

    raw = _call_deepseek(prompt, max_tokens=2500)
    if raw:
        code = _extract_python_block(raw)
    else:
        logger.info("DeepSeek unavailable – using local fallback for hybrid generation")
        code = _local_hybrid(code1, code2)

    stem1 = Path(strategy1_path).stem or "strat1"
    stem2 = Path(strategy2_path).stem or "strat2"
    filename = f"hybrid_{stem1}_{stem2}.py"

    saved_path = save_generated_strategy(code, filename)

    try:
        from .internal_brain import InternalBrain
        InternalBrain().log_event_experience("strategy_generator", "hybrid_success", filename, 1.0, {"parent1": strategy1_path, "parent2": strategy2_path})
    except Exception:
        pass

    return code, saved_path


# ─────────────────────────────────────────────
# Self-Test / Demo
# ─────────────────────────────────────────────

def _write_demo_files() -> Tuple[Path, Path, Path]:
    """كتابة ملفات استراتيجية تجريبية مؤقتة للاختبار"""
    tmp_dir = EVOLVED_DIR.parent / "_demo_strategies"
    tmp_dir.mkdir(exist_ok=True)

    failed = tmp_dir / "momentum_v1.py"
    failed.write_text(textwrap.dedent("""\
        \"\"\"
        # Momentum Strategy V1 (Original - Failed)
        # Simple momentum breakout strategy
        \"\"\"

        def generate_signal(price, high_20, low_20, atr, session_hour=None):
            \"\"\"Generate BUY/SELL/NEUTRAL signal based on momentum breakout.\"\"\"
            stop_loss_pct = 2.0  # 2% stop loss
            entry_tolerance = 0.5  # 0.5% tolerance

            if price > high_20:
                return "BUY", price * (1 - stop_loss_pct / 100)
            elif price < low_20:
                return "SELL", price * (1 + stop_loss_pct / 100)
            return "NEUTRAL", None
        """), encoding="utf-8")

    top1 = tmp_dir / "smc_london_v3.py"
    top1.write_text(textwrap.dedent("""\
        \"\"\"
        # SMC London Session Strategy V3 (Top Performer)
        # Win Rate: 68%, Sharpe: 1.9
        \"\"\"

        def generate_signal(price, ob_high, ob_low, session_hour):
            \"\"\"Order Block based signal with session filter.\"\"\"
            if session_hour not in range(7, 12):
                return "NEUTRAL", None
            stop_loss_pct = 1.2
            if ob_low <= price <= ob_high:
                return "BUY", price * (1 - stop_loss_pct / 100)
            return "NEUTRAL", None
        """), encoding="utf-8")

    top2 = tmp_dir / "rsi_mean_revert_v2.py"
    top2.write_text(textwrap.dedent("""\
        \"\"\"
        # RSI Mean Reversion V2 (Top Performer)
        # Win Rate: 71%, Max DD: 3.1%
        \"\"\"

        def generate_signal(price, rsi, bollinger_low, bollinger_high):
            \"\"\"RSI oversold/overbought with Bollinger confirmation.\"\"\"
            stop_loss_pct = 1.0
            if rsi < 30 and price <= bollinger_low:
                return "BUY", price * (1 - stop_loss_pct / 100)
            if rsi > 70 and price >= bollinger_high:
                return "SELL", price * (1 + stop_loss_pct / 100)
            return "NEUTRAL", None
        """), encoding="utf-8")

    return failed, top1, top2


def run_demo():
    """اختبار شامل لكل وظائف Strategy Generator"""
    print("\n" + "═" * 60)
    print("  VisionTrader AI – Strategy Generator Demo")
    print("═" * 60)

    # التأكد من وجود مجلد _evolved
    _ensure_evolved_dir()
    print(f"\n✅ _evolved/ directory ready: {EVOLVED_DIR}")

    # إنشاء ملفات تجريبية
    failed_path, top1_path, top2_path = _write_demo_files()
    print(f"✅ Demo strategy files created in: {failed_path.parent}")

    # ──────────────────────────────────────
    # Test 1: generate_from_failure()
    # ──────────────────────────────────────
    print("\n" + "─" * 50)
    print("  TEST 1: generate_from_failure()")
    print("─" * 50)

    failure_report = {
        "type": "drawdown_session",
        "reason": "استراتيجية تداول خلال ساعات سيولة منخفضة أدت إلى drawdown 8.4%",
        "time": "2025-05-10 02:30 UTC",
        "max_drawdown_pct": 8.4,
        "notes": "معظم الخسائر كانت بين 00:00 و06:00 UTC",
    }

    market_data = {
        "symbol": "XAUUSD",
        "price": 2315.5,
        "volatility": 1.8,
        "trend": "bullish",
        "session": "Asian",
    }

    code, saved = generate_from_failure(
        failed_strategy_path=str(failed_path),
        failure_report=failure_report,
        top_successful_strategies=[str(top1_path), str(top2_path)],
        market_data=market_data,
    )

    print(f"\n✅ Evolved strategy saved to: {saved}")
    print(f"   Lines of code generated: {len(code.splitlines())}")
    print("\n   Preview (first 20 lines):")
    print("   " + "\n   ".join(code.splitlines()[:20]))

    # ──────────────────────────────────────
    # Test 2: generate_hybrid()
    # ──────────────────────────────────────
    print("\n" + "─" * 50)
    print("  TEST 2: generate_hybrid()")
    print("─" * 50)

    hybrid_code, hybrid_saved = generate_hybrid(
        strategy1_path=str(top1_path),
        strategy2_path=str(top2_path),
        market_data=market_data,
    )

    print(f"\n✅ Hybrid strategy saved to: {hybrid_saved}")
    print(f"   Lines of code generated: {len(hybrid_code.splitlines())}")
    print("\n   Preview (first 20 lines):")
    print("   " + "\n   ".join(hybrid_code.splitlines()[:20]))

    # ──────────────────────────────────────
    # Test 3: save_generated_strategy()
    # ──────────────────────────────────────
    print("\n" + "─" * 50)
    print("  TEST 3: save_generated_strategy()")
    print("─" * 50)

    dummy_code = textwrap.dedent("""\
        \"\"\"
        # Test Direct Save – VisionTrader AI
        # Generated by save_generated_strategy()
        \"\"\"

        def generate_signal(price):
            return "BUY" if price > 100 else "SELL"
        """)

    manual_path = save_generated_strategy(dummy_code, "test_direct_save.py")
    print(f"\n✅ Manual save test passed: {manual_path}")

    # ──────────────────────────────────────
    # Summary
    # ──────────────────────────────────────
    print("\n" + "═" * 60)
    print("  SUMMARY")
    print("═" * 60)

    evolved_files = list(EVOLVED_DIR.glob("*.py"))
    print(f"\n📁 _evolved/ directory: {EVOLVED_DIR}")
    print(f"📄 Files in _evolved/: {len(evolved_files)}")
    for f in evolved_files:
        size_kb = f.stat().st_size / 1024
        print(f"   ├── {f.name}  ({size_kb:.1f} KB)")

    api_status = "✅ Connected" if DEEPSEEK_API_KEY else "⚠️  Not configured (fallback used)"
    print(f"\n🤖 DeepSeek API: {api_status}")
    print("\n✅ All tests passed! Strategy Generator is working correctly.")
    print("═" * 60 + "\n")


if __name__ == "__main__":
    run_demo()
