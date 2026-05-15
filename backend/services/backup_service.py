import shutil
import os
import datetime
import time

class BackupService:
    def __init__(self, db_path="visiontrader.db", backup_dir="backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def perform_backup(self):
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"backup_{timestamp}.db")
            shutil.copy2(self.db_path, backup_file)
            print(f"Database backed up to {backup_file}")
            self.clean_old_backups()
            return True
        except Exception as e:
            print(f"Backup failed: {e}")
            return False

    def clean_old_backups(self, keep=7):
        backups = sorted([f for f in os.listdir(self.backup_dir) if f.endswith(".db")])
        while len(backups) > keep:
            os.remove(os.path.join(self.backup_dir, backups.pop(0)))

backup_service = BackupService()
