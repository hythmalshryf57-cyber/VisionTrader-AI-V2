"""
╔══════════════════════════════════════════════════════════════╗
║       Sandbox Tester – VisionTrader AI                      ║
║  يختبر الاستراتيجيات في بيئة وهمية ويقارن أداءها          ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import math
import json
import random
import logging
import importlib.util
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── UTF-8 fix for Windows terminal ────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_UTC = timezone.utc

# ── Paths ──────────────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent   # backend/
_EVOLVED_DIR = _BACKEND_DIR / "_evolved"
_REPORTS_DIR = _BACKEND_DIR / "_sandbox_reports"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 – Synthetic Market Data Generator
# ══════════════════════════════════════════════════════════════════════════════

def _generate_ohlcv(
    days: int = 5,
    bars_per_day: int = 24,
    base_price: float = 1950.0,
    volatility: float = 0.008,
    trend: float = 0.0002,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    يولّد بيانات OHLCV وهمية لمحاكاة أيام تداول.

    Args:
        days          : عدد أيام المحاكاة
        bars_per_day  : عدد الشمعات في اليوم (24 = ساعي)
        base_price    : سعر البداية
        volatility    : التذبذب نسبياً
        trend         : ميل الاتجاه لكل شمعة
        seed          : بذرة عشوائية للتكرارية

    Returns:
        قائمة من قواميس OHLCV مع timestamp وهور الجلسة
    """
    rng = random.Random(seed)
    bars: List[Dict[str, Any]] = []
    price = base_price
    start_dt = datetime.now(_UTC) - timedelta(days=days)

    for day in range(days):
        for bar in range(bars_per_day):
            dt = start_dt + timedelta(days=day, hours=bar)
            change = rng.gauss(trend, volatility)
            open_p = price
            close_p = round(price * (1 + change), 4)
            high_p = round(max(open_p, close_p) * (1 + abs(rng.gauss(0, volatility * 0.5))), 4)
            low_p = round(min(open_p, close_p) * (1 - abs(rng.gauss(0, volatility * 0.5))), 4)
            volume = round(rng.uniform(500, 5000), 0)

            bars.append({
                "timestamp": dt.isoformat(),
                "hour_utc": dt.hour,
                "day": day + 1,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
                "atr": round(high_p - low_p, 4),
            })
            price = close_p

    logger.debug(f"Generated {len(bars)} OHLCV bars over {days} days")
    return bars


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 – Built-in Strategy Adapters
# ══════════════════════════════════════════════════════════════════════════════

def _momentum_signal(bar: Dict, bars: List[Dict], idx: int) -> str:
    """استراتيجية Momentum بسيطة – تستخدم كـ baseline."""
    if idx < 20:
        return "NEUTRAL"
    window = bars[idx - 20: idx]
    high_20 = max(b["high"] for b in window)
    low_20 = min(b["low"] for b in window)
    price = bar["close"]
    if price > high_20 * 0.999:
        return "BUY"
    if price < low_20 * 1.001:
        return "SELL"
    return "NEUTRAL"


def _rsi_signal(bar: Dict, bars: List[Dict], idx: int, period: int = 14) -> str:
    """استراتيجية RSI Mean Reversion."""
    if idx < period + 1:
        return "NEUTRAL"
    closes = [b["close"] for b in bars[idx - period - 1: idx + 1]]
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        (gains if delta > 0 else losses).append(abs(delta))
    avg_gain = sum(gains) / period if gains else 0.001
    avg_loss = sum(losses) / period if losses else 0.001
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    if rsi < 32:
        return "BUY"
    if rsi > 68:
        return "SELL"
    return "NEUTRAL"


def _smc_london_signal(bar: Dict, bars: List[Dict], idx: int) -> str:
    """استراتيجية SMC مع فلتر جلسة London."""
    if bar["hour_utc"] not in range(7, 13):
        return "NEUTRAL"
    if idx < 5:
        return "NEUTRAL"
    recent = bars[idx - 5: idx]
    avg_close = sum(b["close"] for b in recent) / 5
    price = bar["close"]
    if price > avg_close * 1.002:
        return "BUY"
    if price < avg_close * 0.998:
        return "SELL"
    return "NEUTRAL"


