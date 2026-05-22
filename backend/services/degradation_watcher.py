"""
╔══════════════════════════════════════════════════════════════╗
║       Degradation Watcher – VisionTrader AI                 ║
║  يراقب تدهور الاستراتيجيات ويبدأ دورة التطور تلقائياً        ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import shutil
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_STRATEGIES_DIR = _BACKEND_DIR / "strategies"
_FROZEN_DIR = _BACKEND_DIR / "frozen"
_ARCHIVE_DIR = _BACKEND_DIR / "archive"
_EVOLVED_DIR = _BACKEND_DIR / "_evolved"

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from services.telegram_service import telegram_service
except ImportError:
    telegram_service = None

try:
    from database import SessionLocal
    from models import StrategyPerformance, TradeExperience
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False
    logger.warning("Database imports failed. Using mock data for demo.")

try:
    from services.strategy_generator import generate_from_failure
    from services.sandbox_tester import test_strategy, generate_report, compare_with_best_active
    from services.controlled_deployer import request_approval
    _EVOLUTION_PIPELINE_AVAILABLE = True
except ImportError as e:
    _EVOLUTION_PIPELINE_AVAILABLE = False
    logger.warning(f"Evolution pipeline components missing: {e}")


def _ensure_dirs():
    _STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    _FROZEN_DIR.mkdir(parents=True, exist_ok=True)
    _ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    _EVOLVED_DIR.mkdir(parents=True, exist_ok=True)


class DegradationWatcher:
    def __init__(self, interval_minutes: int = 30):
        self.interval = interval_minutes * 60
        self._running = False
        self._thread = None
        _ensure_dirs()

    def start(self):
        """يبدأ دورة المراقبة في Thread منفصل."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"Degradation Watcher started. Checking every {self.interval/60} minutes.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Degradation Watcher stopped.")

    def _run_loop(self):
        while self._running:
            try:
                self.watch()
            except Exception as e:
                logger.error(f"Error in watch cycle: {e}")
            
            # Sleep in chunks to allow responsive stopping
            for _ in range(int(self.interval)):
                if not self._running:
                    break
                time.sleep(1)

    def watch(self, demo_mode=False):
        """دورة المراقبة الرئيسية."""
        logger.info("Running degradation check cycle...")
        bad_strategies = self._scan_strategies(demo_mode)
        
        for strategy_name, reason in bad_strategies.items():
            logger.warning(f"Strategy {strategy_name} degraded. Reason: {reason}")
            self.freeze_strategy(strategy_name)
            self.send_alert(strategy_name, reason)
            
            # Simulate user choosing "1-تعديل/توليد"
            logger.info(f"Simulating user approval to evolve {strategy_name}...")
            self.start_evolution_cycle(strategy_name, reason)

    def _scan_strategies(self, demo_mode=False) -> Dict[str, str]:
        """
        يفحص جميع الاستراتيجيات ويعيد القاموس بالاستراتيجيات الفاشلة وسبب الفشل.
        """
        bad = {}
        if demo_mode or not _DB_AVAILABLE:
            # Mock scanning for demo purposes
            logger.info("Scanning (MOCK)...")
            # Pretend we found a failing strategy if the mock file exists
            dummy_strat = _STRATEGIES_DIR / "failing_strategy.py"
            if dummy_strat.exists():
                bad["failing_strategy"] = "Win rate dropped to 25% (threshold < 30%)"
            return bad

        # Real DB scanning
        db = SessionLocal()
        try:
            performances = db.query(StrategyPerformance).all()
            for perf in performances:
                total_trades = perf.wins + perf.losses
                if total_trades >= 10:
                    win_rate = (perf.wins / total_trades) * 100
                    if win_rate < 30.0:
                        bad[perf.strategy_name] = f"Win rate is critically low: {win_rate:.1f}%"
                        continue

                # Check consecutive losses in TradeExperience
                # (We'd need a robust query to find consecutive losses for THIS strategy, simplified here)
                recent_trades = db.query(TradeExperience).filter(
                    TradeExperience.strategy_names.like(f"%{perf.strategy_name}%")
                ).order_by(TradeExperience.created_at.desc()).limit(5).all()

                if len(recent_trades) == 5 and all("loss" in (t.result or "").lower() for t in recent_trades):
                    bad[perf.strategy_name] = "Failed 5 consecutive times."
        except Exception as e:
            logger.error(f"DB Scan error: {e}")
        finally:
            db.close()

        return bad

    def freeze_strategy(self, strategy_name: str):
        """يجمد استراتيجية بنقلها لمجلد frozen/."""
        # البحث عن الملف في strategies أو مجلداتها الفرعية
        found = False
        for py_file in _STRATEGIES_DIR.rglob("*.py"):
            if py_file.stem == strategy_name:
                try:
                    dest = _FROZEN_DIR / py_file.name
                    shutil.move(str(py_file), str(dest))
                    logger.info(f"Frozen strategy: {strategy_name} -> {dest}")
                    found = True
                except Exception as e:
                    logger.error(f"Failed to freeze {strategy_name}: {e}")
        
        if not found:
            logger.warning(f"Could not find file for strategy {strategy_name} to freeze.")

    def send_alert(self, strategy_name: str, reason: str):
        """يرسل تنبيه للتليجرام."""
        msg = (
            f"⚠️ *استراتيجية متدهورة: {strategy_name}*\n"
            f"السبب: {reason}\n\n"
            f"تم تجميد الاستراتيجية مؤقتاً.\n"
            f"ماذا تريد أن تفعل؟\n"
            f"1️⃣ تعديل وبدء دورة التطور\n"
            f"2️⃣ إبقاء التجميد"
        )
        
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if telegram_service and chat_id:
            telegram_service.send_message(chat_id, msg)
            logger.info(f"Telegram alert sent for {strategy_name}")
        else:
            logger.info(f"[Telegram Mock Alert]\n{msg}")

    def start_evolution_cycle(self, strategy_name: str, reason: str):
        """دورة التطور: Generator -> Tester -> Deployer"""
        if not _EVOLUTION_PIPELINE_AVAILABLE:
            logger.error("Evolution pipeline components not available. Cannot evolve.")
            return

        frozen_path = _FROZEN_DIR / f"{strategy_name}.py"
        if not frozen_path.exists():
            logger.error(f"Cannot evolve: Frozen file {frozen_path} not found.")
            return

        logger.info(f"=== Starting Evolution Cycle for {strategy_name} ===")

        # 1. Generate (Strategy Generator)
        failure_report = {
            "type": "performance_degradation",
            "reason": reason,
            "time": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info("[Step 1] Generating evolved strategy...")
        evolved_code, saved_path = generate_from_failure(
            failed_strategy_path=str(frozen_path),
            failure_report=failure_report,
            top_successful_strategies=[]  # We can inject top strategies here from DB if needed
        )

        if not saved_path:
            logger.error("Failed to generate evolved strategy.")
            return

        # 2. Test (Sandbox Tester)
        logger.info("[Step 2] Testing evolved strategy in Sandbox...")
        new_results = test_strategy(str(saved_path), days=5)
        
        # 3. Deploy (Controlled Deployer)
        logger.info("[Step 3] Requesting deployment approval...")
        # We pass the original frozen path as the one to be archived formally
        success = request_approval(
            strategy_name=saved_path.stem,
            report=new_results,
            new_path=str(saved_path),
            original_path=str(frozen_path),
            cluster_name="evolved_cluster"
        )

        if success:
            logger.info(f"=== Evolution Cycle Complete: {strategy_name} successfully evolved and deployed ===")
        else:
            logger.warning(f"=== Evolution Cycle Paused: {strategy_name} requires manual approval or failed deployment ===")


# ══════════════════════════════════════════════════════════════════════════════
# Self-Test / Demo
# ══════════════════════════════════════════════════════════════════════════════
def run_demo():
    print("\n" + "═" * 60)
    print("  VisionTrader AI – Degradation Watcher Demo")
    print("═" * 60)

    _ensure_dirs()
    
    # 1. إنشاء استراتيجية فاشلة وهمية في مجلد strategies
    dummy_failing = _STRATEGIES_DIR / "failing_strategy.py"
    dummy_failing.write_text(
        "\"\"\"Mock failing strategy\"\"\"\n"
        "def generate_signal(price, **kwargs):\n"
        "    return 'BUY', price * 0.99\n",
        encoding="utf-8"
    )
    print(f"✅ Created mock failing strategy: {dummy_failing}")

    # 2. تشغيل المراقب (لمرة واحدة بدلاً من دورة لا نهائية للاختبار)
    print("\n" + "─" * 50)
    print("  Running Degradation Check Cycle")
    print("─" * 50)
    
    watcher = DegradationWatcher()
    watcher.watch(demo_mode=True)

    print("\n" + "─" * 50)
    print("  Verifying Results")
    print("─" * 50)

    if not dummy_failing.exists() and (_FROZEN_DIR / "failing_strategy.py").exists():
        print("✅ Failing strategy successfully FROZEN (moved to frozen/).")
    else:
        print("❌ Failed to freeze strategy.")

    # Check if evolved strategy was created and deployed
    evolved_files = list((_STRATEGIES_DIR / "evolved_cluster").glob("evolved_failing_strategy*.py"))
    if evolved_files:
        print(f"✅ Evolved strategy successfully deployed: {evolved_files[0].name}")
    else:
        print("⚠️ Evolved strategy deployment pending manual approval or failed.")

    print("\n" + "═" * 60)
    print("  Degradation Watcher Demo Complete!")
    print("═" * 60 + "\n")

if __name__ == "__main__":
    run_demo()
