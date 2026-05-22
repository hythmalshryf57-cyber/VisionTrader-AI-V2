"""
╔══════════════════════════════════════════════════════════════════╗
║      Advanced Backtesting Engine – VisionTrader AI              ║
║                                                                  ║
║  الميزات:                                                        ║
║   • Monte Carlo Simulation  (1000 سيناريو)                      ║
║   • Advanced Metrics        (Sharpe, Sortino, Calmar, …)        ║
║   • Walk-Forward Analysis   (In-Sample vs Out-Sample)           ║
║   • Overfitting Detection                                        ║
║   • Risk of Ruin Calculation                                     ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ───────────────────────── Logger ──────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("BacktestEngine")

# ── إصلاح ترميز Windows ────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════
#  Data Structures
# ══════════════════════════════════════════════════════════════════

@dataclass
class Trade:
    """صفقة واحدة في نظام الاختبار"""
    entry_date:  str
    exit_date:   str
    symbol:      str
    direction:   str          # "long" | "short"
    entry_price: float
    exit_price:  float
    size:        float        # حجم الصفقة (lots / units)
    pnl:         float        # الربح/الخسارة الصافي
    pnl_pct:     float        # نسبة الربح/الخسارة
    duration_h:  float = 0.0  # مدة الصفقة بالساعات
    max_adverse: float = 0.0  # أقصى خسارة أثناء الصفقة
    max_favored: float = 0.0  # أقصى ربح أثناء الصفقة


@dataclass
class AdvancedMetrics:
    """مجموعة كاملة من مقاييس الأداء"""
    # ─── العوائد الأساسية ─────────────────────────────
    total_return:        float = 0.0
    total_return_pct:    float = 0.0
    annualized_return:   float = 0.0
    cagr:                float = 0.0

    # ─── إحصاءات الصفقات ──────────────────────────────
    total_trades:        int   = 0
    winning_trades:      int   = 0
    losing_trades:       int   = 0
    win_rate:            float = 0.0
    avg_win:             float = 0.0
    avg_loss:            float = 0.0
    avg_trade:           float = 0.0
    expectancy:          float = 0.0      # Expectancy per trade
    profit_factor:       float = 0.0

    # ─── المخاطرة والتذبذب ────────────────────────────
    sharpe_ratio:        float = 0.0
    sortino_ratio:       float = 0.0
    calmar_ratio:        float = 0.0
    max_drawdown:        float = 0.0
    max_drawdown_pct:    float = 0.0
    avg_drawdown:        float = 0.0
    recovery_factor:     float = 0.0
    risk_of_ruin:        float = 0.0      # احتمالية الخراب (0-1)

    # ─── تحليل السلاسل ───────────────────────────────
    max_win_streak:      int   = 0
    max_loss_streak:     int   = 0
    current_streak:      int   = 0
    streak_type:         str   = ""       # "win" | "loss"

    # ─── عوامل الجودة ────────────────────────────────
    ulcer_index:         float = 0.0
    serenity_ratio:      float = 0.0
    payoff_ratio:        float = 0.0      # avg_win / avg_loss


@dataclass
class MonteCarloResult:
    """نتائج محاكاة Monte Carlo"""
    simulations:          int   = 1000
    success_probability:  float = 0.0    # احتمالية تحقيق ربح
    median_return:        float = 0.0
    avg_return:           float = 0.0
    best_case:            float = 0.0    # أفضل سيناريو (95th percentile)
    worst_case:           float = 0.0   # أسوأ سيناريو (5th percentile)
    avg_max_drawdown:     float = 0.0
    worst_drawdown:       float = 0.0   # أسوأ drawdown ممكن
    var_95:               float = 0.0    # Value at Risk (95%)
    cvar_95:              float = 0.0   # Conditional VaR
    percentiles:          Dict[str, float] = field(default_factory=dict)
    all_returns:          List[float]      = field(default_factory=list)
    all_drawdowns:        List[float]      = field(default_factory=list)


@dataclass
class WalkForwardResult:
    """نتائج Walk-Forward Analysis"""
    windows:              int   = 0
    in_sample_return:     float = 0.0
    out_sample_return:    float = 0.0
    efficiency_ratio:     float = 0.0   # out/in – أعلى = أفضل
    is_overfit:           bool  = False
    overfit_score:        float = 0.0   # 0=لا overfitting, 1=كامل
    periods:              List[Dict] = field(default_factory=list)
    recommendation:       str  = ""


# ══════════════════════════════════════════════════════════════════
#  Helper: Pure-Python Statistics (بدون NumPy)
# ══════════════════════════════════════════════════════════════════

def _mean(data: List[float]) -> float:
    return sum(data) / len(data) if data else 0.0

def _std(data: List[float], ddof: int = 1) -> float:
    if len(data) < 2:
        return 0.0
    m = _mean(data)
    variance = sum((x - m) ** 2 for x in data) / (len(data) - ddof)
    return math.sqrt(variance)

def _percentile(data: List[float], p: float) -> float:
    """حساب النسبة المئوية"""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (p / 100) * (len(sorted_data) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo)

def _max_drawdown(equity_curve: List[float]) -> Tuple[float, float]:
    """
    يحسب Max Drawdown ونسبته من equity curve.
    يرجع (drawdown_abs, drawdown_pct)
    """
    if not equity_curve:
        return 0.0, 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = peak - val
        dd_pct = dd / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = dd_pct
    return max_dd, max_dd_pct

def _build_equity_curve(initial: float, pnls: List[float]) -> List[float]:
    curve = [initial]
    for pnl in pnls:
        curve.append(curve[-1] + pnl)
    return curve

def _drawdown_series(equity_curve: List[float]) -> List[float]:
    """سلسلة قيم الـ drawdown في كل نقطة"""
    result = []
    peak = equity_curve[0]
    for val in equity_curve:
        if val > peak:
            peak = val
        result.append(peak - val)
    return result


# ══════════════════════════════════════════════════════════════════
#  Advanced Metrics Calculator
# ══════════════════════════════════════════════════════════════════

class MetricsCalculator:
    """يحسب جميع مقاييس الأداء المتقدمة"""

    RISK_FREE_RATE = 0.05      # 5% سنوياً
    TRADING_DAYS   = 252

    def calculate(self, trades: List[Trade], initial_capital: float = 10_000.0) -> AdvancedMetrics:
        m = AdvancedMetrics()
        if not trades:
            return m

        pnls      = [t.pnl for t in trades]
        pnls_pct  = [t.pnl_pct for t in trades]
        wins      = [p for p in pnls if p > 0]
        losses    = [p for p in pnls if p < 0]

        # ─── إحصاءات أساسية ────────────────────────────────────────
        m.total_trades   = len(trades)
        m.winning_trades = len(wins)
        m.losing_trades  = len(losses)
        m.win_rate       = len(wins) / len(trades) if trades else 0.0
        m.avg_win        = _mean(wins)    if wins   else 0.0
        m.avg_loss       = _mean(losses)  if losses else 0.0
        m.avg_trade      = _mean(pnls)
        m.total_return   = sum(pnls)
        m.total_return_pct = m.total_return / initial_capital

        # Profit Factor
        gross_profit = sum(wins)
        gross_loss   = abs(sum(losses))
        m.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Payoff Ratio
        m.payoff_ratio = abs(m.avg_win / m.avg_loss) if m.avg_loss != 0 else float("inf")

        # Expectancy per trade
        m.expectancy = (m.win_rate * m.avg_win) + ((1 - m.win_rate) * m.avg_loss)

        # ─── Equity Curve & Drawdown ────────────────────────────────
        equity = _build_equity_curve(initial_capital, pnls)
        m.max_drawdown, m.max_drawdown_pct = _max_drawdown(equity)

        dd_series = _drawdown_series(equity)
        non_zero_dd = [d for d in dd_series if d > 0]
        m.avg_drawdown = _mean(non_zero_dd) if non_zero_dd else 0.0

        # Recovery Factor
        m.recovery_factor = m.total_return / m.max_drawdown if m.max_drawdown > 0 else float("inf")

        # ─── Annualized Return ───────────────────────────────────────
        if len(trades) >= 2:
            try:
                d1 = datetime.fromisoformat(trades[0].entry_date)
                d2 = datetime.fromisoformat(trades[-1].exit_date)
                years = max((d2 - d1).days / 365.25, 1/365.25)
            except Exception:
                years = len(trades) / 252.0

            final_equity = equity[-1]
            if initial_capital > 0 and final_equity > 0:
                m.annualized_return = (final_equity / initial_capital) ** (1 / years) - 1
                m.cagr = m.annualized_return
        else:
            years = 1.0

        # ─── Sharpe Ratio ────────────────────────────────────────────
        if len(pnls_pct) >= 2:
            daily_rf = self.RISK_FREE_RATE / self.TRADING_DAYS
            excess   = [r - daily_rf for r in pnls_pct]
            std_ex   = _std(excess)
            if std_ex > 0:
                m.sharpe_ratio = (_mean(excess) / std_ex) * math.sqrt(self.TRADING_DAYS)

        # ─── Sortino Ratio ───────────────────────────────────────────
        neg_returns = [r for r in pnls_pct if r < 0]
        if neg_returns and len(pnls_pct) >= 2:
            downside_std = _std(neg_returns)
            if downside_std > 0:
                daily_rf  = self.RISK_FREE_RATE / self.TRADING_DAYS
                mean_ret  = _mean(pnls_pct) - daily_rf
                m.sortino_ratio = (mean_ret / downside_std) * math.sqrt(self.TRADING_DAYS)

        # ─── Calmar Ratio ────────────────────────────────────────────
        if m.max_drawdown_pct > 0:
            m.calmar_ratio = m.annualized_return / m.max_drawdown_pct

        # ─── Ulcer Index ─────────────────────────────────────────────
        dd_pcts = [d / max(equity) for d in dd_series] if max(equity) > 0 else [0.0]
        m.ulcer_index = math.sqrt(_mean([d ** 2 for d in dd_pcts]))

        # Serenity = Sortino / Ulcer
        if m.ulcer_index > 0:
            m.serenity_ratio = m.sortino_ratio / m.ulcer_index

        # ─── Win/Loss Streak ─────────────────────────────────────────
        max_win_s, max_loss_s = 0, 0
        cur_win_s, cur_loss_s = 0, 0
        for pnl in pnls:
            if pnl > 0:
                cur_win_s  += 1
                cur_loss_s  = 0
            else:
                cur_loss_s += 1
                cur_win_s   = 0
            max_win_s  = max(max_win_s,  cur_win_s)
            max_loss_s = max(max_loss_s, cur_loss_s)

        m.max_win_streak  = max_win_s
        m.max_loss_streak = max_loss_s
        m.current_streak  = cur_win_s if cur_win_s > 0 else -cur_loss_s
        m.streak_type     = "win" if cur_win_s > 0 else "loss"

        # ─── Risk of Ruin ─────────────────────────────────────────────
        m.risk_of_ruin = self._calc_risk_of_ruin(m.win_rate, m.payoff_ratio)

        return m

    @staticmethod
    def _calc_risk_of_ruin(win_rate: float, payoff: float, ruin_pct: float = 0.5) -> float:
        """
        حساب احتمالية الخراب (فقدان X% من رأس المال).
        يستخدم صيغة مبسطة.
        """
        if win_rate <= 0 or win_rate >= 1 or payoff <= 0:
            return 1.0
        lose_rate = 1 - win_rate
        if payoff == 0:
            return 1.0
        # r = (lose_rate / win_rate)^(1/payoff) – إذا r < 1 → خطر
        try:
            r = (lose_rate / win_rate)
            if r >= 1:
                return 1.0
            # Risk of ruin ≈ r^(capital_units)
            # نستخدم 10 وحدات كمرجع
            ror = r ** 10
            return min(max(ror, 0.0), 1.0)
        except Exception:
            return 0.5


# ══════════════════════════════════════════════════════════════════
#  Monte Carlo Engine
# ══════════════════════════════════════════════════════════════════

class MonteCarloEngine:
    """محرك Monte Carlo – يولد 1000 سيناريو عشوائي"""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def run_monte_carlo(
        self,
        trades:          List[Trade],
        simulations:     int   = 1000,
        initial_capital: float = 10_000.0,
    ) -> MonteCarloResult:
        """
        يشغّل محاكاة Monte Carlo عن طريق تبديل ترتيب الصفقات.

        Args:
            trades:          قائمة الصفقات التاريخية
            simulations:     عدد التجارب
            initial_capital: رأس المال الابتدائي

        Returns:
            MonteCarloResult مع كل الإحصاءات
        """
        result = MonteCarloResult(simulations=simulations)
        if not trades or simulations <= 0:
            return result

        pnls = [t.pnl for t in trades]
        n    = len(pnls)

        all_returns:   List[float] = []
        all_drawdowns: List[float] = []
        positive_runs: int         = 0

        logger.info(f"[MonteCarlo] بدء {simulations} محاكاة | {n} صفقة لكل تجربة")

        for sim_i in range(simulations):
            # ── خلط عشوائي للصفقات (Bootstrap Sampling مع استبدال) ──
            sim_pnls = random.choices(pnls, k=n)

            # ── بناء equity curve ──
            equity = _build_equity_curve(initial_capital, sim_pnls)
            final_return = equity[-1] - initial_capital

            # ── Max Drawdown لهذه التجربة ──
            dd, _ = _max_drawdown(equity)

            all_returns.append(final_return)
            all_drawdowns.append(dd)
            if final_return > 0:
                positive_runs += 1

            if (sim_i + 1) % 200 == 0:
                logger.info(f"[MonteCarlo]  {sim_i+1}/{simulations} محاكاة مكتملة")

        # ── حساب الإحصاءات ──
        result.all_returns    = all_returns
        result.all_drawdowns  = all_drawdowns
        result.success_probability = positive_runs / simulations
        result.avg_return     = _mean(all_returns)
        result.median_return  = _percentile(all_returns, 50)
        result.best_case      = _percentile(all_returns, 95)
        result.worst_case     = _percentile(all_returns, 5)
        result.avg_max_drawdown = _mean(all_drawdowns)
        result.worst_drawdown = _percentile(all_drawdowns, 95)

        # ── Value at Risk (95%) ──
        # VaR = potential loss → max(0, -p5). If p5 > 0, no loss at this confidence.
        p5_return      = _percentile(all_returns, 5)
        result.var_95  = max(0.0, -p5_return)
        # ── Conditional VaR (avg of worst 5%) ──
        tail_threshold = p5_return
        tail_losses    = [r for r in all_returns if r <= tail_threshold]
        if tail_losses:
            tail_mean      = _mean(tail_losses)
            result.cvar_95 = max(0.0, -tail_mean)
        else:
            result.cvar_95 = result.var_95

        # ── Percentiles ──
        result.percentiles = {
            "p5":  _percentile(all_returns, 5),
            "p10": _percentile(all_returns, 10),
            "p25": _percentile(all_returns, 25),
            "p50": _percentile(all_returns, 50),
            "p75": _percentile(all_returns, 75),
            "p90": _percentile(all_returns, 90),
            "p95": _percentile(all_returns, 95),
        }

        logger.info(
            f"[MonteCarlo] اكتمل | نجاح={result.success_probability:.1%} | "
            f"متوسط={result.avg_return:+.2f} | أسوأ={result.worst_case:+.2f}"
        )
        return result

    @staticmethod
    def bell_curve_summary(mc: MonteCarloResult, bins: int = 10) -> str:
        """رسم bell curve نصي للتوزيع"""
        if not mc.all_returns:
            return "(لا بيانات)"

        data = sorted(mc.all_returns)
        min_v, max_v = data[0], data[-1]
        if max_v == min_v:
            return "(توزيع ثابت)"

        step  = (max_v - min_v) / bins
        buckets: List[int] = [0] * bins

        for val in data:
            idx = min(int((val - min_v) / step), bins - 1)
            buckets[idx] += 1

        max_count = max(buckets)
        bar_max   = 30
        lines     = ["\n  [توزيع Monte Carlo – Bell Curve]"]
        lines.append(f"  {'Range':>12}  {'Count':>6}  Chart")
        lines.append("  " + "-" * 55)

        for i, cnt in enumerate(buckets):
            lo = min_v + i * step
            hi = lo + step
            bar = "#" * int(cnt / max_count * bar_max)
            lines.append(f"  {lo:+9.1f}→{hi:+9.1f}  {cnt:>6}  {bar}")

        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
#  Walk-Forward Analysis
# ══════════════════════════════════════════════════════════════════

class WalkForwardAnalyzer:
    """
    Walk-Forward Analysis:
      يقسم البيانات لنوافذ متدرجة
      يقارن أداء In-Sample (تدريب) vs Out-of-Sample (اختبار)
      يكتشف Overfitting
    """

    def walk_forward_analysis(
        self,
        trades:          List[Trade],
        n_windows:       int   = 5,
        train_pct:       float = 0.7,
        initial_capital: float = 10_000.0,
    ) -> WalkForwardResult:
        """
        يجري Walk-Forward Analysis على قائمة الصفقات.

        Args:
            trades:          الصفقات المرتبة زمنياً
            n_windows:       عدد النوافذ
            train_pct:       نسبة التدريب (0.7 = 70%)
            initial_capital: رأس المال

        Returns:
            WalkForwardResult
        """
        result = WalkForwardResult(windows=n_windows)

        if len(trades) < n_windows * 4:
            result.recommendation = "غير كافٍ – يحتاج المزيد من الصفقات للتحليل"
            return result

        # ── تقسيم الصفقات إلى نوافذ ──
        window_size = len(trades) // n_windows
        calc        = MetricsCalculator()
        periods     = []

        is_returns:  List[float] = []   # In-Sample
        oos_returns: List[float] = []   # Out-of-Sample

        for i in range(n_windows):
            start  = i * window_size
            end    = start + window_size
            window = trades[start:end]

            split  = int(len(window) * train_pct)
            train  = window[:split]
            test   = window[split:]

            if not train or not test:
                continue

            is_m  = calc.calculate(train, initial_capital)
            oos_m = calc.calculate(test,  initial_capital)

            is_ret  = is_m.total_return_pct
            oos_ret = oos_m.total_return_pct

            is_returns.append(is_ret)
            oos_returns.append(oos_ret)

            period = {
                "window":            i + 1,
                "trade_range":       f"{start}–{end}",
                "train_trades":      len(train),
                "test_trades":       len(test),
                "in_sample_return":  round(is_ret * 100, 2),
                "out_sample_return": round(oos_ret * 100, 2),
                "efficiency":        round(oos_ret / is_ret, 3) if is_ret != 0 else 0.0,
            }
            periods.append(period)

        result.periods = periods

        if not is_returns:
            return result

        result.in_sample_return  = _mean(is_returns)
        result.out_sample_return = _mean(oos_returns)

        # ── Efficiency Ratio (out/in) ──
        if result.in_sample_return != 0:
            result.efficiency_ratio = result.out_sample_return / result.in_sample_return
        else:
            result.efficiency_ratio = 0.0

        # ── Overfitting Score & Detection ──
        result.overfit_score, result.is_overfit = self.detect_overfitting(
            is_returns, oos_returns
        )

        # ── التوصية ──
        result.recommendation = self._generate_recommendation(result)

        return result

    @staticmethod
    def detect_overfitting(
        in_sample:  List[float],
        out_sample: List[float],
    ) -> Tuple[float, bool]:
        """
        يكتشف Overfitting بمقارنة In-Sample vs Out-of-Sample.

        المنطق:
          - إذا IS جيد جداً لكن OOS سيئ → Overfit
          - نحسب: overfit_score = (IS_return - OOS_return) / IS_return
          - إذا > 0.5 → Overfit مشتبه به

        Returns:
            (overfit_score, is_overfit)
        """
        if not in_sample or not out_sample:
            return 0.0, False

        avg_is  = _mean(in_sample)
        avg_oos = _mean(out_sample)

        if avg_is <= 0:
            # استراتيجية خاسرة حتى في التدريب
            return 0.0, False

        overfit_score = (avg_is - avg_oos) / avg_is if avg_is != 0 else 0.0
        overfit_score = max(min(overfit_score, 1.0), 0.0)
        is_overfit    = overfit_score > 0.5

        return overfit_score, is_overfit

    @staticmethod
    def _generate_recommendation(result: WalkForwardResult) -> str:
        eff = result.efficiency_ratio
        oos = result.out_sample_return

        if result.is_overfit:
            return (
                f"تحذير: Overfitting مرتفع ({result.overfit_score:.0%}) – "
                "الاستراتيجية محسّنة للبيانات التاريخية ولن تعمل جيداً في المستقبل. "
                "يُنصح بتبسيط النموذج وتقليل المعاملات."
            )
        if eff >= 0.8:
            return (
                f"ممتاز: الاستراتيجية متسقة (كفاءة {eff:.0%}) – "
                "النتائج خارج العينة قريبة من نتائج التدريب."
            )
        if eff >= 0.5:
            return (
                f"جيد: كفاءة {eff:.0%} – "
                "الاستراتيجية مقبولة لكن يمكن تحسينها."
            )
        if oos < 0:
            return (
                "تحذير: الاستراتيجية خاسرة خارج العينة – "
                "لا تُنشر في الإنتاج بدون مراجعة شاملة."
            )
        return f"مقبول: كفاءة {eff:.0%} – راجع الاستراتيجية قبل النشر."


# ══════════════════════════════════════════════════════════════════
#  Main BacktestEngine
# ══════════════════════════════════════════════════════════════════

class BacktestEngine:
    """
    المحرك الرئيسي للـ Backtesting المتقدم.

    الاستخدام:
        engine  = BacktestEngine()
        trades  = engine.generate_sample_trades(200)
        metrics = engine.calculate_advanced_metrics(trades)
        mc      = engine.run_monte_carlo(trades, simulations=1000)
        wf      = engine.walk_forward_analysis(trades)
    """

    RESULTS_FILE = "backtest_results.json"

    def __init__(self, initial_capital: float = 10_000.0, seed: Optional[int] = 42):
        self.initial_capital = initial_capital
        self.calc  = MetricsCalculator()
        self.mc    = MonteCarloEngine(seed=seed)
        self.wf    = WalkForwardAnalyzer()
        logger.info(f"BacktestEngine جاهز | رأس المال: ${initial_capital:,.0f}")

    # ─── توليد صفقات تجريبية ────────────────────────────────────────
    def generate_sample_trades(
        self,
        n:          int   = 200,
        win_rate:   float = 0.55,
        avg_win:    float = 150.0,
        avg_loss:   float = -80.0,
        volatility: float = 0.3,
    ) -> List[Trade]:
        """يولد صفقات تجريبية واقعية"""
        trades = []
        base_date = datetime(2023, 1, 1)
        symbols = ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD", "USDJPY"]

        for i in range(n):
            is_win   = random.random() < win_rate
            base_pnl = avg_win if is_win else avg_loss
            noise    = random.gauss(0, abs(base_pnl) * volatility)
            pnl      = base_pnl + noise

            entry_date = base_date + timedelta(hours=i * random.uniform(6, 24))
            exit_date  = entry_date + timedelta(hours=random.uniform(1, 48))
            entry_px   = random.uniform(1.05, 1.35)
            direction  = random.choice(["long", "short"])
            pnl_pct    = pnl / self.initial_capital

            trades.append(Trade(
                entry_date=  entry_date.isoformat(),
                exit_date=   exit_date.isoformat(),
                symbol=      random.choice(symbols),
                direction=   direction,
                entry_price= entry_px,
                exit_price=  entry_px + (pnl / 10000),
                size=        random.uniform(0.1, 1.0),
                pnl=         round(pnl, 2),
                pnl_pct=     round(pnl_pct, 5),
                duration_h=  round((exit_date - entry_date).seconds / 3600, 1),
                max_adverse= round(abs(pnl) * random.uniform(0.2, 0.5), 2),
                max_favored= round(abs(pnl) * random.uniform(1.0, 2.0), 2),
            ))

        logger.info(f"تم توليد {n} صفقة تجريبية")
        return trades

    # ─── الدوال الرئيسية ─────────────────────────────────────────────

    def calculate_advanced_metrics(self, trades: List[Trade]) -> AdvancedMetrics:
        """يحسب كل المقاييس المتقدمة"""
        return self.calc.calculate(trades, self.initial_capital)

    def run_monte_carlo(
        self,
        trades:      List[Trade],
        simulations: int = 1000,
    ) -> MonteCarloResult:
        """يشغّل محاكاة Monte Carlo"""
        return self.mc.run_monte_carlo(trades, simulations, self.initial_capital)

    def walk_forward_analysis(
        self,
        trades:    List[Trade],
        n_windows: int   = 5,
        train_pct: float = 0.7,
    ) -> WalkForwardResult:
        """يجري Walk-Forward Analysis"""
        return self.wf.walk_forward_analysis(trades, n_windows, train_pct, self.initial_capital)

    def detect_overfitting(
        self,
        in_sample:  List[float],
        out_sample: List[float],
    ) -> Tuple[float, bool]:
        """يكتشف Overfitting مباشرة"""
        return self.wf.detect_overfitting(in_sample, out_sample)

    # ─── تقرير شامل ──────────────────────────────────────────────────
    def full_report(
        self,
        trades:      List[Trade],
        simulations: int = 1000,
        n_windows:   int = 5,
    ) -> Dict[str, Any]:
        """
        يولد تقريراً شاملاً يجمع:
          - Advanced Metrics
          - Monte Carlo
          - Walk-Forward Analysis
        """
        logger.info("= بدء التقرير الشامل =")

        metrics = self.calculate_advanced_metrics(trades)
        mc      = self.run_monte_carlo(trades, simulations)
        wf      = self.walk_forward_analysis(trades, n_windows)

        report = {
            "generated_at":    datetime.utcnow().isoformat(),
            "initial_capital": self.initial_capital,
            "total_trades":    len(trades),
            "metrics":         asdict(metrics),
            "monte_carlo": {
                "simulations":         mc.simulations,
                "success_probability": mc.success_probability,
                "avg_return":          mc.avg_return,
                "median_return":       mc.median_return,
                "best_case_95":        mc.best_case,
                "worst_case_5":        mc.worst_case,
                "avg_max_drawdown":    mc.avg_max_drawdown,
                "worst_drawdown_95":   mc.worst_drawdown,
                "var_95":              mc.var_95,
                "cvar_95":             mc.cvar_95,
                "percentiles":         mc.percentiles,
            },
            "walk_forward": {
                "windows":              wf.windows,
                "in_sample_return":     wf.in_sample_return,
                "out_sample_return":    wf.out_sample_return,
                "efficiency_ratio":     wf.efficiency_ratio,
                "is_overfit":           wf.is_overfit,
                "overfit_score":        wf.overfit_score,
                "recommendation":       wf.recommendation,
                "periods":              wf.periods,
            },
            "bell_curve": self.mc.bell_curve_summary(mc),
        }

        # حفظ النتائج
        try:
            with open(self.RESULTS_FILE, "w", encoding="utf-8") as f:
                # لا نحفظ all_returns كاملاً (كبيرة)
                save_report = {k: v for k, v in report.items() if k != "bell_curve"}
                json.dump(save_report, f, ensure_ascii=False, indent=2)
            logger.info(f"النتائج محفوظة في {self.RESULTS_FILE}")
        except Exception as exc:
            logger.warning(f"خطأ في الحفظ: {exc}")

        return report


# ══════════════════════════════════════════════════════════════════
#  Singleton
# ══════════════════════════════════════════════════════════════════
backtest_engine = BacktestEngine()


# ══════════════════════════════════════════════════════════════════
#  Self-Test
# ══════════════════════════════════════════════════════════════════

def _print_section(title: str, width: int = 60):
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")

def _fmt(val: float, pct: bool = False, dollar: bool = False) -> str:
    if dollar:
        return f"${val:+,.2f}"
    if pct:
        return f"{val*100:+.2f}%"
    return f"{val:.4f}"


if __name__ == "__main__":

    print("\n" + "=" * 65)
    print("  Advanced Backtesting Engine – VisionTrader AI")
    print("  Full Test Suite")
    print("=" * 65)

    engine = BacktestEngine(initial_capital=10_000.0, seed=42)

    # ══════════════════════════════════════════════════════════════
    # TEST 1: توليد وحساب المقاييس المتقدمة
    # ══════════════════════════════════════════════════════════════
    _print_section("TEST 1: Advanced Metrics (200 trades)")

    trades = engine.generate_sample_trades(n=200, win_rate=0.56, avg_win=150, avg_loss=-80)
    m = engine.calculate_advanced_metrics(trades)

    print(f"\n  [Returns]")
    print(f"   Total Return       : {_fmt(m.total_return, dollar=True)}")
    print(f"   Return %           : {_fmt(m.total_return_pct, pct=True)}")
    print(f"   Annualized Return  : {_fmt(m.annualized_return, pct=True)}")
    print(f"   CAGR               : {_fmt(m.cagr, pct=True)}")

    print(f"\n  [Trade Stats]")
    print(f"   Total Trades       : {m.total_trades}")
    print(f"   Win Rate           : {m.win_rate*100:.1f}%")
    print(f"   Avg Win            : {_fmt(m.avg_win, dollar=True)}")
    print(f"   Avg Loss           : {_fmt(m.avg_loss, dollar=True)}")
    print(f"   Profit Factor      : {m.profit_factor:.2f}")
    print(f"   Payoff Ratio       : {m.payoff_ratio:.2f}")
    print(f"   Expectancy/trade   : {_fmt(m.expectancy, dollar=True)}")

    print(f"\n  [Risk Metrics]")
    print(f"   Sharpe Ratio       : {m.sharpe_ratio:.3f}")
    print(f"   Sortino Ratio      : {m.sortino_ratio:.3f}")
    print(f"   Calmar Ratio       : {m.calmar_ratio:.3f}")
    print(f"   Max Drawdown       : {_fmt(m.max_drawdown, dollar=True)}")
    print(f"   Max Drawdown %     : {m.max_drawdown_pct*100:.2f}%")
    print(f"   Avg Drawdown       : {_fmt(m.avg_drawdown, dollar=True)}")
    print(f"   Recovery Factor    : {m.recovery_factor:.2f}x")
    print(f"   Ulcer Index        : {m.ulcer_index:.4f}")
    print(f"   Risk of Ruin       : {m.risk_of_ruin*100:.2f}%")

    print(f"\n  [Streak Analysis]")
    print(f"   Max Win Streak     : {m.max_win_streak}")
    print(f"   Max Loss Streak    : {m.max_loss_streak}")
    print(f"   Current Streak     : {m.current_streak} ({m.streak_type})")

    # تحقق أساسي
    t1_ok = (
        m.total_trades == 200
        and 0 < m.win_rate < 1
        and m.sharpe_ratio != 0
        and m.max_drawdown > 0
        and 0 <= m.risk_of_ruin <= 1
    )
    print(f"\n  [RESULT] TEST 1: {'PASS' if t1_ok else 'FAIL'}")

    # ══════════════════════════════════════════════════════════════
    # TEST 2: Monte Carlo Simulation
    # ══════════════════════════════════════════════════════════════
    _print_section("TEST 2: Monte Carlo Simulation (1000 runs)")

    mc = engine.run_monte_carlo(trades, simulations=1000)

    print(f"\n  [Monte Carlo Results]")
    print(f"   Simulations        : {mc.simulations:,}")
    print(f"   Success Prob       : {mc.success_probability*100:.1f}%")
    print(f"   Avg Return         : {_fmt(mc.avg_return, dollar=True)}")
    print(f"   Median Return      : {_fmt(mc.median_return, dollar=True)}")
    print(f"   Best Case  (p95)   : {_fmt(mc.best_case, dollar=True)}")
    print(f"   Worst Case (p5)    : {_fmt(mc.worst_case, dollar=True)}")
    print(f"   Avg Max Drawdown   : {_fmt(mc.avg_max_drawdown, dollar=True)}")
    print(f"   Worst DD (p95)     : {_fmt(mc.worst_drawdown, dollar=True)}")
    print(f"   VaR 95%            : {_fmt(mc.var_95, dollar=True)}")
    print(f"   CVaR 95%           : {_fmt(mc.cvar_95, dollar=True)}")

    print(f"\n  [Percentile Distribution]")
    for k, v in mc.percentiles.items():
        bar = "#" * int(max(0, (v + abs(mc.worst_case)) / (mc.best_case - mc.worst_case + 1) * 20))
        print(f"   {k:>4}: {v:+9.2f}  {bar}")

    # Bell Curve
    bell = engine.mc.bell_curve_summary(mc, bins=8)
    print(bell)

    t2_ok = (
        mc.simulations == 1000
        and 0 < mc.success_probability <= 1.0   # 100% success is valid for strong strategies
        and mc.worst_case < mc.best_case
        and mc.var_95 >= 0                       # VaR always >= 0
        and mc.cvar_95 >= 0                      # CVaR always >= 0
        and len(mc.percentiles) == 7
    )
    print(f"\n  [RESULT] TEST 2: {'PASS' if t2_ok else 'FAIL'}")

    # ══════════════════════════════════════════════════════════════
    # TEST 3: Walk-Forward Analysis
    # ══════════════════════════════════════════════════════════════
    _print_section("TEST 3: Walk-Forward Analysis (5 windows)")

    wf = engine.walk_forward_analysis(trades, n_windows=5, train_pct=0.7)

    print(f"\n  [Walk-Forward Results]")
    print(f"   Windows            : {wf.windows}")
    print(f"   In-Sample Avg      : {wf.in_sample_return*100:+.2f}%")
    print(f"   Out-Sample Avg     : {wf.out_sample_return*100:+.2f}%")
    print(f"   Efficiency Ratio   : {wf.efficiency_ratio:.3f}")
    print(f"   Is Overfit         : {'YES' if wf.is_overfit else 'NO'}")
    print(f"   Overfit Score      : {wf.overfit_score*100:.1f}%")
    print(f"   Recommendation     : {wf.recommendation[:70]}")

    print(f"\n  [Window Details]")
    print(f"   {'Win':>4} {'IS%':>8} {'OOS%':>8} {'Eff':>7} {'Trades'}  ")
    print(f"   {'-'*40}")
    for p in wf.periods:
        print(
            f"   {p['window']:>4} "
            f"{p['in_sample_return']:>+7.2f}% "
            f"{p['out_sample_return']:>+7.2f}% "
            f"{p['efficiency']:>7.3f} "
            f"({p['train_trades']}+{p['test_trades']})"
        )

    t3_ok = (
        len(wf.periods) > 0
        and isinstance(wf.is_overfit, bool)
        and 0 <= wf.overfit_score <= 1
        and wf.recommendation != ""
    )
    print(f"\n  [RESULT] TEST 3: {'PASS' if t3_ok else 'FAIL'}")

    # ══════════════════════════════════════════════════════════════
    # TEST 4: Overfitting Detection
    # ══════════════════════════════════════════════════════════════
    _print_section("TEST 4: Overfitting Detection")

    # سيناريو Overfit واضح
    overfit_score, is_overfit = engine.detect_overfitting(
        in_sample=  [0.30, 0.28, 0.32, 0.29],   # IS جيد جداً
        out_sample= [0.02, -0.05, 0.01, -0.03],  # OOS سيئ
    )
    t4a_ok = is_overfit
    print(f"\n  Scenario A (clear overfit):")
    print(f"   Overfit Score: {overfit_score*100:.1f}%  |  Is Overfit: {is_overfit}")
    print(f"   Result: {'PASS (detected)' if t4a_ok else 'FAIL (missed)'}")

    # سيناريو طبيعي
    overfit_score2, is_overfit2 = engine.detect_overfitting(
        in_sample=  [0.10, 0.12, 0.09, 0.11],
        out_sample= [0.08, 0.10, 0.07, 0.09],
    )
    t4b_ok = not is_overfit2
    print(f"\n  Scenario B (healthy strategy):")
    print(f"   Overfit Score: {overfit_score2*100:.1f}%  |  Is Overfit: {is_overfit2}")
    print(f"   Result: {'PASS (not overfit)' if t4b_ok else 'FAIL (false positive)'}")

    t4_ok = t4a_ok and t4b_ok

    # ══════════════════════════════════════════════════════════════
    # TEST 5: Full Report Generation
    # ══════════════════════════════════════════════════════════════
    _print_section("TEST 5: Full Report (500 trades)")

    big_trades = engine.generate_sample_trades(n=500, win_rate=0.58)
    report = engine.full_report(big_trades, simulations=500, n_windows=5)

    t5_ok = (
        "metrics"       in report
        and "monte_carlo"   in report
        and "walk_forward"  in report
        and "bell_curve"    in report
        and os.path.exists(engine.RESULTS_FILE)
    )
    print(f"  Report keys       : {list(report.keys())}")
    print(f"  Saved to          : {engine.RESULTS_FILE}")
    print(f"  File exists       : {os.path.exists(engine.RESULTS_FILE)}")
    print(f"\n  [RESULT] TEST 5: {'PASS' if t5_ok else 'FAIL'}")

    # ══════════════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════════════
    all_tests = [t1_ok, t2_ok, t3_ok, t4_ok, t5_ok]
    n_pass    = sum(all_tests)
    all_pass  = all(all_tests)

    _print_section("FINAL SUMMARY")
    for i, (ok, name) in enumerate(zip(all_tests, [
        "Advanced Metrics",
        "Monte Carlo",
        "Walk-Forward",
        "Overfitting Detection",
        "Full Report",
    ]), 1):
        print(f"  TEST {i} [{name:22s}]: {'PASS' if ok else 'FAIL'}")

    print(f"\n  Total: {n_pass}/5 passed")
    status = "ALL TESTS PASSED" if all_pass else f"{5-n_pass} TEST(S) FAILED"
    print(f"  [{status}]")
    print("=" * 65 + "\n")

    sys.exit(0 if all_pass else 1)
