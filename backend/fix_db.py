from database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE trade_experience ADD COLUMN chart_features TEXT"))
        conn.commit()
        print("Added chart_features column successfully")
except Exception as e:
    print(f"Error: {e}")