from database import SessionLocal
import models

def main():
    s = SessionLocal()
    users = s.query(models.User).all()
    print('USERS_COUNT', len(users))
    for u in users:
        print(u.id, u.email, getattr(u, 'is_admin', False), getattr(u, 'hashed_password', None) is not None)
    s.close()


if __name__ == '__main__':
    main()
