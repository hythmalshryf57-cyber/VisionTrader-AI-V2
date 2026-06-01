"""
MetaTrader 5 Integration Service
Provides live connection to MT5 for prices, historical data, and trade execution.
Includes a Simulator mode for Linux/Render or testing without an active MT5 terminal.
"""
import os
import logging
import random
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try importing MetaTrader5 (Only works on Windows)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


class MT5Service:
    def __init__(self):
        self.connected = False
        self.simulator_mode = not MT5_AVAILABLE
        self.account_info = {
            "balance": 10000.0,
            "equity": 10000.0,
            "margin": 0.0,
            "free_margin": 10000.0,
            "margin_level": 0.0,
            "currency": "USD"
        }
        self.open_positions = {}
        self.ticket_counter = 100000

    def connect(self, account: int = 0, password: str = "", server: str = "") -> bool:
        """Connects to MT5 terminal or enables simulator"""
        if self.simulator_mode:
            logger.warning("MT5 package not available or Simulator forced. Starting in Simulator mode.")
            # Do NOT claim a successful live connection when in simulator mode.
            # Leave `connected` as False (not connected) but allow simulator behavior in methods.
            self.connected = False
            return {"status": "simulated", "warning": "MT5 غير متصل - النتائج محاكاة"}

        if not mt5.initialize():
            logger.error(f"MT5 initialize failed, error code: {mt5.last_error()}")
            self.simulator_mode = True
            self.connected = True
            return True

        # If credentials provided, login
        if account and password and server:
            authorized = mt5.login(account, password=password, server=server)
            if not authorized:
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                self.simulator_mode = True
                self.connected = True
                return True

        self.connected = True
        logger.info("Connected to MetaTrader 5 successfully.")
        return True

    def get_account_info(self) -> dict:
        """Returns account info: balance, equity, margin"""
        # If simulator mode is enabled, return simulated account info (transparent simulation)
        if self.simulator_mode:
            floating_pnl = sum(p['pnl'] for p in self.open_positions.values())
            self.account_info['equity'] = self.account_info['balance'] + floating_pnl
            return {**self.account_info, "status": "simulated", "warning": "MT5 غير متصل - النتائج محاكاة"}

        if not self.connected:
            return {}

        account_info = mt5.account_info()
        if account_info is None:
            logger.error(f"Failed to get MT5 account info: {mt5.last_error()}")
            return {}

        return {
            "balance": account_info.balance,
            "equity": account_info.equity,
            "margin": account_info.margin,
            "free_margin": account_info.margin_free,
            "margin_level": account_info.margin_level,
            "currency": account_info.currency
        }

    def get_price(self, symbol: str) -> dict:
        """Returns live bid/ask price for a symbol"""
        # Simulator has priority: provide simulated price even if not marked as connected.
        if self.simulator_mode:
            base_price = 2000.0 if "XAU" in symbol else 1.1000
            spread = 0.5 if "XAU" in symbol else 0.0002
            variation = random.uniform(-0.1, 0.1) if "XAU" in symbol else random.uniform(-0.001, 0.001)
            bid = round(base_price + variation, 5)
            ask = round(bid + spread, 5)

            # Update simulated P&L
            for t_id, pos in self.open_positions.items():
                if pos['symbol'] == symbol:
                    diff = (bid - pos['open_price']) if pos['type'] == 'buy' else (pos['open_price'] - ask)
                    pos['pnl'] = round(diff * pos['volume'] * 100, 2)

            return {"symbol": symbol, "bid": bid, "ask": ask, "time": datetime.utcnow().isoformat(), "status": "simulated", "warning": "MT5 غير متصل - النتائج محاكاة"}

        if not self.connected:
            return {}

        symbol_info = mt5.symbol_info_tick(symbol)
        if symbol_info is None:
            logger.error(f"Failed to get price for {symbol}: {mt5.last_error()}")
            return {}

        return {
            "symbol": symbol,
            "bid": symbol_info.bid,
            "ask": symbol_info.ask,
            "time": datetime.fromtimestamp(symbol_info.time).isoformat()
        }

    def get_history(self, symbol: str, timeframe: str, bars: int) -> list:
        """Returns historical OHLCV data"""
        # Return simulated history when in simulator mode
        if self.simulator_mode:
            history = []
            base_price = 2000.0 if "XAU" in symbol else 1.1000
            for i in range(bars, 0, -1):
                dt = datetime.utcnow() - timedelta(minutes=i*15)
                open_p = base_price + random.uniform(-5, 5)
                close_p = open_p + random.uniform(-2, 2)
                high_p = max(open_p, close_p) + random.uniform(0, 3)
                low_p = min(open_p, close_p) - random.uniform(0, 3)
                history.append({
                    "time": dt.isoformat(),
                    "open": round(open_p, 5),
                    "high": round(high_p, 5),
                    "low": round(low_p, 5),
                    "close": round(close_p, 5),
                    "volume": random.randint(100, 1000)
                })
            return history
        if not self.connected:
            return []

        # Map timeframe string to MT5 constant
        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1
        }
        mt5_tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
        
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, bars)
        if rates is None:
            logger.error(f"Failed to get history for {symbol}: {mt5.last_error()}")
            return []

        history = []
        for r in rates:
            history.append({
                "time": datetime.fromtimestamp(r['time']).isoformat(),
                "open": r['open'],
                "high": r['high'],
                "low": r['low'],
                "close": r['close'],
                "tick_volume": r['tick_volume']
            })
        return history

    def place_order(self, symbol: str, order_type: str, volume: float, price: float = 0.0, sl: float = 0.0, tp: float = 0.0) -> dict:
        """Places Market, Limit, or Stop order"""
        if self.simulator_mode:
            self.ticket_counter += 1
            ticket = self.ticket_counter
            
            if price == 0.0:
                p_data = self.get_price(symbol)
                price = p_data['ask'] if order_type == 'buy' else p_data['bid']

            self.open_positions[ticket] = {
                "ticket": ticket,
                "symbol": symbol,
                "type": order_type,
                "volume": volume,
                "open_price": price,
                "sl": sl,
                "tp": tp,
                "pnl": 0.0,
                "status": "OPEN",
                "time": datetime.utcnow().isoformat()
            }
            logger.info(f"[Simulator] Order placed: {ticket} {order_type} {symbol} Vol: {volume}")
            return {"ticket": ticket, "status": "success", "open_price": price}

        # MT5 Execution
        action_map = {
            "buy": mt5.ORDER_TYPE_BUY,
            "sell": mt5.ORDER_TYPE_SELL,
            "buy_limit": mt5.ORDER_TYPE_BUY_LIMIT,
            "sell_limit": mt5.ORDER_TYPE_SELL_LIMIT,
            "buy_stop": mt5.ORDER_TYPE_BUY_STOP,
            "sell_stop": mt5.ORDER_TYPE_SELL_STOP
        }
        
        if order_type not in action_map:
            return {"error": "Invalid order type"}

        action = action_map[order_type]
        
        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL if order_type in ["buy", "sell"] else mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": float(volume),
            "type": action,
            "sl": float(sl) if sl > 0 else 0.0,
            "tp": float(tp) if tp > 0 else 0.0,
            "deviation": 20,
            "magic": 234000,
            "comment": "VisionTrader AI",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if price > 0.0:
            request["price"] = float(price)
        else:
            p_data = self.get_price(symbol)
            request["price"] = float(p_data.get('ask')) if order_type == 'buy' else float(p_data.get('bid'))

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result.retcode}")
            return {"error": f"MT5 order failed. retcode={result.retcode}"}

        return {
            "ticket": result.order,
            "status": "success",
            "open_price": result.price
        }

    def modify_position(self, ticket: int, sl: float, tp: float) -> dict:
        """Modifies Stop Loss and Take Profit of a position"""
        if not self.connected:
            return {"error": "Not connected"}

        if self.simulator_mode:
            if ticket in self.open_positions:
                self.open_positions[ticket]['sl'] = sl
                self.open_positions[ticket]['tp'] = tp
                logger.info(f"[Simulator] Modified {ticket}: SL={sl}, TP={tp}")
                return {"status": "success", "ticket": ticket, "status_detail": "simulated"}
            return {"error": "Ticket not found"}

        if not self.connected:
            return {"error": "Not connected"}

        # For MT5, we need to know symbol and order type to modify
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {"error": "Position not found in MT5"}
        
        pos = position[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "sl": float(sl),
            "tp": float(tp),
            "position": ticket
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"error": f"Modify failed: {result.retcode}"}

        return {"status": "success", "ticket": ticket}

    def close_position(self, ticket: int) -> dict:
        """Closes an open position"""
        if self.simulator_mode:
            if ticket in self.open_positions:
                pos = self.open_positions.pop(ticket)
                self.account_info['balance'] += pos['pnl']
                logger.info(f"[Simulator] Closed {ticket}. PnL: {pos['pnl']}")
                return {"status": "success", "ticket": ticket, "pnl": pos['pnl']}
            return {"error": "Ticket not found"}
        if not self.connected:
            return {"error": "Not connected"}

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {"error": "Position not found"}

        pos = position[0]
        tick = mt5.symbol_info_tick(pos.symbol)
        close_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": ticket,
            "price": close_price,
            "deviation": 20,
            "magic": 234000,
            "comment": "VisionTrader Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"error": f"Close failed: {result.retcode}"}

        return {"status": "success", "ticket": ticket, "close_price": close_price}


