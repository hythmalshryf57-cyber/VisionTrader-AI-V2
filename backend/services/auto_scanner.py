import time
import requests
import json
import os
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from services.cache_service import cache_service
from services.voting_engine import voting_engine
from services.alert_manager import create_alert
from services.telegram_service import telegram_service

MARKETS = [
    "BTCUSD", "ETHUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY",
    "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "GBP JPY", "EURJPY",
    "NAS100", "US30", "GER40", "UK100", "WTI", "SOLUSD"
]

class AutoScanner:
    def __init__(self):
        self.is_running = False
        self.last_run_l1 = 0
        self.last_run_l2 = 0
        self.last_run_l3 = 0

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

    def start(self):
        self.is_running = True
        print("VisionTrader Auto-Scanner Started...")
        while self.is_running:
            now = time.time()
            
            # Level 1 (Every 1 min): Scalping
            if now - self.last_run_l1 >= 60:
                self.scan_markets(["XAUUSD", "EURUSD"], "Scalping (M1/M5)")
                self.last_run_l1 = now
                
            # Level 2 (Every 15 min): Day Trading
            if now - self.last_run_l2 >= 15 * 60:
                major_markets = ["BTCUSD", "ETHUSD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
                self.scan_markets(major_markets, "Day Trading (M15/H1)")
                self.last_run_l2 = now
                
            # Level 3 (Every 4 hours): Swing Trading
            if now - self.last_run_l3 >= 4 * 3600:
                self.scan_markets(MARKETS, "Swing Trading (H4/D1)")
                self.last_run_l3 = now
                
            time.sleep(10) # Check every 10 seconds

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
        base_prices = {
            "BTCUSD": (62000.0, 2),
            "ETHUSD": (4200.0, 2),
            "XAUUSD": (1925.0, 2),
            "EURUSD": (1.0850, 5),
            "GBPUSD": (1.2710, 5),
            "USDJPY": (154.25, 3),
            "AUDUSD": (0.6500, 5),
            "NZDUSD": (0.6000, 5),
            "USDCAD": (1.3800, 5),
            "USDCHF": (0.9000, 5),
            "GBPJPY": (196.50, 3),
            "EURJPY": (167.30, 3),
            "NAS100": (16800.0, 1),
            "US30": (38000.0, 0),
            "GER40": (16850.0, 1),
            "UK100": (7600.0, 1),
            "WTI": (74.20, 2),
            "SOLUSD": (220.0, 2)
        }
        key = market.replace(" ", "").upper()
        return base_prices.get(key, (1000.0, 2))

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
