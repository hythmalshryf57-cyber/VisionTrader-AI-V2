import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from bot.telegram_bot import telegram_notifier
from services.multi_tf_analyzer import full_multi_tf_analysis

logger = logging.getLogger(__name__)

# List of symbols the sniper will monitor
SNIPER_SYMBOLS = ["XAUUSD", "BTCUSDT", "EURUSD", "GBPUSD"]
SNIPER_INTERVAL_MINUTES = 60
CONFIDENCE_THRESHOLD = 80

scheduler = AsyncIOScheduler()

async def sniper_job():
    """
    Background job to scan top pairs and send telegram alerts for high-confidence setups.
    """
    logger.info("🎯 Auto-Sniper Job started.")
    for symbol in SNIPER_SYMBOLS:
        try:
            logger.info(f"🎯 Sniper analyzing {symbol}...")
            # We'll use "يومي" (Daily) as the default trade type for these alerts
            result = await full_multi_tf_analysis(symbol, "يومي")
            
            confidence = result.get("final_analysis", {}).get("confidence", 0)
            recommendation = result.get("final_analysis", {}).get("recommendation", "Neutral")
            reason = result.get("final_analysis", {}).get("reason", "No details provided.")
            
            if confidence >= CONFIDENCE_THRESHOLD and recommendation.lower() not in ["neutral", "محايد"]:
                logger.info(f"🎯 Sniper found high-confidence setup on {symbol}: {recommendation} ({confidence}%)")
                await telegram_notifier.send_sniper_alert(
                    symbol=symbol,
                    trade_type="يومي",
                    recommendation=recommendation,
                    confidence=confidence,
                    reason=reason
                )
            else:
                logger.info(f"🎯 Sniper skipped {symbol}: Confidence {confidence}% < {CONFIDENCE_THRESHOLD}% or Neutral.")
                
            # Prevent rate-limits
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"🎯 Sniper error on {symbol}: {e}")

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            sniper_job,
            trigger=IntervalTrigger(minutes=SNIPER_INTERVAL_MINUTES),
            id="sniper_job",
            name="Auto-Sniper Market Scanner",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"⏳ Auto-Sniper Scheduler started (Interval: {SNIPER_INTERVAL_MINUTES}m).")

def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏳ Auto-Sniper Scheduler stopped.")
