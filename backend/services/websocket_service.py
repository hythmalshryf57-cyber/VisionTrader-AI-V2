import asyncio
import json
import logging
from typing import Dict, List, Callable, Optional
from collections import defaultdict
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

logger = logging.getLogger(__name__)

class BinanceWebSocketService:
    BASE_WS_URL = "wss://fstream.binance.com/ws/"

    def __init__(self, symbols: List[str], max_symbols: int = 20):
        if len(symbols) > max_symbols:
            raise ValueError(f"Maximum {max_symbols} symbols allowed")
        self.symbols = [s.upper() for s in symbols]
        self.max_symbols = max_symbols
        self.ws = None
        self.running = False
        self.data = defaultdict(dict)  # Store live data per symbol
        self.cumulative_delta = defaultdict(float)
        self.recent_trades = defaultdict(list)
        self.callbacks = defaultdict(list)  # Callbacks for different events
        self.reconnect_delay = 5  # seconds
        self.ping_interval = 30  # seconds

    async def connect(self):
        """Establish WebSocket connection and subscribe to streams"""
        streams = []
        for symbol in self.symbols:
            streams.extend([
                f"{symbol.lower()}@ticker",
                f"{symbol.lower()}@depth@100ms",  # Closest to 20ms
                f"{symbol.lower()}@trade",
                f"{symbol.lower()}@kline_1m",
                f"{symbol.lower()}@forceOrder",
                f"{symbol.lower()}@openInterest"
            ])

        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1
        }

        while self.running:
            try:
                async with websockets.connect(self.BASE_WS_URL) as websocket:
                    self.ws = websocket
                    logger.info(f"Connected to Binance WebSocket for symbols: {self.symbols}")

                    # Subscribe to streams
                    await websocket.send(json.dumps(subscribe_msg))
                    logger.info("Subscribed to streams")

                    # Start ping task
                    ping_task = asyncio.create_task(self._ping_loop())

                    # Handle messages
                    async for message in websocket:
                        try:
                            await self._handle_message(json.loads(message))
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse message: {e}")

                    ping_task.cancel()

            except (ConnectionClosedError, WebSocketException) as e:
                logger.warning(f"WebSocket connection error: {e}. Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                logger.error(f"Unexpected error: {e}. Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)

    async def _ping_loop(self):
        """Send ping messages to keep connection alive"""
        while self.running:
            try:
                if self.ws:
                    await self.ws.ping()
                    logger.debug("Sent ping")
                await asyncio.sleep(self.ping_interval)
            except Exception as e:
                logger.error(f"Ping error: {e}")
                break

    async def _handle_message(self, msg: dict):
        """Process incoming WebSocket messages"""
        if 'stream' in msg:
            stream = msg['stream']
            data = msg['data']

            # Parse stream type
            parts = stream.split('@')
            if len(parts) >= 2:
                symbol = parts[0].upper()
                stream_type = parts[1]

                if stream_type == 'ticker':
                    await self._handle_ticker(symbol, data)
                elif stream_type == 'depth':
                    await self._handle_depth(symbol, data)
                elif stream_type == 'trade':
                    await self._handle_trade(symbol, data)
                elif stream_type == 'kline_1m':
                    await self._handle_kline(symbol, data)
                elif stream_type == 'forceOrder':
                    await self._handle_force_order(symbol, data)
                elif stream_type == 'openInterest':
                    await self._handle_open_interest(symbol, data)

    async def _handle_ticker(self, symbol: str, data: dict):
        """Handle ticker updates"""
        self.data[symbol]['price'] = float(data.get('c', 0))  # Last price
        self.data[symbol]['price_change'] = float(data.get('P', 0))  # Price change percent
        self._trigger_callbacks('ticker', symbol, self.data[symbol])

    async def _handle_depth(self, symbol: str, data: dict):
        """Handle order book depth updates"""
        bids = [[float(price), float(qty)] for price, qty in data.get('b', [])[:20]]
        asks = [[float(price), float(qty)] for price, qty in data.get('a', [])[:20]]

        self.data[symbol]['bids'] = bids
        self.data[symbol]['asks'] = asks
        self.data[symbol]['order_book'] = {'bids': bids, 'asks': asks}

        # Monitor spread
        if bids and asks:
            spread = asks[0][0] - bids[0][0]
            self.data[symbol]['spread'] = spread
            await self._check_spread_alert(symbol, spread)

        self._trigger_callbacks('depth', symbol, self.data[symbol])

    async def _handle_trade(self, symbol: str, data: dict):
        """Handle trade updates"""
        price = float(data.get('p', 0))
        qty = float(data.get('q', 0))
        is_buyer_maker = data.get('m', False)  # True if buyer is market maker

        # Calculate delta (buy volume - sell volume)
        delta = qty if not is_buyer_maker else -qty
        self.cumulative_delta[symbol] += delta
        self.data[symbol]['cumulative_delta'] = self.cumulative_delta[symbol]
        self.recent_trades[symbol].append({
            'price': price,
            'qty': qty,
            'delta': delta,
            'timestamp': data.get('T'),
            'is_buyer_maker': is_buyer_maker
        })
        if len(self.recent_trades[symbol]) > 200:
            self.recent_trades[symbol] = self.recent_trades[symbol][-200:]
        self.data[symbol]['recent_trades'] = list(self.recent_trades[symbol])

        # Whale alert
        usd_value = price * qty
        if usd_value > 50000:
            await self._whale_alert(symbol, usd_value, is_buyer_maker)

        self._trigger_callbacks('trade', symbol, {
            'price': price,
            'qty': qty,
            'delta': delta,
            'cumulative_delta': self.cumulative_delta[symbol]
        })

    async def _handle_kline(self, symbol: str, data: dict):
        """Handle kline updates"""
        k = data.get('k', {})
        self.data[symbol]['kline'] = {
            'open': float(k.get('o', 0)),
            'high': float(k.get('h', 0)),
            'low': float(k.get('l', 0)),
            'close': float(k.get('c', 0)),
            'volume': float(k.get('v', 0)),
            'is_closed': k.get('x', False)
        }
        self._trigger_callbacks('kline', symbol, self.data[symbol]['kline'])

    async def _handle_force_order(self, symbol: str, data: dict):
        """Handle liquidation updates"""
        self.data[symbol]['liquidations'] = data.get('o', [])
        self._trigger_callbacks('force_order', symbol, data)

    async def _handle_open_interest(self, symbol: str, data: dict):
        """Handle open interest updates"""
        oi = float(data.get('o', 0))
        oi_change = float(data.get('c', 0))  # Change in open interest
        self.data[symbol]['open_interest'] = oi
        self.data[symbol]['open_interest_change'] = oi_change
        self._trigger_callbacks('open_interest', symbol, {
            'open_interest': oi,
            'change': oi_change
        })

    async def _check_spread_alert(self, symbol: str, spread: float):
        """Check if spread is expanding and alert"""
        # Simple threshold - can be made configurable
        threshold = 0.001  # 0.1%
        if spread > threshold:
            self._trigger_callbacks('spread_alert', symbol, {'spread': spread})

    async def _whale_alert(self, symbol: str, usd_value: float, is_buy: bool):
        """Send whale alert"""
        self._trigger_callbacks('whale_alert', symbol, {
            'usd_value': usd_value,
            'is_buy': not is_buy,  # is_buyer_maker is False for buyer
            'type': 'buy' if not is_buy else 'sell'
        })

    def add_callback(self, event: str, callback: Callable):
        """Add callback for specific event"""
        self.callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, symbol: str, data: dict):
        """Trigger all callbacks for an event"""
        for callback in self.callbacks[event]:
            try:
                asyncio.create_task(callback(symbol, data))
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    def get_live_data(self, symbol: str) -> dict:
        """Get current live data for a symbol"""
        return self.data.get(symbol.upper(), {})

    async def start(self):
        """Start the WebSocket service"""
        self.running = True
        await self.connect()

    async def stop(self):
        """Stop the WebSocket service"""
        self.running = False
        if self.ws:
            await self.ws.close()

    def reset_cumulative_delta(self, symbol: str):
        """Reset cumulative delta for a symbol"""
        self.cumulative_delta[symbol.upper()] = 0.0