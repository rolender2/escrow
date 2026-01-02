from sqlalchemy.orm import Session
from database import SessionLocal
import models
import auth

def fix_alice():
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.username == "alice_agent").first()
    if user:
        print(f"Updating password for {user.username}...")
        user.hashed_password = auth.get_password_hash("password123")
        db.commit()
        print("Password updated to 'password123'")
    else:
        print("User alice_agent not found!")
    db.close()

if __name__ == "__main__":
    fix_alice()
