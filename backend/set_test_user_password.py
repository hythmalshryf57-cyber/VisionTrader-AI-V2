from sqlalchemy import create_engine, text
from auth import get_password_hash

engine = create_engine('sqlite:///visiontrader.db')
password = 'TestPassword123!'
hashed = get_password_hash(password)
with engine.connect() as conn:
    conn.execute(text("UPDATE users SET hashed_password = :hashed WHERE email = :email"), {"hashed": hashed, "email": "copilot_test_user@local.example"})
    conn.commit()
print('password updated for copilot_test_user@local.example')
