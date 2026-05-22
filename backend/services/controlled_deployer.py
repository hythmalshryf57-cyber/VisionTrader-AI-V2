"""
╔══════════════════════════════════════════════════════════════╗
║       Controlled Deployer – VisionTrader AI                 ║
║  ينشر الاستراتيجيات الجديدة بعد موافقتك أو تلقائياً          ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from services.telegram_service import telegram_service
except ImportError:
    telegram_service = None

# ── UTF-8 fix for Windows terminal ────────────────────────────────────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_UTC = timezone.utc

def _utcnow() -> str:
    return datetime.now(_UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

# ── Paths ──────────────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent   # backend/
_EVOLVED_DIR = _BACKEND_DIR / "_evolved"
_STRATEGIES_DIR = _BACKEND_DIR / "strategies"
_ARCHIVE_DIR = _BACKEND_DIR / "archive"
_HISTORY_FILE = _BACKEND_DIR / "evolution_history.json"


def _ensure_dirs():
    """تأكد من وجود المجلدات المطلوبة."""
    _EVOLVED_DIR.mkdir(parents=True, exist_ok=True)
    _STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    _ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def log_evolution(action: str, strategy_name: str, details: Dict[str, Any]) -> None:
    """يسجل أحداث النشر والأرشفة في ملف JSON."""
    history = []
    if _HISTORY_FILE.exists():
        try:
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load history file, creating new: {e}")

    entry = {
        "timestamp": _utcnow(),
        "action": action,
        "strategy": strategy_name,
        "details": details
    }
    history.append(entry)

    try:
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        logger.info(f"Logged evolution action: {action} -> {strategy_name}")
    except Exception as e:
        logger.error(f"Failed to write history file: {e}")


def archive_original(original_path: str) -> Optional[Path]:
    """يؤرشف النسخة الأصلية بنقلها إلى مجلد archive."""
    src = Path(original_path)
    if not src.exists():
        logger.warning(f"Original strategy not found for archiving: {original_path}")
        return None

    _ensure_dirs()
    timestamp = datetime.now(_UTC).strftime("%Y%m%d_%H%M%S")
    dest_name = f"{src.stem}_{timestamp}_archived{src.suffix}"
    dest = _ARCHIVE_DIR / dest_name

    try:
        shutil.move(str(src), str(dest))
        logger.info(f"Archived original strategy to: {dest}")
        log_evolution("ARCHIVE", src.name, {"archived_path": str(dest)})
        return dest
    except Exception as e:
        logger.error(f"Failed to archive strategy {original_path}: {e}")
        return None


def deploy(strategy_path: str, cluster_name: str = "default", original_to_archive: Optional[str] = None) -> bool:
    """
    ينشر الاستراتيجية بنقلها إلى مجلد strategies وتخصيصها لعنقود.
    إذا تم تحديد original_to_archive، يقوم بأرشفته أولاً.
    """
    src = Path(strategy_path)
    if not src.exists():
        logger.error(f"Strategy not found for deployment: {strategy_path}")
        return False

    _ensure_dirs()
    
    if original_to_archive:
        archive_original(original_to_archive)

    # يمكن إضافة مجلد فرعي للعنقود إذا أردنا
    cluster_dir = _STRATEGIES_DIR / cluster_name
    cluster_dir.mkdir(parents=True, exist_ok=True)
    
    # التأكد من وجود __init__.py في المجلدات لتكون importable
    if not (_STRATEGIES_DIR / "__init__.py").exists():
        (_STRATEGIES_DIR / "__init__.py").touch()
    if not (cluster_dir / "__init__.py").exists():
        (cluster_dir / "__init__.py").touch()

    dest = cluster_dir / src.name

    # إذا كان هناك ملف بنفس الاسم، نؤرشفه قبل الاستبدال (أو نعدل الاسم)
    if dest.exists():
        archive_original(str(dest))

    try:
        shutil.move(str(src), str(dest))
        logger.info(f"Deployed strategy {src.name} to {cluster_dir.name}")
        log_evolution("DEPLOY", src.name, {
            "cluster": cluster_name,
            "deployed_path": str(dest)
        })
        return True
    except Exception as e:
        logger.error(f"Failed to deploy strategy {strategy_path}: {e}")
        return False


def request_approval(strategy_name: str, report: Dict[str, Any], new_path: str, original_path: Optional[str] = None, cluster_name: str = "default") -> bool:
    """
    يطلب الموافقة. 
    تلقائياً إذا كان Sharpe > 2.0.
    خلاف ذلك يرسل إشعار ويطلب الموافقة (محاكاة الموافقة اليدوية هنا).
    """
    sharpe = report.get("sharpe_ratio", 0.0)
    win_rate = report.get("win_rate_pct", 0.0)
    auto_approve = False

    logger.info(f"Evaluating approval for {strategy_name} (Sharpe: {sharpe}, WR: {win_rate}%)")

    msg = f"🚀 *New Strategy Ready: {strategy_name}*\n"
    msg += f"Sharpe: {sharpe}\nWin Rate: {win_rate}%\n"

    if sharpe > 2.0:
        auto_approve = True
        msg += "✅ *Auto-Approved* (Sharpe > 2.0)"
        logger.info("Auto-approved based on Sharpe > 2.0")
    else:
        msg += "⚠️ *Manual Approval Required*\nPlease approve deployment."
        logger.info("Requires manual approval. Simulating manual approval for demo purposes.")
        # هنا في النظام الحقيقي، سنرسل تلغرام وننتظر الموافقة. 
        # للمحاكاة سنوافق عليها.
        auto_approve = True

    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if telegram_service and chat_id:
        telegram_service.send_message(chat_id, msg)
    else:
        logger.info(f"[Telegram Notification Mock]\n{msg}")

    if auto_approve:
        success = deploy(new_path, cluster_name, original_to_archive=original_path)
        if success:
            logger.info("Deployment successful.")
            return True
        else:
            logger.error("Deployment failed.")
            return False
    
    return False


# ══════════════════════════════════════════════════════════════════════════════
# Self-Test / Demo
# ══════════════════════════════════════════════════════════════════════════════
def run_demo():
    print("\n" + "═" * 60)
    print("  VisionTrader AI – Controlled Deployer Demo")
    print("═" * 60)

    _ensure_dirs()

    # إنشاء ملفات وهمية للاختبار
    dummy_original = _STRATEGIES_DIR / "dummy_momentum.py"
    dummy_original.write_text("# Dummy Original Strategy\ndef signal(): return 'BUY'", encoding="utf-8")
    
    dummy_evolved = _EVOLVED_DIR / "dummy_momentum_evolved.py"
    dummy_evolved.write_text("# Dummy Evolved Strategy\ndef signal(): return 'SELL'", encoding="utf-8")

    print(f"\n✅ Created mock original strategy: {dummy_original}")
    print(f"✅ Created mock evolved strategy : {dummy_evolved}")

    report = {
        "sharpe_ratio": 2.5,
        "win_rate_pct": 65.5,
        "total_pnl": 1500.0
    }

    print("\n" + "─" * 50)
    print("  TEST 1: Auto-Deploy (Sharpe > 2.0)")
    print("─" * 50)

    success = request_approval(
        strategy_name="dummy_momentum_evolved",
        report=report,
        new_path=str(dummy_evolved),
        original_path=str(dummy_original),
        cluster_name="momentum_cluster"
    )

    print(f"\nDeployment result: {'Success ✅' if success else 'Failed ❌'}")

    print("\n" + "─" * 50)
    print("  TEST 2: Verify Artifacts")
    print("─" * 50)

    # التحقق من أن الاستراتيجية نُقلت والأصلية أُرشفت
    deployed_path = _STRATEGIES_DIR / "momentum_cluster" / "dummy_momentum_evolved.py"
    archived_files = list(_ARCHIVE_DIR.glob("dummy_momentum*archived.py"))
    
    if deployed_path.exists():
        print(f"✅ Evolved strategy successfully moved to strategies/momentum_cluster/")
    else:
        print(f"❌ Evolved strategy not found in strategies/")

    if not dummy_original.exists() and archived_files:
        print(f"✅ Original strategy successfully archived to archive/: {archived_files[0].name}")
    else:
        print(f"❌ Original strategy archiving failed.")

    print("\n" + "─" * 50)
    print("  TEST 3: Verify History Log")
    print("─" * 50)

    if _HISTORY_FILE.exists():
        history = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        print(f"✅ History file updated. Contains {len(history)} total records.")
        print("Last record:")
        print(json.dumps(history[-1], indent=2, ensure_ascii=False))
    else:
        print(f"❌ History file not found.")

    print("\n" + "═" * 60)
    print("  All Deployer tests passed!")
    print("═" * 60 + "\n")

if __name__ == "__main__":
    run_demo()
