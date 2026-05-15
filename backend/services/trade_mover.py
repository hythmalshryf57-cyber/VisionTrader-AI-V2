import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class TradeMoverService:
    def __init__(self):
        self.reverse_keywords = [
            "choch", "تشوخ", "خروج", "هيكل", "اختراق هيكل", "كسر هيكل",
            "ابتلاع", "engulfing", "reversal", "reverse", "عوده", "انعكاس"
        ]
        self.active_trades = {}  # Track active trades for dynamic adjustments

    def _parse_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            text = value.replace(',', '.').strip()
            match = re.search(r"-?\d+(?:\.\d+)?", text)
            if match:
                try:
                    return float(match.group(0))
                except ValueError:
                    return None
        return None

    def _collect_reasons(self, analysis_data: Dict[str, Any]) -> str:
        reasons = []
        if isinstance(analysis_data.get('reason'), str):
            reasons.append(analysis_data['reason'])

        details = analysis_data.get('details')
        if isinstance(details, list):
            for item in details:
                if isinstance(item, dict):
                    for field in ('reason', 'analysis', 'comment', 'description'):
                        value = item.get(field)
                        if isinstance(value, str):
                            reasons.append(value)

        extra = analysis_data.get('notes')
        if isinstance(extra, str):
            reasons.append(extra)

        return ' '.join(reasons)

    def _contains_reverse_signal(self, text: str) -> bool:
        lower = text.lower()
        return any(keyword in lower for keyword in self.reverse_keywords)

    def _build_trade_context(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        recommendation = str(analysis_data.get('recommendation') or '').strip()
        entry = self._parse_float(analysis_data.get('entry'))
        sl = self._parse_float(analysis_data.get('sl'))
        tp = self._parse_float(analysis_data.get('tp'))
        return {
            'recommendation': recommendation,
            'entry_price': entry,
            'stop_loss': sl,
            'take_profit': tp,
            'reason_text': self._collect_reasons(analysis_data)
        }

    def _is_buy(self, recommendation: str) -> bool:
        return recommendation.startswith('شراء')

    def _is_sell(self, recommendation: str) -> bool:
        return recommendation.startswith('بيع')

    def _calculate_trailing_stop(self, current_price: float, entry_price: float, stop_loss: float, is_buy: bool) -> Optional[float]:
        if stop_loss is None or entry_price is None:
            return None

        distance = abs(entry_price - stop_loss)
        buffer = max(distance * 0.25, abs(current_price) * 0.0005)

        if is_buy:
            new_stop = current_price - buffer
            if new_stop <= stop_loss or new_stop <= entry_price:
                return None
        else:
            new_stop = current_price + buffer
            if new_stop >= stop_loss or new_stop >= entry_price:
                return None

        return round(new_stop, 5)

    def suggest(self, analysis_data: Dict[str, Any], current_price: Optional[float] = None, trade_id: Optional[str] = None) -> Dict[str, Any]:
        context = self._build_trade_context(analysis_data)
        recommendation = context['recommendation']
        entry_price = context['entry_price']
        stop_loss = context['stop_loss']
        take_profit = context['take_profit']
        reason_text = context['reason_text']

        # Check for reverse signals
        if self._contains_reverse_signal(reason_text):
            return {
                'action': 'exit',
                'reason': 'تم اكتشاف إشارة عكسية قوية في التحليل، يفضل الخروج المبكر.',
                'suggested_stop': stop_loss,
                'entry_price': entry_price,
                'take_profit': take_profit,
                'recommendation': recommendation
            }

        # Automatic stop loss management
        stop_action = self._manage_stop_loss(current_price, entry_price, stop_loss, recommendation, trade_id)
        if stop_action:
            return stop_action

        # Dynamic target adjustments
        target_action = self._adjust_targets(current_price, entry_price, take_profit, recommendation, trade_id)
        if target_action:
            return target_action

        # Check for take profit hit
        if current_price is not None and entry_price is not None and take_profit is not None:
            if self._is_buy(recommendation) and current_price >= take_profit:
                return {
                    'action': 'breakeven',
                    'reason': 'السعر وصل إلى الهدف الأول، اقترح نقل الوقف إلى نقطة الدخول.',
                    'suggested_stop': entry_price,
                    'entry_price': entry_price,
                    'take_profit': take_profit,
                    'recommendation': recommendation
                }
            if self._is_sell(recommendation) and current_price <= take_profit:
                return {
                    'action': 'breakeven',
                    'reason': 'السعر وصل إلى الهدف الأول، اقترح نقل الوقف إلى نقطة الدخول.',
                    'suggested_stop': entry_price,
                    'entry_price': entry_price,
                    'take_profit': take_profit,
                    'recommendation': recommendation
                }

        # Trailing stop suggestion
        if current_price is not None and entry_price is not None and stop_loss is not None:
            if self._is_buy(recommendation):
                trailing_stop = self._calculate_trailing_stop(current_price, entry_price, stop_loss, True)
                if trailing_stop is not None:
                    return {
                        'action': 'move_sl',
                        'reason': 'السعر في صالحك، اقترح تحريك الوقف كوقف متدرج خلف القمة الجديدة.',
                        'suggested_stop': trailing_stop,
                        'entry_price': entry_price,
                        'take_profit': take_profit,
                        'recommendation': recommendation
                    }
            if self._is_sell(recommendation):
                trailing_stop = self._calculate_trailing_stop(current_price, entry_price, stop_loss, False)
                if trailing_stop is not None:
                    return {
                        'action': 'move_sl',
                        'reason': 'السعر في صالحك، اقترح تحريك الوقف كوقف متدرج خلف القاع الجديد.',
                        'suggested_stop': trailing_stop,
                        'entry_price': entry_price,
                        'take_profit': take_profit,
                        'recommendation': recommendation
                    }

        return {
            'action': 'hold',
            'reason': 'لا توجد إشارات كافية لتحريك الوقف أو للخروج الآن. راقب أداء الصفقة.',
            'suggested_stop': stop_loss,
            'entry_price': entry_price,
            'take_profit': take_profit,
            'recommendation': recommendation
        }

    def _manage_stop_loss(self, current_price: Optional[float], entry_price: Optional[float], stop_loss: Optional[float], recommendation: str, trade_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Automatic stop loss management based on profit levels."""
        if not all([current_price, entry_price, stop_loss]):
            return None

        is_buy = self._is_buy(recommendation)
        profit_points = abs(current_price - entry_price)

        # Rule 1: Move to Breakeven at +30 points
        if profit_points >= 30:
            if is_buy and stop_loss < entry_price:
                logger.info(f"تم نقل الوقف إلى Breakeven عند {entry_price}")
                return {
                    'action': 'move_sl_to_breakeven',
                    'reason': 'الربح وصل 30 نقطة، نقل الوقف إلى نقطة الدخول.',
                    'suggested_stop': entry_price,
                    'entry_price': entry_price,
                    'take_profit': None,
                    'recommendation': recommendation
                }
            elif not is_buy and stop_loss > entry_price:
                logger.info(f"تم نقل الوقف إلى Breakeven عند {entry_price}")
                return {
                    'action': 'move_sl_to_breakeven',
                    'reason': 'الربح وصل 30 نقطة، نقل الوقف إلى نقطة الدخول.',
                    'suggested_stop': entry_price,
                    'entry_price': entry_price,
                    'take_profit': None,
                    'recommendation': recommendation
                }

        # Rule 2: Activate Trailing Stop at +50 points
        if profit_points >= 50:
            trailing_stop = self._calculate_trailing_stop(current_price, entry_price, stop_loss, is_buy)
            if trailing_stop is not None:
                logger.info("Trailing Stop مفعّل")
                return {
                    'action': 'activate_trailing_stop',
                    'reason': 'الربح وصل 50 نقطة، تفعيل الوقف المتدرج.',
                    'suggested_stop': trailing_stop,
                    'entry_price': entry_price,
                    'take_profit': None,
                    'recommendation': recommendation
                }

        return None

    def _adjust_targets(self, current_price: Optional[float], entry_price: Optional[float], take_profit: Optional[float], recommendation: str, trade_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Dynamic target adjustments based on momentum."""
        if not all([current_price, entry_price, take_profit]):
            return None

        is_buy = self._is_buy(recommendation)
        profit_points = abs(current_price - entry_price)

        # Track trade state
        if trade_id:
            if trade_id not in self.active_trades:
                self.active_trades[trade_id] = {
                    'entry_price': entry_price,
                    'initial_tp': take_profit,
                    'tp1_hit': False,
                    'momentum': 'neutral'
                }

            trade_state = self.active_trades[trade_id]

            # Check if TP1 was hit
            if not trade_state['tp1_hit']:
                if (is_buy and current_price >= take_profit) or (not is_buy and current_price <= take_profit):
                    trade_state['tp1_hit'] = True
                    logger.info(f"تم الوصول إلى TP1، نقل الوقف إلى الدخول للكمية المتبقية")
                    return {
                        'action': 'move_sl_after_tp1',
                        'reason': 'تم الوصول إلى الهدف الأول، نقل الوقف إلى نقطة الدخول للكمية المتبقية.',
                        'suggested_stop': entry_price,
                        'entry_price': entry_price,
                        'take_profit': take_profit,
                        'recommendation': recommendation
                    }

            # Adjust targets based on momentum
            current_momentum = self._assess_momentum(current_price, trade_state)

            if current_momentum != trade_state['momentum']:
                trade_state['momentum'] = current_momentum

                if current_momentum == 'increasing':
                    # Raise TP2 and TP3
                    new_tp2 = take_profit + (abs(take_profit - entry_price) * 0.2)
                    logger.info(f"تم رفع TP2 من {take_profit} إلى {new_tp2} بسبب زيادة الزخم")
                    return {
                        'action': 'raise_targets',
                        'reason': 'زيادة الزخم، رفع الأهداف.',
                        'new_tp2': round(new_tp2, 5),
                        'entry_price': entry_price,
                        'take_profit': take_profit,
                        'recommendation': recommendation
                    }

                elif current_momentum == 'decreasing':
                    # Lower TP2 and TP3 or close early
                    new_tp2 = take_profit - (abs(take_profit - entry_price) * 0.1)
                    if profit_points < 20:  # Close early if profit is small
                        logger.info("ضعف الزخم مع ربح صغير، إغلاق مبكر")
                        return {
                            'action': 'close_early',
                            'reason': 'ضعف الزخم مع ربح صغير، إغلاق مبكر للحفاظ على الربح.',
                            'entry_price': entry_price,
                            'take_profit': take_profit,
                            'recommendation': recommendation
                        }
                    else:
                        logger.info(f"تم خفض TP2 من {take_profit} إلى {new_tp2} بسبب ضعف الزخم")
                        return {
                            'action': 'lower_targets',
                            'reason': 'ضعف الزخم، خفض الأهداف.',
                            'new_tp2': round(new_tp2, 5),
                            'entry_price': entry_price,
                            'take_profit': take_profit,
                            'recommendation': recommendation
                        }

        return None

    def _assess_momentum(self, current_price: float, trade_state: Dict[str, Any]) -> str:
        """Assess current momentum based on price movement."""
        # Simple momentum assessment - can be enhanced with more indicators
        entry_price = trade_state['entry_price']
        last_price = trade_state.get('last_price', entry_price)
        price_change = abs(current_price - entry_price)
        last_change = abs(last_price - entry_price)

        # Update last price
        trade_state['last_price'] = current_price

        if price_change > last_change * 1.05:  # 5% increase in profit
            return 'increasing'
        elif price_change < last_change * 0.95:  # 5% decrease in profit
            return 'decreasing'
        else:
            return 'neutral'

    def add_liquidity_target(self, trade_id: str, liquidity_level: float) -> Dict[str, Any]:
        """Add a new target based on detected liquidity."""
        if trade_id in self.active_trades:
            logger.info(f"تم إضافة هدف جديد عند {liquidity_level} بسبب اكتشاف سيولة")
            return {
                'action': 'add_target',
                'reason': 'تم اكتشاف مستوى سيولة جديد، إضافة هدف إضافي.',
                'new_target': round(liquidity_level, 5),
                'entry_price': self.active_trades[trade_id]['entry_price'],
                'take_profit': self.active_trades[trade_id]['initial_tp']
            }
        return {'action': 'no_action'}

trade_mover_service = TradeMoverService()
