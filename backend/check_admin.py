from database import SessionLocal
import models

db = SessionLocal()
user = db.query(models.User).filter(models.User.email=='hythmalshryf57@gmail.com').first()
print('exists', bool(user))
if user:
    print('id', user.id, 'is_admin', user.is_admin, 'trial_end', user.trial_end)
db.close()
