import sqlite3
conn = sqlite3.connect('visiontrader.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print(tables)
for name, in tables:
    print('table', name)
conn.close()
