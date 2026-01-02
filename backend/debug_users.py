
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import models
import database

def check_users():
    db = database.SessionLocal()
    users = db.query(models.User).all()
    print(f"Total Users: {len(users)}")
    for u in users:
        print(f" - {u.username} ({u.role})")
    db.close()

if __name__ == "__main__":
    check_users()
