from backend.database import SessionLocal
from backend import models
from datetime import datetime

db = SessionLocal()
user = db.query(models.User).filter(models.User.email=='testuser@example.com').first()
if not user:
    print('User not found')
else:
    user.trial_end = datetime(2100,1,1)
    db.add(user)
    db.commit()
    print('Extended trial_end for', user.email)
    print('trial_end now', user.trial_end)
db.close()
