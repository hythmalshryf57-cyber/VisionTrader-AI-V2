import os
import sys

# Ensure backend package root is on sys.path so imports like `database` work when
# running this script from the `scripts/` folder.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database import SessionLocal
from models import User, UserPreferences
from auth import get_password_hash, create_access_token
from datetime import datetime, timedelta

DB = SessionLocal()

def ensure_test_user(email: str = "integration_test@example.com", password: str = "TestPass123!"):
    user = DB.query(User).filter(User.email == email).first()
    if user:
        return user
    hashed = get_password_hash(password)
    trial_start = datetime.utcnow()
    trial_end = trial_start + timedelta(days=7)
    new_user = User(
        email=email,
        hashed_password=hashed,
        invite_code=None,
        ip_address='127.0.0.1',
        is_active=True,
        is_admin=False,
        trial_start=trial_start,
        trial_end=trial_end,
        daily_analyses_count=0,
        has_used_trial=True
    )
    DB.add(new_user)
    DB.commit()
    DB.refresh(new_user)
    default_prefs = UserPreferences(
        user_id=new_user.id,
        theme='dark',
        language='ar',
        demo_mode=False,
        demo_balance=1000000.0,
        trading_mode='day',
        capital=10000.0,
        account_balance=10000.0,
        risk_percentage=1.0,
        favorite_strategies='[]',
        watchlist='[]'
    )
    DB.add(default_prefs)
    DB.commit()
    return new_user

if __name__ == '__main__':
    user = ensure_test_user()
    token = create_access_token({"sub": str(user.id), "user_id": user.id, "email": user.email})
    print(token)
