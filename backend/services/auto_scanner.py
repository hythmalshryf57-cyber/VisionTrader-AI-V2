import time
import requests
import json
import os
import datetime
import urllib.parse
from typing import Optional
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from services.cache_service import cache_service
from services.voting_engine import voting_engine
from services.alert_manager import create_alert
from services.telegram_service import telegram_service
from services.binance_service import binance_service
from services.tradingview_service import tradingview_service
from services.news_adapter import NewsAdapter, ImpactLevel

MARKETS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD", "EURGBP",
    "XAUUSD", "XAGUSD",
    "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "XRPUSD",
    "US30", "US100", "SPX500"
]

class AutoScanner:
    CRYPTO_MARKETS = {"BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "XRPUSD"}
    TIER1_MARKETS = ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD"]
    TIER2_MARKETS = ["USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD", "EURGBP", "ETHUSD", "US30", "US100"]
    TIER3_MARKETS = ["XAGUSD", "SOLUSD", "BNBUSD", "XRPUSD", "SPX500"]
    NEWS_CACHE_TTL = 600

    def __init__(self):
        self.is_running = False
        self.last_run_l1 = 0
        self.last_run_l2 = 0
        self.last_run_l3 = 0
        self.last_event_check = 0
        self.last_immediate_scan = {}
        self.news_adapter = NewsAdapter()
        self.news_cache = []
        self.news_cache_at = 0

    def stop(self):
        try:
            self.is_running = False
        except Exception:
            pass

    def _get_active_users(self):
        db = SessionLocal()
        try:
            return db.query(models.User).filter(models.User.is_active == True).all()
        finally:
            db.close()

    def _is_market_relevant_to_user(self, prefs, mode_name, market):
        watchlist = []
        try:
            watchlist = json.loads(prefs.watchlist or "[]")
        except Exception:
            watchlist = []
        if watchlist and market not in watchlist:
            return False
        trading_mode = (prefs.trading_mode or "day").lower()
        if "scalping" in mode_name.lower() and trading_mode != "scalping":
            return False
        if "day trading" in mode_name.lower() and trading_mode == "swing":
            return False
        if "swing trading" in mode_name.lower() and trading_mode == "scalping":
            return False
        return True

    def _map_binance_symbol(self, market: str) -> str:
        mapping = {
            "BTCUSD": "BTCUSDT",
            "ETHUSD": "ETHUSDT",
            "SOLUSD": "SOLUSDT",
            "BNBUSD": "BNBUSDT",
            "XRPUSD": "XRPUSDT",
        }
        return mapping.get(market.replace(" ", "").upper(), market.replace(" ", "").upper())

    def _get_live_price(self, market: str) -> Optional[float]:
        key = market.replace(" ", "").upper()
        if key in self.CRYPTO_MARKETS:
            binance_symbol = self._map_binance_symbol(key)
            price = binance_service.get_ticker_price(binance_symbol)
            if price and float(price) > 0:
                return float(price)

            price = tradingview_service.get_price_from_twelvedata(key)
            if price and float(price) > 0:
                return float(price)
            return None

        price = tradingview_service.get_symbol_price(key)
        if price and float(price) > 0:
            return float(price)
        return None

    def _get_price_decimals(self, price: float) -> int:
        if price >= 1000:
            return 2
        if price >= 100:
            return 2
        if price >= 10:
            return 3
        return 4

    def _fetch_recent_crypto_snapshot(self, market: str) -> dict:
        binance_symbol = self._map_binance_symbol(market)
        data = {
            "symbol": binance_symbol,
            "price": 0.0,
            "recent_pct": 0.0,
            "volume": 0.0,
            "avg_volume": 0.0,
            "news_impact": None,
        }

        live = {}
        if binance_service.ws_service:
            live = binance_service.ws_service.get_live_data(binance_symbol)
            data["price"] = float(live.get("price", 0.0))
            data["volume"] = float(live.get("kline", {}).get("volume", 0.0))
            data["recent_pct"] = float(live.get("price_change", 0.0))

        klines = binance_service.get_klines(binance_symbol, interval="1m", limit=10)
        volumes = []
        closes = []
        for candle in klines:
            try:
                volumes.append(float(candle[5]))
                closes.append(float(candle[4]))
            except Exception:
                continue
        if closes:
            data["recent_pct"] = abs((closes[-1] - closes[0]) / closes[0]) if closes[0] != 0 else 0.0
            data["price"] = float(closes[-1])
        if volumes:
            data["avg_volume"] = sum(volumes) / len(volumes)
            data["volume"] = volumes[-1]
        return data

    def _fetch_recent_tradable_snapshot(self, market: str) -> dict:
        result = {"market": market, "price": 0.0, "pct_change": 0.0, "volume": 0.0, "avg_volume": 0.0}
        try:
            ticker = market.replace(" ", "").upper()
            mapping = {
                "EURUSD": "EURUSD=X",
                "GBPUSD": "GBPUSD=X",
                "USDJPY": "USDJPY=X",
                "USDCHF": "USDCHF=X",
                "AUDUSD": "AUDUSD=X",
                "NZDUSD": "NZDUSD=X",
                "USDCAD": "USDCAD=X",
                "EURGBP": "EURGBP=X",
                "XAUUSD": "GC=F",
                "XAGUSD": "SI=F",
                "US30": "^DJI",
                "US100": "^NDX",
                "SPX500": "^GSPC",
            }
            ticker = mapping.get(ticker, ticker)
            quote = self._fetch_yahoo_quote(ticker)
            if quote:
                result.update(quote)
        except Exception:
            pass
        return result

    def _fetch_yahoo_quote(self, ticker: str) -> dict:
        try:
            q = urllib.parse.quote(ticker, safe='')
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={q}"
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            body = resp.json()
            results = body.get("quoteResponse", {}).get("result", [])
            if not results:
                return {}
            item = results[0]
            return {
                "price": float(item.get("regularMarketPrice", 0.0) or item.get("bid", 0.0) or item.get("ask", 0.0) or item.get("lastPrice", 0.0)),
                "pct_change": float(item.get("regularMarketChangePercent", 0.0) or 0.0),
                "volume": float(item.get("regularMarketVolume", 0.0) or item.get("volume", 0.0) or 0.0),
                "avg_volume": float(item.get("averageDailyVolume3Month", 0.0) or 0.0),
            }
        except Exception:
            return {}

    def _extract_relevant_news(self, market: str):
        now = time.time()
        if now - self.news_cache_at > self.NEWS_CACHE_TTL:
            self.news_cache = self.news_adapter.fetch()
            self.news_cache_at = now

        keywords_map = {
            "EURUSD": ["eur", "euro", "ecb", "europe"],
            "GBPUSD": ["gbp", "pound", "boe", "britain"],
            "USDJPY": ["usd", "jpy", "yen", "boj"],
            "USDCHF": ["usd", "chf", "swiss"],
            "AUDUSD": ["aud", "australia", "rba"],
            "NZDUSD": ["nzd", "new zealand", "rbnZ"],
            "USDCAD": ["cad", "canada", "boC"],
            "EURGBP": ["eur", "gbp", "euro", "pound"],
            "XAUUSD": ["gold", "xau", "precious"],
            "XAGUSD": ["silver", "xag", "precious"],
            "US30": ["dow jones", "djia", "us30"],
            "US100": ["nasdaq", "ndx", "us100"],
            "SPX500": ["s&p 500", "spx", "s&p", "sp500"],
            "BTCUSD": ["bitcoin", "btc", "crypto"],
            "ETHUSD": ["ethereum", "eth", "crypto"],
            "SOLUSD": ["solana", "sol", "crypto"],
            "BNBUSD": ["binance", "bnb", "crypto"],
            "XRPUSD": ["xrp", "ripple", "crypto"],
        }

        tokens = keywords_map.get(market, [market.lower()])
        best = None
        for item in self.news_cache:
            if item.impact not in (ImpactLevel.HIGH, ImpactLevel.CRITICAL):
                continue
            title = item.title.lower()
            if any(token.lower() in title for token in tokens):
                best = item
                break
        return best

    def _should_trigger_immediate_scan(self, market: str) -> bool:
        key = market.replace(" ", "").upper()
        try:
            if key in self.CRYPTO_MARKETS:
                snapshot = self._fetch_recent_crypto_snapshot(key)
                if snapshot["price"] <= 0:
                    return False
                if abs(snapshot["recent_pct"]) >= 0.005:
                    return True
                if snapshot["avg_volume"] > 0 and snapshot["volume"] >= snapshot["avg_volume"] * 3:
                    return True
            else:
                snapshot = self._fetch_recent_tradable_snapshot(key)
                if snapshot["price"] <= 0:
                    return False
                if abs(snapshot["pct_change"]) >= 0.004:
                    return True
                if snapshot["avg_volume"] > 0 and snapshot["volume"] >= snapshot["avg_volume"] * 3:
                    return True

            news_item = self._extract_relevant_news(key)
            if news_item is not None:
                return True
        except Exception:
            return False
        return False

    def _can_send_immediate_scan(self, market: str) -> bool:
        now = time.time()
        if now - self.last_immediate_scan.get(market, 0) >= 5 * 60:
            self.last_immediate_scan[market] = now
            return True
        return False

    def _check_immediate_events(self):
        now = time.time()
        if now - self.last_event_check < 15:
            return
        self.last_event_check = now

        for market in self.TIER1_MARKETS:
            if not self._can_send_immediate_scan(market):
                continue
            if self._should_trigger_immediate_scan(market):
                print(f"Immediate scan triggered for {market} due to live breakout or news")
                self.scan_markets([market], f"Immediate Scan ({market})")
                break

    def start(self):
        self.is_running = True
        print("VisionTrader Auto-Scanner Started...")
        while self.is_running:
            now = time.time()

            # Tier 1 (Every 5 minutes): highest frequency, WebSocket-enabled for live crypto.
            if now - self.last_run_l1 >= 5 * 60:
                self.scan_markets(self.TIER1_MARKETS, "Tier 1 (M5)")
                self.last_run_l1 = now

            # Tier 2 (Every 15 minutes): important FX, ETH, and major indices.
            if now - self.last_run_l2 >= 15 * 60:
                self.scan_markets(self.TIER2_MARKETS, "Tier 2 (M15)")
                self.last_run_l2 = now

            # Tier 3 (Every hour): lower-frequency crypto and remaining indices.
            if now - self.last_run_l3 >= 60 * 60:
                self.scan_markets(self.TIER3_MARKETS, "Tier 3 (H1)")
                self.last_run_l3 = now

            self._check_immediate_events()
            time.sleep(10)  # Heartbeat every 10 seconds

    def scan_markets(self, markets_to_scan, mode_name):
        print(f"[{mode_name}] Scanning {len(markets_to_scan)} markets at {datetime.datetime.now()}")
        user_list = self._get_active_users()
        watchlist_frequency = {}
        for user in user_list:
            db = SessionLocal()
            try:
                prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == user.id).first()
                if prefs:
                    try:
                        for symbol in json.loads(prefs.watchlist or "[]"):
                            watchlist_frequency[symbol] = watchlist_frequency.get(symbol, 0) + 1
                    except Exception:
                        continue
            finally:
                db.close()

        sorted_markets = sorted(
            markets_to_scan,
            key=lambda market: (-watchlist_frequency.get(market, 0), market)
        )

        for market in sorted_markets:
            try:
                simulated_visual = [
                    {"description": f"Market {market} analysis for {mode_name}. Trend analysis at {datetime.datetime.now()}."}
                ]
                
                cached_scan = cache_service.get_auto_scan(market, mode_name)
                if cached_scan is not None:
                    final_decision = cached_scan
                    print(f"Using cached auto-scan result for {market} ({mode_name})")
                else:
                    final_decision = voting_engine.analyze(simulated_visual)
                    cache_service.cache_auto_scan(market, mode_name, final_decision)
                
                rec = final_decision.get("recommendation", "محايد")
                conf = final_decision.get("confidence", 0)
                confluence_score = final_decision.get("confluence_score", 0)
                top_3 = final_decision.get("top_3_strategies", [])
                
                # Dynamic Threshold based on mode
                threshold = 85 if "Swing" in mode_name else 80
                if conf < threshold or rec not in ["شراء", "بيع"] or confluence_score < 2:
                    continue

                # Before notifying users, ensure we can build trade levels using live prices.
                try:
                    levels = self._build_trade_levels(market, rec)
                except Exception as e:
                    # If live price fetch fails for this market, skip it (do not use fake data).
                    print(f"Skipping {market} due to live price fetch failure: {e}")
                    continue

                for user in user_list:
                    try:
                        db = SessionLocal()
                        prefs = db.query(models.UserPreferences).filter(models.UserPreferences.user_id == user.id).first()
                        if not prefs:
                            prefs = models.UserPreferences(user_id=user.id)
                            db.add(prefs)
                            db.commit()
                            db.refresh(prefs)
                        if not self._is_market_relevant_to_user(prefs, mode_name, market):
                            continue

                        print(f"🔥 [{mode_name}] Alert for user {user.email} on {market}: {rec} ({conf}%)")
                        create_alert(
                            user_id=user.id,
                            market=market,
                            recommendation=rec,
                            confidence=conf,
                            entry="نطاق السعر الحالي",
                            sl="تحت منطقة السيولة",
                            tp="الهدف الأول",
                            top_strategies=", ".join(top_3)
                        )
                        if prefs.telegram_chat_id:
                            telegram_service.send_alert(prefs.telegram_chat_id, market, rec, conf, top_3)
                    except Exception as inner:
                        print(f"Error sending alert for user {user.email}: {inner}")
                    finally:
                        db.close()
            except Exception as e:
                print(f"Error scanning {market}: {e}")

    def _market_price_reference(self, market):
        key = market.replace(" ", "").upper()

        price = self._get_live_price(key)
        if not price or float(price) == 0.0:
            raise RuntimeError(f"Failed to fetch live price for {key}")

        decimals = self._get_price_decimals(float(price))
        return (float(price), decimals)

    def _format_price(self, value, decimals):
        return f"{value:.{decimals}f}"

    def _build_trade_levels(self, market, recommendation):
        base_price, decimals = self._market_price_reference(market)
        sl_offset = base_price * 0.005
        tp_offset = base_price * 0.015

        if recommendation == "شراء":
            entry = base_price
            sl = max(0.0, base_price - sl_offset)
            tp = base_price + tp_offset
        else:
            entry = base_price
            sl = base_price + sl_offset
            tp = max(0.0, base_price - tp_offset)

        return {
            "entry": self._format_price(entry, decimals),
            "sl": self._format_price(sl, decimals),
            "tp": self._format_price(tp, decimals)
        }

    def get_top_opportunities(self):
        opportunities = []
        for market in MARKETS:
            try:
                simulated_visual = [
                    {"description": f"Top opportunities scan for {market}. Detect best current trend."}
                ]
                result = voting_engine.analyze(simulated_visual)
                recommendation = result.get("recommendation", "محايد")
                confidence = int(result.get("confidence", 0))

                if recommendation not in ["شراء", "بيع"]:
                    continue

                levels = self._build_trade_levels(market, recommendation)
                opportunities.append({
                    "market": market,
                    "recommendation": recommendation,
                    "confidence": confidence,
                    "entry": levels["entry"],
                    "sl": levels["sl"],
                    "tp": levels["tp"]
                })
            except Exception as e:
                print(f"Error building opportunity for {market}: {e}")

        opportunities.sort(key=lambda item: item["confidence"], reverse=True)
        return opportunities[:3]

    def send_telegram_notification(self, market, rec, conf, top_3, mode):
        # In real app, import and use TelegramBot service
        print(f"Sending Telegram Alert for {market} ({mode})")

auto_scanner = AutoScanner()
