import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_FILE = Path(__file__).resolve().parent.parent / "cancelled_trades.json"


class CancelledTradeMemory:
    """Simple Cancelled Trade Memory service.

    - يسجل التوصيات التي أُلغيت مع السبب
    - يحاول حساب الربح/الخسارة بأثر رجعي إذا وُجدت بيانات سعرية
    - يحفظ إلى JSON ويعد ملخصات للتعلّم
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.lock = threading.Lock()
        self.storage = Path(storage_path) if storage_path else _FILE
        self._load()

    def _load(self):
        try:
            if self.storage.exists():
                with open(self.storage, 'r', encoding='utf-8') as f:
                    self.trades: List[Dict[str, Any]] = json.load(f)
            else:
                self.trades = []
        except Exception:
            self.trades = []

    def _save(self):
        try:
            with self.lock:
                with open(self.storage, 'w', encoding='utf-8') as f:
                    json.dump(self.trades, f, ensure_ascii=False, indent=2, default=str)
        except Exception:
            pass

    def record_cancellation(self, recommendation: Dict[str, Any], reason: str, user_id: Optional[int] = None) -> None:
        """Record a cancelled recommendation.

        recommendation: dict containing at least: market, direction ('buy'/'sell'), entry_price (optional), timestamp (optional)
        reason: free text reason for cancellation
        """
        rec = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': user_id,
            'recommendation': recommendation,
            'reason': reason,
            'analysis': None
        }
        # try quick retrospective analysis now if price history included
        try:
            analysis = self._analyze_single(recommendation)
            rec['analysis'] = analysis
        except Exception:
            rec['analysis'] = None

        self.trades.append(rec)
        # keep recent 2000 only
        if len(self.trades) > 2000:
            self.trades = self.trades[-2000:]
        self._save()

    def _analyze_single(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to compute hypothetical PnL using provided price history or simple exit assumptions.

        Expects recommendation to optionally include `price_history` (list of closes) or `entry_price` and `exit_target`.
        Returns a dict with estimated PnL, max_drawdown, best_outcome, notes.
        """
        res = {'estimated_pnl': None, 'max_drawdown': None, 'best_outcome': None, 'notes': ''}
        entry = None
        direction = None
        if not isinstance(recommendation, dict):
            res['notes'] = 'recommendation not dict'
            return res

        direction = str(recommendation.get('direction', '')).lower()
        if 'entry_price' in recommendation:
            try:
                entry = float(recommendation.get('entry_price'))
            except Exception:
                entry = None

        price_history = recommendation.get('price_history') or recommendation.get('chart_data', {}).get('closes') if isinstance(recommendation.get('chart_data'), dict) else None

        if entry is None and price_history and len(price_history) > 0:
            entry = float(price_history[0])

        if entry is None:
            res['notes'] = 'no entry price or price history'
            return res

        if price_history and len(price_history) > 1:
            closes = [float(x) for x in price_history]
            # compute pnl as change from entry to last
            last = closes[-1]
            if direction in ('sell', 'short'):
                pnl = (entry - last)
            else:
                pnl = (last - entry)
            # percent
            res['estimated_pnl'] = round(pnl, 6)
            # max drawdown relative to entry
            dd = 0.0
            if direction in ('sell', 'short'):
                highs = [float(x) for x in closes]
                worst = max(highs)
                dd = worst - entry
            else:
                lows = [float(x) for x in closes]
                worst = min(lows)
                dd = entry - worst
            res['max_drawdown'] = round(dd, 6)
            res['best_outcome'] = round(max((c - entry) if direction not in ('sell','short') else (entry - c) for c in closes), 6)
            res['notes'] = 'computed from provided price_history'
            return res

        # fallback: if exit_target present
        if 'exit_target' in recommendation:
            try:
                exit_p = float(recommendation.get('exit_target'))
                if direction in ('sell', 'short'):
                    pnl = entry - exit_p
                else:
                    pnl = exit_p - entry
                res['estimated_pnl'] = round(pnl, 6)
                res['notes'] = 'computed from entry and exit_target'
                return res
            except Exception:
                pass

        res['notes'] = 'insufficient price information to compute pnl'
        return res

    def analyze_missed_opportunities(self, min_count: int = 1) -> Dict[str, Any]:
        """Analyze cancelled trades that would have been profitable on hindsight.

        Returns aggregated stats.
        """
        wins = []
        losses = []
        unknown = []
        for t in self.trades:
            a = t.get('analysis')
            if not a or a.get('estimated_pnl') is None:
                unknown.append(t)
                continue
            pnl = float(a.get('estimated_pnl') or 0.0)
            if pnl > 0:
                wins.append(pnl)
            else:
                losses.append(pnl)

        summary = {
            'total_cancelled': len(self.trades),
            'analyzed': len(self.trades) - len(unknown),
            'missed_wins_count': len(wins),
            'missed_wins_avg': round(sum(wins) / max(1, len(wins)), 6) if wins else 0.0,
            'avoided_losses_count': len([p for p in losses if p < 0]),
            'avoided_losses_avg': round(sum(losses) / max(1, len(losses)), 6) if losses else 0.0,
            'unknown_count': len(unknown)
        }
        return summary

    def analyze_narrow_escapes(self, loss_threshold: float = 0.5) -> Dict[str, Any]:
        """Find cancellations that avoided large losses (max_drawdown > loss_threshold).
        Returns list and counts.
        """
        escapes = []
        for t in self.trades:
            a = t.get('analysis') or {}
            dd = a.get('max_drawdown')
            pnl = a.get('estimated_pnl')
            if dd is not None and abs(float(dd)) >= loss_threshold:
                escapes.append({'trade': t, 'max_drawdown': dd, 'estimated_pnl': pnl})
        return {'count': len(escapes), 'examples': escapes[:10]}

    def get_learning_summary(self) -> Dict[str, Any]:
        return {
            'total': len(self.trades),
            **self.analyze_missed_opportunities(),
            'narrow_escapes': self.analyze_narrow_escapes()
        }

    def adjust_future_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Lightweight adjustment heuristic based on memory:
        - if similar market/direction historically produced missed wins, boost confidence
        - if many narrow escapes for similar pattern, lower confidence
        Returns modified recommendation copy with `adjustment` field.
        """
        out = dict(recommendation)
        market = str(recommendation.get('market', '')).upper()
        direction = str(recommendation.get('direction', '')).lower()
        missed = 0
        missed_sum = 0.0
        escapes = 0
        for t in self.trades:
            rec = t.get('recommendation') or {}
            if str(rec.get('market','')).upper() == market and str(rec.get('direction','')).lower() == direction:
                a = t.get('analysis') or {}
                pnl = a.get('estimated_pnl')
                dd = a.get('max_drawdown')
                if pnl is not None and float(pnl) > 0:
                    missed += 1
                    missed_sum += float(pnl)
                if dd is not None and abs(float(dd)) > 0.5:
                    escapes += 1

        adjustment = 0.0
        note = []
        if missed >= 2 and (missed_sum / missed) > 0.0:
            adjustment += 0.1  # boost
            note.append(f'missed_wins={missed}')
        if escapes >= 2:
            adjustment -= 0.15
            note.append(f'narrow_escapes={escapes}')

        out['adjustment'] = round(adjustment, 3)
        out['adjustment_note'] = ';'.join(note) if note else None
        return out


# Create a module-level instance for convenience
cancelled_trade_memory = CancelledTradeMemory()
