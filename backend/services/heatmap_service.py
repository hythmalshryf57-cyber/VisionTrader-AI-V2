import asyncio
import yfinance as yf
import logging
from typing import List, Dict, Any
from services.binance_service import binance_service

logger = logging.getLogger(__name__)

# Define our heatmap universe
CRYPTO_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
FOREX_METALS = {
    "XAUUSD": "GC=F", # Gold futures or XAUUSD=X
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "US30": "^DJI",
    "NAS100": "^NDX"
}

def _calculate_rsi(prices: List[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_crypto_data(symbol: str) -> Dict[str, Any]:
    try:
        klines = binance_service.get_klines(symbol, interval="1d", limit=20)
        if not klines or len(klines) < 2:
            return None
        
        current_price = float(klines[-1][4])
        open_price = float(klines[-1][1])
        prev_close = float(klines[-2][4])
        
        change_24h = ((current_price - prev_close) / prev_close) * 100
        
        closes = [float(k[4]) for k in klines]
        rsi = _calculate_rsi(closes)
        
        return {
            "symbol": symbol,
            "type": "crypto",
            "price": current_price,
            "change_24h": round(change_24h, 2),
            "rsi": round(rsi, 2)
        }
    except Exception as e:
        logger.error(f"Error fetching crypto data for {symbol}: {e}")
        return None

def get_yfinance_data(display_symbol: str, yf_symbol: str) -> Dict[str, Any]:
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="1mo")
        if hist.empty or len(hist) < 2:
            return None
            
        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        change_24h = ((current_price - prev_close) / prev_close) * 100
        
        closes = hist['Close'].tolist()
        rsi = _calculate_rsi(closes)
        
        return {
            "symbol": display_symbol,
            "type": "forex_metal",
            "price": round(current_price, 5) if "USD" in display_symbol else round(current_price, 2),
            "change_24h": round(change_24h, 2),
            "rsi": round(rsi, 2)
        }
    except Exception as e:
        logger.error(f"Error fetching yfinance data for {yf_symbol}: {e}")
        return None

async def generate_heatmap_data() -> List[Dict[str, Any]]:
    heatmap = []
    
    # Process Crypto (can be sync since binance_service uses requests)
    for sym in CRYPTO_PAIRS:
        data = get_crypto_data(sym)
        if data:
            heatmap.append(data)
            
    # Process Forex/Metals
    for sym, yf_sym in FOREX_METALS.items():
        data = get_yfinance_data(sym, yf_sym)
        if data:
            heatmap.append(data)
            
    # Calculate score/color based on RSI and Change
    for item in heatmap:
        score = 0
        if item["change_24h"] > 1.5: score += 2
        elif item["change_24h"] > 0: score += 1
        elif item["change_24h"] < -1.5: score -= 2
        elif item["change_24h"] < 0: score -= 1
        
        if item["rsi"] > 70: score -= 2 # Overbought, bearish signal
        elif item["rsi"] > 60: score += 1
        elif item["rsi"] < 30: score += 2 # Oversold, bullish signal
        elif item["rsi"] < 40: score -= 1
        
        if score >= 2:
            item["color"] = "green"
            item["status"] = "Strong Buy"
        elif score <= -2:
            item["color"] = "red"
            item["status"] = "Strong Sell"
        elif score > 0:
            item["color"] = "lightgreen"
            item["status"] = "Buy"
        elif score < 0:
            item["color"] = "lightcoral"
            item["status"] = "Sell"
        else:
            item["color"] = "gray"
            item["status"] = "Neutral"
            
    return heatmap
