import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .binance_service import BinanceService
from .websocket_service import BinanceWebSocketService
from .telegram_service import telegram_service
from .shadow_trader import ShadowTrader
from database import SessionLocal
import models
import logging

logger = logging.getLogger(__name__)

SESSION_MAP = {
    'Tokyo': {'hours': range(0, 9), 'label': 'طوكيو 🟡', 'note': 'جلسة طوكيو: عرضي غالباً، أهداف أضيق.'},
    'London': {'hours': range(8, 17), 'label': 'لندن 🟢', 'note': 'جلسة لندن: تقلب أعلى، استخدم وقف أوسع.'},
    'NewYork': {'hours': range(13, 22), 'label': 'نيويورك 🔵', 'note': 'جلسة نيويورك: تداخل مع لندن = أفضل وقت.'},
}

DEFAULT_WS_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT', 'LTCUSDT', 'XAUUSDT'
]

class MarketProtectionService:
    def __init__(self, symbols: Optional[List[str]] = None):
        self.symbols = symbols or DEFAULT_WS_SYMBOLS
        self.ws_service = BinanceWebSocketService(self.symbols, max_symbols=20)
        self.binance = BinanceService(ws_service=self.ws_service)
        self.spread_history = defaultdict(lambda: deque(maxlen=500))
        self.spread_alerts = deque(maxlen=200)
        self.ws_service.add_callback('depth', self._on_depth)
        self.ws_service.add_callback('ticker', self._on_ticker)
        self.is_running = False

    def get_current_session(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        hour = now.hour
        for name, info in SESSION_MAP.items():
            if hour in info['hours']:
                return {
                    'session': name,
                    'label': info['label'],
                    'note': info['note'],
                    'timestamp': now.isoformat() + 'Z'
                }
        return {
            'session': 'Tokyo',
            'label': SESSION_MAP['Tokyo']['label'],
            'note': SESSION_MAP['Tokyo']['note'],
            'timestamp': now.isoformat() + 'Z'
        }

    def apply_session_adjustment(self, plan: Dict[str, Any], session_info: Dict[str, Any]) -> Dict[str, Any]:
        session = session_info.get('session')
        if not session or session == 'NewYork':
            plan['session_note'] = session_info.get('note')
            return plan

        if session == 'London':
            plan['recommended_risk_percent'] = round(min(2.0, float(plan.get('recommended_risk_percent', 1.0)) * 1.1), 2)
            plan['session_note'] = session_info.get('note')
        elif session == 'Tokyo':
            plan['recommended_risk_percent'] = round(max(0.25, float(plan.get('recommended_risk_percent', 1.0)) * 0.85), 2)
            plan['session_note'] = session_info.get('note')
        else:
            plan['session_note'] = session_info.get('note')

        return plan

    def detect_strategy_clash(self, strategy_signals: Optional[List[dict]]) -> Dict[str, Any]:
        if not strategy_signals:
            return {'clash': False}

        strong_buys: List[Dict[str, Any]] = []
        strong_sells: List[Dict[str, Any]] = []

        for signal in strategy_signals:
            name = str(signal.get('strategy') or signal.get('name') or '').strip()
            direction = str(signal.get('direction') or signal.get('recommendation') or '').lower()
            strength = float(signal.get('strength') or signal.get('confidence') or 0)
            entry = {
                'name': name,
                'direction': direction,
                'strength': strength,
                'reason': signal.get('reason') or signal.get('note') or ''
            }
            if ('buy' in direction or 'شراء' in direction) and strength >= 65:
                strong_buys.append(entry)
            if ('sell' in direction or 'بيع' in direction) and strength >= 65:
                strong_sells.append(entry)

        if not strong_buys or not strong_sells:
            return {'clash': False}

        name_lower = lambda item: item['name'].lower() if item['name'] else ''
        smc_buy = [item for item in strong_buys if 'smc' in name_lower(item)]
        pa_sell = [item for item in strong_sells if 'price' in name_lower(item) or 'action' in name_lower(item)]
        smc_sell = [item for item in strong_sells if 'smc' in name_lower(item)]
        pa_buy = [item for item in strong_buys if 'price' in name_lower(item) or 'action' in name_lower(item)]

        message = '⚠️ تعارض في التحليل. انتظر'
        details = {
            'strong_buys': strong_buys,
            'strong_sells': strong_sells,
        }
        if (smc_buy and pa_sell) or (smc_sell and pa_buy):
            return {'clash': True, 'reject': True, 'message': message + ' (SMC vs Price Action)', 'details': details}

        return {'clash': True, 'reject': False, 'message': message, 'details': details}

    def create_price_alert(self, user_id: int, market: str, target_price: float, direction: Optional[str] = None) -> Dict[str, Any]:
        market = (market or '').strip().upper()
        if not market or target_price is None:
            raise ValueError('Market and target price are required')

        if direction not in ('above', 'below'):
            direction = 'above'

        db = SessionLocal()
        try:
            alert = models.PriceAlert(
                user_id=user_id,
                market=market,
                target_price=target_price,
                direction=direction,
                active=True,
                created_at=datetime.now(timezone.utc)
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            return {
                'id': alert.id,
                'market': alert.market,
                'target_price': alert.target_price,
                'direction': alert.direction,
                'active': alert.active,
                'created_at': alert.created_at.isoformat()
            }
        finally:
            db.close()

    def list_price_alerts(self, user_id: int) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            alerts = db.query(models.PriceAlert).filter(models.PriceAlert.user_id == user_id).order_by(models.PriceAlert.created_at.desc()).all()
            return [
                {
                    'id': alert.id,
                    'market': alert.market,
                    'target_price': alert.target_price,
                    'direction': alert.direction,
                    'active': alert.active,
                    'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None,
                    'created_at': alert.created_at.isoformat() if alert.created_at else None,
                    'message': alert.message,
                }
                for alert in alerts
            ]
        finally:
            db.close()

    def delete_price_alert(self, user_id: int, alert_id: int) -> bool:
        db = SessionLocal()
        try:
            alert = db.query(models.PriceAlert).filter(models.PriceAlert.user_id == user_id, models.PriceAlert.id == alert_id).first()
            if not alert:
                return False
            alert.active = False
            db.commit()
            return True
        finally:
            db.close()

    def record_slippage(self, user_id: int, market: str, expected_price: float, executed_price: float, trade_id: Optional[int] = None) -> Dict[str, Any]:
        slippage = None
        if expected_price is not None and executed_price is not None:
            slippage = round(abs(executed_price - expected_price), 6)

        db = SessionLocal()
        try:
            log = models.TradeSlippageLog(
                user_id=user_id,
                market=market,
                expected_price=expected_price,
                executed_price=executed_price,
                slippage=slippage,
                trade_id=trade_id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return {
                'id': log.id,
                'market': log.market,
                'expected_price': log.expected_price,
                'executed_price': log.executed_price,
                'slippage': log.slippage,
                'trade_id': log.trade_id,
                'created_at': log.created_at.isoformat()
            }
        finally:
            db.close()

    def quick_trade_entry(self, user_id: int, market: str, recommendation: str, entry_price: float,
                          stop_loss: Optional[float] = None, take_profit: Optional[float] = None,
                          expected_price: Optional[float] = None, notes: Optional[str] = None) -> Dict[str, Any]:
        market = (market or '').strip().upper()
        direction = 'شراء' if 'شراء' in str(recommendation) or 'buy' in str(recommendation).lower() else 'بيع'
        if not stop_loss or not take_profit:
            if direction == 'شراء':
                stop_loss = round(entry_price * 0.99, 6)
                take_profit = round(entry_price * 1.018, 6)
            else:
                stop_loss = round(entry_price * 1.01, 6)
                take_profit = round(entry_price * 0.982, 6)

        trader = ShadowTrader(user_id)
        trade = trader.open_trade(market, entry_price, sl=stop_loss, tp=take_profit)

        db = SessionLocal()
        try:
            journal = models.JournalEntry(
                user_id=user_id,
                date=datetime.now(timezone.utc),
                market=market,
                recommendation=direction,
                result='pending',
                profit_loss=0.0,
                confidence=None,
                notes=notes or f'سجلت صفقة بسرعة مع SL={stop_loss}, TP={take_profit}.',
                session=self.get_current_session().get('session')
            )
            db.add(journal)
            db.commit()
            db.refresh(journal)
        finally:
            db.close()

        slippage_record = None
        if expected_price is not None:
            slippage_record = self.record_slippage(
                user_id=user_id,
                market=market,
                expected_price=expected_price,
                executed_price=entry_price,
                trade_id=trade.id
            )

        return {
            'trade': {
                'id': trade.id,
                'market': trade.market,
                'entry_price': trade.entry_price,
                'stop_loss': trade.stop_loss,
                'take_profit': trade.take_profit,
                'status': trade.status,
                'created_at': trade.created_at.isoformat() if getattr(trade, 'created_at', None) else None,
            },
            'journal': {
                'id': journal.id,
                'market': journal.market,
                'recommendation': journal.recommendation,
                'result': journal.result,
                'profit_loss': journal.profit_loss,
                'notes': journal.notes,
                'session': journal.session,
                'created_at': journal.created_at.isoformat() if getattr(journal, 'created_at', None) else None,
            },
            'slippage': slippage_record,
            'session_info': self.get_current_session()
        }

    def get_spread_report(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        recent_week = now - timedelta(days=7)
        all_values: List[float] = []
        symbol_data = []

        for symbol, history in self.spread_history.items():
            values = [value for ts, value in history if ts >= recent_week]
            if not values:
                continue
            average = round(sum(values) / len(values), 6)
            latest = round(values[-1], 6)
            alert = latest > average * 3 if average > 0 else False
            symbol_data.append({
                'symbol': symbol,
                'latest_spread': latest,
                'average_spread': average,
                'alert': alert,
            })
            all_values.extend(values)

        weekly_average = round(sum(all_values) / len(all_values), 6) if all_values else 0.0
        return {
            'symbols': symbol_data,
            'weekly_average_spread': weekly_average,
            'spread_alerts': list(self.spread_alerts)[-5:]
        }

    def _price_matches(self, alert: models.PriceAlert, price: float) -> bool:
        if alert.direction == 'below':
            return price <= alert.target_price
        return price >= alert.target_price

    def _trigger_price_alert(self, alert: models.PriceAlert, price: float):
        db = SessionLocal()
        try:
            active_alert = db.query(models.PriceAlert).filter(models.PriceAlert.id == alert.id).first()
            if not active_alert or not active_alert.active:
                return
            active_alert.active = False
            active_alert.triggered_at = datetime.now(timezone.utc)
            active_alert.message = f'وصل سعر {active_alert.market} إلى {price}$' if active_alert.direction == 'above' else f'هبط سعر {active_alert.market} إلى {price}$'
            db.commit()
            message = f'تنبيه: {active_alert.market} وصل {price}$'
            prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == active_alert.user_id).first()
            if prefs and prefs.telegram_chat_id:
                telegram_service.send_message(prefs.telegram_chat_id, message)
            self.spread_alerts.append({'market': active_alert.market, 'price': price, 'message': active_alert.message, 'time': datetime.now(timezone.utc).isoformat()})
        finally:
            db.close()

    async def _on_depth(self, symbol: str, data: dict):
        spread = data.get('spread')
        if spread is None:
            return
        now = datetime.now(timezone.utc)
        self.spread_history[symbol].append((now, spread))
        history = [value for ts, value in self.spread_history[symbol] if ts >= now - timedelta(hours=2)]
        if not history:
            return
        average = sum(history) / len(history)
        if average > 0 and spread > average * 3:
            alert = {
                'symbol': symbol,
                'spread': spread,
                'average': round(average, 6),
                'message': 'السبريد عالي الآن. لا تدخل',
                'time': now.isoformat()
            }
            self.spread_alerts.append(alert)

    async def _on_ticker(self, symbol: str, data: dict):
        price = data.get('price')
        if price is None:
            return
        alerts = self._find_price_alerts_for_symbol(symbol)
        for alert in alerts:
            if alert.active and self._price_matches(alert, price):
                self._trigger_price_alert(alert, price)

    def _find_price_alerts_for_symbol(self, symbol: str) -> List[models.PriceAlert]:
        db = SessionLocal()
        try:
            return db.query(models.PriceAlert).filter(models.PriceAlert.market == symbol.upper(), models.PriceAlert.active == True).all()
        finally:
            db.close()

    def run(self):
        if self.is_running:
            return
        self.is_running = True
        try:
            asyncio.run(self.ws_service.start())
        except Exception as e:
            logger.exception(f"Market monitor failed: {e}")
        finally:
            self.is_running = False

market_protection_service = MarketProtectionService()
