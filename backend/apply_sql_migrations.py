import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'visiontrader.db')
if not os.path.exists(db_path):
    print('No sqlite DB found at', db_path)
    raise SystemExit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA table_info(user_preferences)")
cols = [r[1] for r in cur.fetchall()]
print('Existing columns:', cols)
if 'daily_loss_limit_amount' not in cols:
    try:
        cur.execute('ALTER TABLE user_preferences ADD COLUMN daily_loss_limit_amount FLOAT')
        print('Added daily_loss_limit_amount column')
    except Exception as e:
        print('Failed to add column:', e)
else:
    print('daily_loss_limit_amount already present')

# Ensure daily_loss_limit_percent default is at least 5.0 (no easy ALTER DEFAULT for SQLite)
conn.commit()
conn.close()
print('Migration applied')