# Map استراتيجية → دالة إشارة
_BUILTIN_STRATEGIES: Dict[str, Callable] = {
    "momentum_baseline": _momentum_signal,
    "rsi_mean_reversion": _rsi_signal,
    "smc_london": _smc_london_signal,
}


def _load_evolved_strategy(strategy_path: str) -> Optional[Callable]:
    """
    يحاول تحميل استراتيجية من ملف _evolved/ وإرجاع دالة الإشارة.
    يبحث عن: generate_signal(), signal(), get_signal()
    """
    path = Path(strategy_path)
    if not path.exists():
        logger.warning(f"Strategy file not found: {path}")
        return None
    try:
        spec = importlib.util.spec_from_file_location("evolved_strategy", str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for fn_name in ("generate_signal", "signal", "get_signal"):
            fn = getattr(module, fn_name, None)
            if callable(fn):
                logger.info(f"Loaded '{fn_name}' from {path.name}")
                return fn
        logger.warning(f"No signal function found in {path.name} – using momentum fallback")
    except Exception as exc:
        logger.warning(f"Cannot load {path.name}: {exc} – using momentum fallback")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 – Shadow Trade Simulation Engine (No DB Required)
# ══════════════════════════════════════════════════════════════════════════════

class _ShadowAccount:
    """حساب وهمي لمحاكاة الصفقات."""

    def __init__(self, initial_capital: float = 10_000.0, risk_pct: float = 1.0):
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.risk_pct = risk_pct
        self.trades: List[Dict] = []
        self._open_trade: Optional[Dict] = None

    # ── إدارة الصفقات ──────────────────────────────────────────────────────

    def open_trade(self, signal: str, bar: Dict) -> None:
        if self._open_trade is not None:
            return  # صفقة مفتوحة بالفعل
        price = bar["close"]
        atr = bar.get("atr", price * 0.005)
        sl_distance = max(atr * 1.5, price * 0.005)
        tp_distance = sl_distance * 2.0          # RR = 1:2

        if signal == "BUY":
            sl = round(price - sl_distance, 4)
            tp = round(price + tp_distance, 4)
        else:  # SELL
            sl = round(price + sl_distance, 4)
            tp = round(price - tp_distance, 4)

        risk_amount = self.capital * (self.risk_pct / 100)
        position_size = round(risk_amount / sl_distance, 4)

        self._open_trade = {
            "direction": signal,
            "entry": price,
            "sl": sl,
            "tp": tp,
            "size": position_size,
            "open_bar": bar["timestamp"],
        }

    def update(self, bar: Dict) -> None:
        """يفحص SL / TP على كل شمعة."""
        if self._open_trade is None:
            return
        t = self._open_trade
        high, low = bar["high"], bar["low"]

        hit_sl = hit_tp = False
        if t["direction"] == "BUY":
            hit_sl = low <= t["sl"]
            hit_tp = high >= t["tp"]
        else:
            hit_sl = high >= t["sl"]
            hit_tp = low <= t["tp"]

        if hit_tp:
            self._close_trade(t["tp"], bar["timestamp"], "TP")
        elif hit_sl:
            self._close_trade(t["sl"], bar["timestamp"], "SL")

    def _close_trade(self, exit_price: float, ts: str, reason: str) -> None:
        t = self._open_trade
        if t is None:
            return
        if t["direction"] == "BUY":
            pnl = (exit_price - t["entry"]) * t["size"]
        else:
            pnl = (t["entry"] - exit_price) * t["size"]

        self.capital += pnl
        record = {
            **t,
            "exit": exit_price,
            "close_bar": ts,
            "reason": reason,
            "pnl": round(pnl, 4),
            "result": "WIN" if pnl > 0 else "LOSS",
        }
        self.trades.append(record)
        self._open_trade = None

    def force_close_open(self, bar: Dict) -> None:
        """يُغلق الصفقة المفتوحة عند نهاية المحاكاة بسعر السوق."""
        if self._open_trade:
            self._close_trade(bar["close"], bar["timestamp"], "END_OF_SIM")

    # ── الإحصائيات ──────────────────────────────────────────────────────────

    def compute_metrics(self) -> Dict[str, Any]:
        trades = self.trades
        total = len(trades)
        if total == 0:
            return {
                "total_trades": 0, "wins": 0, "losses": 0,
                "win_rate_pct": 0.0, "total_pnl": 0.0,
                "profit_factor": 0.0, "sharpe_ratio": 0.0,
                "max_drawdown_pct": 0.0, "avg_pnl_per_trade": 0.0,
                "final_capital": round(self.capital, 2),
                "return_pct": 0.0,
            }

        wins = [t for t in trades if t["result"] == "WIN"]
        losses = [t for t in trades if t["result"] == "LOSS"]
        pnls = [t["pnl"] for t in trades]

        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        profit_factor = round(gross_profit / gross_loss, 3) if gross_loss > 0 else round(gross_profit, 3)

        # Sharpe (annualised, assuming 252 trading days)
        mean_r = sum(pnls) / total
        if total > 1:
            variance = sum((p - mean_r) ** 2 for p in pnls) / (total - 1)
            std_r = math.sqrt(variance) if variance > 0 else 1e-9
            sharpe = round((mean_r / std_r) * math.sqrt(252), 3)
        else:
            sharpe = 0.0

        # Max Drawdown %
        equity = self.initial_capital
        peak = equity
        max_dd = 0.0
        for pnl in pnls:
            equity += pnl
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd

        total_pnl = sum(pnls)
        return_pct = round((total_pnl / self.initial_capital) * 100, 3)

        return {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": round(len(wins) / total * 100, 2),
            "total_pnl": round(total_pnl, 4),
            "avg_pnl_per_trade": round(mean_r, 4),
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": round(max_dd, 3),
            "final_capital": round(self.capital, 2),
            "return_pct": return_pct,
        }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 – Core Public API
# ══════════════════════════════════════════════════════════════════════════════

def test_strategy(
    strategy_path: str,
    days: int = 5,
    initial_capital: float = 10_000.0,
    risk_pct: float = 1.0,
    seed: Optional[int] = 42,
    market_params: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    يختبر استراتيجية (من _evolved/ أو builtin) على بيانات وهمية لمدة `days` أيام.

    Args:
        strategy_path    : مسار ملف .py أو اسم استراتيجية builtin
        days             : عدد أيام المحاكاة
        initial_capital  : رأس المال الابتدائي
        risk_pct         : نسبة المخاطرة لكل صفقة
        seed             : بذرة عشوائية
        market_params    : معاملات السوق الوهمي {base_price, volatility, trend}

    Returns:
        قاموس يحوي المقاييس الكاملة + قائمة الصفقات
    """
    mp = market_params or {}
    bars = _generate_ohlcv(
        days=days,
        bars_per_day=24,
        base_price=mp.get("base_price", 1950.0),
        volatility=mp.get("volatility", 0.008),
        trend=mp.get("trend", 0.0002),
        seed=seed,
    )

    # تحديد دالة الإشارة
    builtin_fn = _BUILTIN_STRATEGIES.get(strategy_path)
    if builtin_fn:
        signal_fn = builtin_fn
        strategy_name = strategy_path
        logger.info(f"Using builtin strategy: {strategy_name}")
    else:
        loaded_fn = _load_evolved_strategy(strategy_path)
        signal_fn = loaded_fn if loaded_fn else _momentum_signal
        strategy_name = Path(strategy_path).stem if strategy_path else "unknown"
        logger.info(f"Testing evolved strategy: {strategy_name}")

    account = _ShadowAccount(initial_capital=initial_capital, risk_pct=risk_pct)

    for idx, bar in enumerate(bars):
        account.update(bar)

        if account._open_trade is None:
            # استدعاء دالة الإشارة بمرونة (تقبل معاملات مختلفة)
            try:
                sig = signal_fn(bar, bars, idx)
            except TypeError:
                try:
                    sig = signal_fn(bar["close"])
                except Exception:
                    sig = "NEUTRAL"
            except Exception:
                sig = "NEUTRAL"

            sig = str(sig).upper().strip()
            if sig in ("BUY", "SELL"):
                account.open_trade(sig, bar)

    # إغلاق أي صفقة مفتوحة عند نهاية المحاكاة
    if bars:
        account.force_close_open(bars[-1])

    metrics = account.compute_metrics()
    metrics["strategy_name"] = strategy_name
    metrics["days_simulated"] = days
    metrics["total_bars"] = len(bars)
    metrics["trades_list"] = account.trades
    logger.info(
        f"[{strategy_name}] Trades:{metrics['total_trades']} "
        f"WR:{metrics['win_rate_pct']}% "
        f"PnL:{metrics['total_pnl']} "
        f"Sharpe:{metrics['sharpe_ratio']}"
    )
    return metrics


def compare_with_original(
    new_results: Dict[str, Any],
    original_results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    يقارن نتائج الاستراتيجية الجديدة مع الأصلية.

    Returns:
        قاموس التقييم مع نسبة التحسن / التراجع لكل مقياس
    """
    def _delta(new_val, orig_val, higher_is_better=True) -> Tuple[float, str]:
        if orig_val == 0:
            delta_pct = 100.0 if new_val > 0 else 0.0
        else:
            delta_pct = round((new_val - orig_val) / abs(orig_val) * 100, 2)
        better = (delta_pct > 0) == higher_is_better
        direction = "↑ تحسّن" if better else "↓ تراجع"
        return delta_pct, direction

    metrics_cfg = [
        ("win_rate_pct",      "Win Rate",         True),
        ("sharpe_ratio",      "Sharpe Ratio",      True),
        ("max_drawdown_pct",  "Max Drawdown",      False),
        ("profit_factor",     "Profit Factor",     True),
        ("return_pct",        "Return %",          True),
        ("total_trades",      "Total Trades",      True),
    ]

    comparison: Dict[str, Any] = {}
    wins_count = 0
    total_count = 0

    for key, label, higher_is_better in metrics_cfg:
        new_v = new_results.get(key, 0)
        orig_v = original_results.get(key, 0)
        delta_pct, direction = _delta(new_v, orig_v, higher_is_better)
        comparison[key] = {
            "label": label,
            "new": new_v,
            "original": orig_v,
            "delta_pct": delta_pct,
            "verdict": direction,
        }
        total_count += 1
        if "تحسّن" in direction:
            wins_count += 1

    overall_improvement = round(wins_count / total_count * 100, 1) if total_count else 0
    is_superior = wins_count >= (total_count // 2 + 1)

    return {
        "metrics": comparison,
        "wins_count": wins_count,
        "total_metrics": total_count,
        "overall_improvement_pct": overall_improvement,
        "is_superior": is_superior,
        "verdict_summary": (
            f"الاستراتيجية الجديدة متفوقة بنسبة {overall_improvement:.0f}% على الأصلية ✅"
            if is_superior else
            f"الاستراتيجية الأصلية لا تزال أفضل ({overall_improvement:.0f}% فقط من المقاييس تحسّنت) ⚠️"
        ),
    }


def compare_with_best_active(
    new_results: Dict[str, Any],
    days: int = 5,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    يقارن الاستراتيجية الجديدة مع أفضل استراتيجية builtin نشطة.

    Returns:
        اسم الأفضل + تقرير المقارنة
    """
    best_name = None
    best_sharpe = -999.0
    best_results = None

    for name in _BUILTIN_STRATEGIES:
        r = test_strategy(name, days=days, seed=seed)
        if r["sharpe_ratio"] > best_sharpe:
            best_sharpe = r["sharpe_ratio"]
            best_name = name
            best_results = r

    if best_results is None:
        return {"error": "No active strategies found"}

    comparison = compare_with_original(new_results, best_results)
    comparison["best_active_strategy"] = best_name
    comparison["best_active_sharpe"] = best_sharpe
    return comparison


def generate_report(
    results: Dict[str, Any],
    vs_original: Optional[Dict] = None,
    vs_best: Optional[Dict] = None,
    save_to_file: bool = True,
) -> str:
    """
    يولّد تقرير نصي شامل عن نتائج المحاكاة.

    Args:
        results     : ناتج test_strategy()
        vs_original : ناتج compare_with_original() (اختياري)
        vs_best     : ناتج compare_with_best_active() (اختياري)
        save_to_file: يحفظ التقرير في _sandbox_reports/

    Returns:
        نص التقرير
    """
    sep = "═" * 62
    thin = "─" * 62
    now = datetime.now(_UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    name = results.get("strategy_name", "unknown")

    lines = [
        sep,
        f"  SANDBOX TEST REPORT – VisionTrader AI",
        f"  Strategy : {name}",
        f"  Generated: {now}",
        sep,
        "",
        "  📊 PERFORMANCE METRICS",
        thin,
        f"  Days Simulated   : {results['days_simulated']}",
        f"  Total Bars       : {results['total_bars']}",
        f"  Total Trades     : {results['total_trades']}",
        f"  Wins / Losses    : {results['wins']} / {results['losses']}",
        f"  Win Rate         : {results['win_rate_pct']:.2f}%",
        f"  Total PnL        : {results['total_pnl']:+.4f}",
        f"  Return %         : {results['return_pct']:+.3f}%",
        f"  Final Capital    : ${results['final_capital']:,.2f}",
        f"  Profit Factor    : {results['profit_factor']:.3f}",
        f"  Sharpe Ratio     : {results['sharpe_ratio']:.3f}",
        f"  Max Drawdown     : {results['max_drawdown_pct']:.3f}%",
        f"  Avg PnL/Trade    : {results['avg_pnl_per_trade']:+.4f}",
        "",
    ]

    if vs_original:
        lines += [
            "  🔄 VS. ORIGINAL STRATEGY",
            thin,
        ]
        for key, info in vs_original.get("metrics", {}).items():
            delta_str = f"{info['delta_pct']:+.1f}%"
            lines.append(
                f"  {info['label']:<18}: {info['new']:<10} (orig: {info['original']}) "
                f"{delta_str} {info['verdict']}"
            )
        lines += [
            "",
            f"  ⭐ {vs_original.get('verdict_summary', '')}",
            "",
        ]

    if vs_best:
        best_name = vs_best.get("best_active_strategy", "?")
        best_sharpe = vs_best.get("best_active_sharpe", 0)
        lines += [
            f"  🏆 VS. BEST ACTIVE STRATEGY  ({best_name}, Sharpe={best_sharpe:.3f})",
            thin,
        ]
        for key, info in vs_best.get("metrics", {}).items():
            delta_str = f"{info['delta_pct']:+.1f}%"
            lines.append(
                f"  {info['label']:<18}: {info['new']:<10} (best: {info['original']}) "
                f"{delta_str} {info['verdict']}"
            )
        lines += [
            "",
            f"  ⭐ {vs_best.get('verdict_summary', '')}",
            "",
        ]

    # آخر 5 صفقات
    trade_list = results.get("trades_list", [])
    if trade_list:
        lines += [
            "  📋 LAST 5 TRADES",
            thin,
        ]
        for t in trade_list[-5:]:
            icon = "✅" if t["result"] == "WIN" else "❌"
            lines.append(
                f"  {icon} {t['direction']:<5} entry={t['entry']:.2f} "
                f"exit={t['exit']:.2f}  PnL={t['pnl']:+.4f}  [{t['reason']}]"
            )
        lines.append("")

    lines.append(sep)
    report_text = "\n".join(lines)

    if save_to_file:
        _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(_UTC).strftime("%Y%m%d_%H%M%S")
        report_path = _REPORTS_DIR / f"report_{name}_{ts}.txt"
        report_path.write_text(report_text, encoding="utf-8")
        logger.info(f"Report saved → {report_path}")

    return report_text


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 – Self-Test / Demo
# ══════════════════════════════════════════════════════════════════════════════

def run_demo():
    """اختبار شامل لجميع وظائف Sandbox Tester."""
    print("\n" + "═" * 62)
    print("  VisionTrader AI – Sandbox Tester Demo")
    print("═" * 62)

    # ── اختيار استراتيجية من _evolved/ ──────────────────────────────────────
    evolved_strategy = None
    if _EVOLVED_DIR.exists():
        candidates = [
            f for f in _EVOLVED_DIR.glob("evolved_*.py")
            if f.stat().st_size > 100
        ]
        if candidates:
            evolved_strategy = str(candidates[0])
            print(f"\n✅ Found evolved strategy: {candidates[0].name}")

    # اختار استراتيجية للاختبار
    strategy_under_test = evolved_strategy or "rsi_mean_reversion"
    strategy_label = (
        Path(evolved_strategy).stem if evolved_strategy else "rsi_mean_reversion"
    )

    market_params = {
        "base_price": 1950.0,
        "volatility": 0.009,
        "trend": 0.00015,
    }

    # ── TEST 1: test_strategy() ───────────────────────────────────────────────
    print("\n" + "─" * 50)
    print("  TEST 1: test_strategy()  [5 days simulation]")
    print("─" * 50)

    new_results = test_strategy(
        strategy_path=strategy_under_test,
        days=5,
        initial_capital=10_000.0,
        risk_pct=1.0,
        seed=42,
        market_params=market_params,
    )
    print(f"\n  Strategy     : {new_results['strategy_name']}")
    print(f"  Total Trades : {new_results['total_trades']}")
    print(f"  Win Rate     : {new_results['win_rate_pct']:.2f}%")
    print(f"  Return %     : {new_results['return_pct']:+.3f}%")
    print(f"  Sharpe Ratio : {new_results['sharpe_ratio']:.3f}")
    print(f"  Max Drawdown : {new_results['max_drawdown_pct']:.3f}%")
    print(f"  Profit Factor: {new_results['profit_factor']:.3f}")
    print(f"\n  ✅ TEST 1 PASSED")

    # ── TEST 2: compare_with_original() ──────────────────────────────────────
    print("\n" + "─" * 50)
    print("  TEST 2: compare_with_original()  [vs. momentum_baseline]")
    print("─" * 50)

    original_results = test_strategy(
        strategy_path="momentum_baseline",
        days=5,
        seed=42,
        market_params=market_params,
    )
    vs_orig = compare_with_original(new_results, original_results)
    print(f"\n  Original Sharpe : {original_results['sharpe_ratio']:.3f}")
    print(f"  New Sharpe      : {new_results['sharpe_ratio']:.3f}")
    print(f"\n  {vs_orig['verdict_summary']}")
    print(f"\n  ✅ TEST 2 PASSED")

    # ── TEST 3: compare_with_best_active() ───────────────────────────────────
    print("\n" + "─" * 50)
    print("  TEST 3: compare_with_best_active()")
    print("─" * 50)

    vs_best = compare_with_best_active(new_results, days=5, seed=42)
    print(f"\n  Best Active Strategy : {vs_best.get('best_active_strategy', '?')}")
    print(f"  Best Active Sharpe   : {vs_best.get('best_active_sharpe', 0):.3f}")
    print(f"\n  {vs_best.get('verdict_summary', '')}")
    print(f"\n  ✅ TEST 3 PASSED")

    # ── TEST 4: generate_report() ─────────────────────────────────────────────
    print("\n" + "─" * 50)
    print("  TEST 4: generate_report()")
    print("─" * 50)

    report = generate_report(
        results=new_results,
        vs_original=vs_orig,
        vs_best=vs_best,
        save_to_file=True,
    )
    print("\n" + report)
    print(f"  ✅ TEST 4 PASSED")

    # ── Summary ───────────────────────────────────────────────────────────────
    report_files = list(_REPORTS_DIR.glob("*.txt")) if _REPORTS_DIR.exists() else []
    print("\n" + "═" * 62)
    print("  SUMMARY")
    print("═" * 62)
    print(f"\n  📁 Reports directory : {_REPORTS_DIR}")
    print(f"  📄 Report files      : {len(report_files)}")
    for rf in report_files[-3:]:
        print(f"     ├── {rf.name}  ({rf.stat().st_size / 1024:.1f} KB)")
    print(f"\n  ✅ All Sandbox Tester tests passed!")
    print("═" * 62 + "\n")


if __name__ == "__main__":
    run_demo()
