from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///visiontrader.db')
with engine.connect() as conn:
    conn.execute(text("UPDATE users SET is_admin=1 WHERE email='copilot_test_user@local.example'"))
    conn.commit()
print('updated')
