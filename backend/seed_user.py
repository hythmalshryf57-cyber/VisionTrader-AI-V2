from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from auth import get_password_hash

def seed():
    db = SessionLocal()
    email = "test@test.com"
    password = "123456"
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        print(f"Creating user {email}...")
        hashed_password = get_password_hash(password)
        new_user = models.User(email=email, hashed_password=hashed_password)
        db.add(new_user)
        db.commit()
        print("User created successfully.")
    else:
        print(f"User {email} already exists.")
    db.close()

if __name__ == "__main__":
    seed()
