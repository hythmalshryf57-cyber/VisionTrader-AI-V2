from typing import Optional, Dict, Any, List
import threading
import time
from datetime import datetime, timedelta

from .risk_calculator import RiskCalculator
from .performance_tracker import PerformanceTracker
from .binance_service import binance_service
from .notification_service import notification_service
from .journal_service import journal_service
import models


class TradeManagerService:
    def __init__(self):
        self.risk_calculator = RiskCalculator()
        self.performance_tracker = PerformanceTracker()
        self.active_trades = {}  # {trade_id: trade_data}
        self.monitoring_thread = None
        self.monitoring_active = False

    def _normalize_direction(self, recommendation: str) -> str:
        recommendation = str(recommendation or "").strip()
        if recommendation.startswith("شراء"):
            return "شراء"
        if recommendation.startswith("بيع"):
            return "بيع"
        return "محايد"

    def _parse_zone_value(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(',', '.'))
            except Exception:
                import re
                match = re.search(r"-?\d+(?:\.\d+)?", value.replace(',', '.'))
                if match:
                    try:
                        return float(match.group(0))
                    except Exception:
                        return None
        return None

    def _build_entry_zone(
        self,
        direction: str,
        current_price: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        context: dict,
    ) -> dict:
        support = self._parse_zone_value(context.get("support_level"))
        resistance = self._parse_zone_value(context.get("resistance_level"))
        order_block_low = self._parse_zone_value(context.get("order_block_low"))
        order_block_high = self._parse_zone_value(context.get("order_block_high"))
        fvg_low = self._parse_zone_value(context.get("fvg_low"))
        fvg_high = self._parse_zone_value(context.get("fvg_high"))

        if direction == "شراء":
            lows = [v for v in (support, order_block_low, fvg_low, stop_loss) if v is not None]
            highs = [v for v in (current_price, resistance, order_block_high, fvg_high, take_profit) if v is not None]
        else:
            lows = [v for v in (current_price, support, order_block_low, fvg_low, take_profit) if v is not None]
            highs = [v for v in (resistance, order_block_high, fvg_high, stop_loss) if v is not None]

        if lows:
            zone_low = min(lows)
        else:
            zone_low = current_price * 0.997

        if highs:
            zone_high = max(highs)
        else:
            zone_high = current_price * 1.003

        if zone_high < zone_low:
            zone_low, zone_high = min(zone_low, zone_high), max(zone_low, zone_high)

        if zone_low <= 0:
            zone_low = current_price * 0.997
        if zone_high <= 0:
            zone_high = current_price * 1.003

        if current_price < zone_low:
            zone_low = current_price * 0.995
        if current_price > zone_high:
            zone_high = current_price * 1.005

        width = max(abs(current_price) * 0.001, 0.1)
        if zone_high - zone_low < width * 0.5:
            zone_low = current_price - width
            zone_high = current_price + width

        zone_low = round(zone_low, 5)
        zone_high = round(zone_high, 5)
        entry_zone = f"{zone_low:.2f} - {zone_high:.2f}"
        return {
            "entry_zone": entry_zone,
            "entry_zone_low": zone_low,
            "entry_zone_high": zone_high,
            "entry_zone_reason": "منطقة دخول مبنية على أقرب دعم/مقاومة، كتلة أوامر أو FVG." if any((support, resistance, order_block_low, order_block_high, fvg_low, fvg_high)) else "منطقة دخول ديناميكية حول السعر الحالي."
        }

    def plan_trade(
        self,
        user_id: int,
        recommendation: str,
        current_price: Optional[float],
        stop_loss: Optional[float],
        take_profit: Optional[float],
        confidence: int = 50,
        account_balance: Optional[float] = None,
        base_risk_percent: Optional[float] = None,
        analysis_context: Optional[dict] = None,
    ) -> Dict[str, Any]:
        analysis_context = analysis_context or {}
        # الحصول على البيانات من user preferences
        from database import SessionLocal
        db = SessionLocal()
        try:
            user_prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == user_id).first()
            if user_prefs:
                if account_balance is None:
                    account_balance = user_prefs.capital
                if base_risk_percent is None:
                    base_risk_percent = user_prefs.risk_percentage
        finally:
            db.close()

        account_balance = account_balance or 10000.0
        base_risk_percent = base_risk_percent or 1.0
        demo_mode = False
        if user_prefs and getattr(user_prefs, 'demo_mode', False):
            demo_mode = True
            account_balance = float(user_prefs.demo_balance or account_balance)

        direction = self._normalize_direction(recommendation)
        if direction == "محايد":
            return {
                "status": "hold",
                "reason": "التوصية الحالية ليست صعودية أو هبوطية.",
                "confidence": confidence,
                "recommendation": recommendation,
            }

        confidence = max(0, min(100, confidence))
        adjusted_risk = self.risk_calculator.adjusted_risk(confidence, base_risk_percent)

        # منع إذا risk > 2%
        if adjusted_risk > 2.0:
            return {
                "status": "rejected",
                "reason": "المخاطرة المحسوبة أعلى من 2%",
                "confidence": confidence,
                "recommendation": recommendation,
            }

        # ضبط اللوت حسب الثقة
        lot_multiplier = 1.0
        if confidence >= 90:
            lot_multiplier = 1.0  # حجم كامل
        elif confidence >= 60:
            lot_multiplier = 0.5  # نصف
        else:
            lot_multiplier = 0.25  # ربع

        performance = self.performance_tracker.summarize_performance(user_id, lookback_days=90)

        if performance["win_rate"] < 45.0:
            adjusted_risk = round(adjusted_risk * 0.8, 2)
        if performance["max_drawdown"] > 15.0:
            adjusted_risk = round(min(adjusted_risk, 1.5), 2)

        plan = {
            "direction": direction,
            "confidence": confidence,
            "recommended_risk_percent": adjusted_risk,
            "lot_multiplier": lot_multiplier,
            "performance_summary": performance,
            "demo_mode": demo_mode,
            "risk_note": "",
            "trade_valid": False,
        }
        if demo_mode:
            plan["risk_note"] = "يتم استخدام الحساب التجريبي. الأرقام افتراضية ولا تمثل أموالاً حقيقية."

        if current_price is None or stop_loss is None:
            plan["risk_note"] = "السعر الحالي أو وقف الخسارة غير موجود."
            return plan

        trade_size = self.risk_calculator.calculate_position_size(
            account_balance=account_balance,
            entry_price=current_price,
            stop_loss=stop_loss,
            risk_percent=adjusted_risk,
        )
        # ضبط اللوت حسب الثقة
        trade_size["position_size"] *= lot_multiplier
        plan.update(trade_size)

        if not trade_size.get("valid"):
            plan["risk_note"] = trade_size.get("note", "فشل حساب حجم الصفقة.")
            return plan

        if take_profit is not None and take_profit != 0:
            reward = abs(take_profit - current_price)
            risk = abs(current_price - stop_loss)
            reward_ratio = round((reward / risk) if risk > 0 else 0.0, 2)
            plan["reward_ratio"] = reward_ratio
            if reward_ratio < 1.2:
                plan["risk_note"] = "نسبة العائد إلى المخاطرة منخفضة، يفضل تحسين الهدف أو وقف الخسارة."
            else:
                plan["risk_note"] = "نسبة العائد إلى المخاطرة مقبولة."

        if confidence < 50:
            plan["risk_note"] = "الثقة منخفضة، يفضل تقليل حجم الصفقة أو انتظار فرصة أوضح." if not plan["risk_note"] else plan["risk_note"]

        if performance["win_rate"] < 40:
            plan["risk_note"] = "أداء التداول الحالي ضعيف، قلل المخاطرة أكثر أو توقف مؤقتاً." if not plan["risk_note"] else plan["risk_note"]

        plan["trade_valid"] = True
        plan["account_balance"] = round(account_balance, 2)
        plan["entry_price"] = round(current_price, 6)
        plan["take_profit"] = round(take_profit, 6) if take_profit is not None else None
        plan["stop_loss"] = round(stop_loss, 6)
        zone_data = self._build_entry_zone(direction, current_price, stop_loss, take_profit, analysis_context)
        plan.update(zone_data)
        return plan

    def start_live_monitoring(self):
        """بدء مراقبة الصفقات الحية"""
        if self.monitoring_active:
            return
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_trades_loop, daemon=True)
        self.monitoring_thread.start()

    def stop_live_monitoring(self):
        """إيقاف مراقبة الصفقات الحية"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

    def add_active_trade(self, trade_id: str, user_id: int, market: str, direction: str,
                        entry_price: float, stop_loss: float, take_profits: List[float],
                        position_size: float, entry_time: datetime = None):
        """إضافة صفقة نشطة للتتبع"""
        if entry_time is None:
            entry_time = datetime.utcnow()

        self.active_trades[trade_id] = {
            'user_id': user_id,
            'market': market,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profits': take_profits,
            'position_size': position_size,
            'entry_time': entry_time,
            'current_price': entry_price,
            'last_update': datetime.utcnow(),
            'alerts_sent': set(),  # لتجنب تكرار التنبيهات
        }

    def remove_active_trade(self, trade_id: str):
        """إزالة صفقة من التتبع"""
        if trade_id in self.active_trades:
            del self.active_trades[trade_id]

    def get_active_trades(self, user_id: int = None) -> List[Dict[str, Any]]:
        """الحصول على الصفقات النشطة مع P&L حي"""
        trades = []
        for trade_id, trade in self.active_trades.items():
            if user_id and trade['user_id'] != user_id:
                continue

            current_price = trade.get('current_price', trade['entry_price'])
            pnl = self._calculate_pnl(trade, current_price)
            distance_to_tp1 = abs(current_price - trade['take_profits'][0]) if trade['take_profits'] else None
            distance_to_sl = abs(current_price - trade['stop_loss'])

            trades.append({
                'trade_id': trade_id,
                'market': trade['market'],
                'direction': trade['direction'],
                'entry_price': trade['entry_price'],
                'current_price': current_price,
                'stop_loss': trade['stop_loss'],
                'take_profits': trade['take_profits'],
                'position_size': trade['position_size'],
                'pnl': pnl,
                'pnl_percent': round((pnl / (trade['entry_price'] * trade['position_size'])) * 100, 2) if trade['entry_price'] * trade['position_size'] > 0 else 0,
                'duration': str(datetime.utcnow() - trade['entry_time']),
                'distance_to_tp1': distance_to_tp1,
                'distance_to_sl': distance_to_sl,
                'last_update': trade['last_update'],
            })
        return trades

    def _calculate_pnl(self, trade: Dict, current_price: float) -> float:
        """حساب الربح/الخسارة الحي"""
        entry = trade['entry_price']
        size = trade['position_size']
        if trade['direction'] == 'شراء':
            return (current_price - entry) * size
        else:
            return (entry - current_price) * size

    def _monitor_trades_loop(self):
        """حلقة مراقبة الصفقات الحية"""
        while self.monitoring_active:
            try:
                # تحديث أسعار من Binance
                symbols = list(set(trade['market'] for trade in self.active_trades.values()))
                if symbols:
                    prices = binance_service.get_current_prices(symbols)
                    for trade_id, trade in list(self.active_trades.items()):
                        symbol = trade['market']
                        if symbol in prices:
                            current_price = prices[symbol]
                            trade['current_price'] = current_price
                            trade['last_update'] = datetime.utcnow()
                            self._check_alerts(trade_id, trade, current_price)
            except Exception as e:
                print(f"خطأ في مراقبة الصفقات: {e}")
            time.sleep(5)  # تحديث كل 5 ثواني

    def _check_alerts(self, trade_id: str, trade: Dict, current_price: float):
        """فحص وإرسال التنبيهات"""
        alerts_sent = trade['alerts_sent']
        direction = trade['direction']
        entry = trade['entry_price']
        sl = trade['stop_loss']
        tps = trade['take_profits']

        # تنبيه TP1 قريب
        if tps and len(tps) > 0:
            tp1 = tps[0]
            distance = abs(current_price - tp1)
            if distance <= 5 and 'tp1_near' not in alerts_sent:
                message = f"TP1 قريب - على بعد {distance:.1f} نقاط من {tp1}"
                self._send_alert(trade['user_id'], trade['market'], message)
                alerts_sent.add('tp1_near')

        # تنبيه تم تحقيق TP1
        if tps and len(tps) > 0 and direction == 'شراء' and current_price >= tps[0] and 'tp1_hit' not in alerts_sent:
            message = f"تم تحقيق TP1 - إغلاق 50% من الصفقة عند {tps[0]}"
            self._send_alert(trade['user_id'], trade['market'], message)
            alerts_sent.add('tp1_hit')
        elif tps and len(tps) > 0 and direction == 'بيع' and current_price <= tps[0] and 'tp1_hit' not in alerts_sent:
            message = f"تم تحقيق TP1 - إغلاق 50% من الصفقة عند {tps[0]}"
            self._send_alert(trade['user_id'], trade['market'], message)
            alerts_sent.add('tp1_hit')

        # تنبيه السعر يتراجع نحو SL
        distance_to_sl = abs(current_price - sl)
        if distance_to_sl <= 10 and 'sl_near' not in alerts_sent:
            message = f"السعر يتراجع - على بعد {distance_to_sl:.1f} نقاط من الوقف عند {sl}"
            self._send_alert(trade['user_id'], trade['market'], message)
            alerts_sent.add('sl_near')

        # تنبيه تم تفعيل SL
        if (direction == 'شراء' and current_price <= sl) or (direction == 'بيع' and current_price >= sl):
            if 'sl_hit' not in alerts_sent:
                message = f"تم تفعيل Stop Loss عند {sl}"
                self._send_alert(trade['user_id'], trade['market'], message)
                alerts_sent.add('sl_hit')
                # إزالة الصفقة وتوليد تقرير
                self._generate_trade_report(trade_id, trade, current_price, 'stop_loss')
                self.remove_active_trade(trade_id)

        # تنبيه Breakeven
        if 'breakeven' not in alerts_sent and ((direction == 'شراء' and current_price >= entry + 30) or (direction == 'بيع' and current_price <= entry - 30)):
            message = f"Breakeven مفعّل - الصفقة آمنة الآن عند {current_price}"
            self._send_alert(trade['user_id'], trade['market'], message)
            alerts_sent.add('breakeven')

    def _send_alert(self, user_id: int, market: str, message: str):
        """إرسال تنبيه عبر جميع القنوات"""
        full_message = f"🚨 تنبيه صفقة {market}: {message}"
        notification_service.send_smart_notification(user_id, full_message, market)
        # يمكن إضافة Push Notification و Email هنا إذا كان مطلوباً

    def _generate_trade_report(self, trade_id: str, trade: Dict, exit_price: float, exit_reason: str):
        """توليد تقرير تلقائي بعد إغلاق الصفقة"""
        entry_price = trade['entry_price']
        direction = trade['direction']
        pnl = self._calculate_pnl(trade, exit_price)
        pnl_percent = round((pnl / (entry_price * trade['position_size'])) * 100, 2) if entry_price * trade['position_size'] > 0 else 0
        duration = datetime.utcnow() - trade['entry_time']
        targets_hit = 0
        for tp in trade['take_profits']:
            if (direction == 'شراء' and exit_price >= tp) or (direction == 'بيع' and exit_price <= tp):
                targets_hit += 1

        result = "ربح" if pnl >= 0 else "خسارة"
        strategies_correct = []  # يمكن تحسين هذا بناءً على البيانات
        lessons_learned = f"النظام تعلم أن {direction} في {trade['market']} كان {'صحيحاً' if pnl >= 0 else 'خاطئاً'} في هذه الحالة."

        report = f"""