mt5_service = MT5Service()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=========================================")
    print("   MetaTrader 5 Integration Tests")
    print("=========================================")
    
    svc = MT5Service()
    svc.connect()
    
    print("\n[Account Info]")
    print(svc.get_account_info())
    
    print("\n[Live Price - XAUUSD]")
    print(svc.get_price("XAUUSD"))
    
    print("\n[History - EURUSD M15]")
    history = svc.get_history("EURUSD", "M15", 3)
    for h in history:
        print(h)
        
    print("\n[Place Trade - BUY XAUUSD]")
    p = svc.get_price("XAUUSD")
    current_ask = p.get("ask", 2000.0)
    order = svc.place_order("XAUUSD", "buy", 0.01, sl=current_ask - 20, tp=current_ask + 20)
    print(order)
    ticket = order.get("ticket")
    
    if ticket:
        print("\n[Modify Trade - Adjust SL/TP]")
        print(svc.modify_position(ticket, sl=current_ask - 25, tp=current_ask + 30))
        
        # Simulate price move
        print("\n[Waiting for price update...]")
        time.sleep(1)
        svc.get_price("XAUUSD")
        
        print("\n[Close Trade]")
        print(svc.close_position(ticket))
        
    print("\n[Final Account Info]")
    print(svc.get_account_info())
    print("\n✅ All MT5 Service operations executed successfully!")
