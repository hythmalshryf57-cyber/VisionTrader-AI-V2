from datetime import datetime
from typing import Any, Dict

class SyncBackupAgent:
    def __init__(self):
        self.name = "Sync Backup Agent"

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        backup_status = data.get("backup_status") or {}
        last_sync = backup_status.get("last_sync")
        last_backup = backup_status.get("last_backup")
        outage = backup_status.get("last_outage")

        now = datetime.utcnow()
        summary = []
        if last_sync:
            summary.append(f"آخر مزامنة: {last_sync}")
        else:
            summary.append("لم يتم التحقق من المزامنة الأخيرة.")
        if last_backup:
            summary.append(f"آخر نسخة احتياطية: {last_backup}")
        else:
            summary.append("لم يتم إنشاء نسخة احتياطية اليوم.")
        if outage:
            summary.append("استعادة تلقائية مطلوبة بعد انقطاع سابق.")

        report = " ".join(summary)
        signal = "neutral"
        confidence = 70 if last_backup else 30

        return {
            "agent": self.name,
            "signal": signal,
            "confidence": confidence,
            "report": report,
            "last_sync": last_sync,
            "last_backup": last_backup,
            "outage_detected": bool(outage),
        }