📊 تقرير صفقة {trade['market']} - {result}

النتيجة: {result} ({pnl:+.2f}$ / {pnl_percent:+.2f}%)
المبلغ: {pnl:+.2f}$
النسبة المئوية: {pnl_percent:+.2f}%
مدة الصفقة: {duration}
عدد الأهداف المحققة: {targets_hit}/{len(trade['take_profits'])}
الاستراتيجيات الصحيحة: {', '.join(strategies_correct) if strategies_correct else 'غير محدد'}
ما تعلمه النظام: {lessons_learned}
        """.strip()

        # حفظ في JournalEntry
        journal_service.add_entry(
            user_id=trade['user_id'],
            market=trade['market'],
            result=result,
            profit_loss=pnl,
            notes=report,
            strategies=strategies_correct,
            duration=str(duration),
            entry_price=entry_price,
            exit_price=exit_price,
            stop_loss=trade['stop_loss'],
            take_profit=trade['take_profits'][0] if trade['take_profits'] else None,
        )

        # حفظ في TradeExperience للتعلم
        from database import SessionLocal
        db = SessionLocal()
        try:
            experience = models.TradeExperience(
                user_id=trade['user_id'],
                market=trade['market'],
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=pnl,
                result=result,
                strategies=strategies_correct,
                lessons=lessons_learned,
                duration=str(duration),
            )
            db.add(experience)
            db.commit()
        finally:
            db.close()


trade_manager_service = TradeManagerService()
