import sqlite3, os
p = os.path.join(os.path.dirname(__file__), 'visiontrader.db')
conn = sqlite3.connect(p)
cur = conn.cursor()
cur.execute("UPDATE user_preferences SET daily_loss_limit_percent = 5.0 WHERE daily_loss_limit_percent = 10.0")
print('rows updated', cur.rowcount)
conn.commit()
conn.close()
