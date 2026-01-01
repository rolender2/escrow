from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import auth

# Ensure tables exist
models.Base.metadata.create_all(bind=engine)

def seed_users():
    db = SessionLocal()
    
    users = [
        {"username": "alice_agent", "role": models.UserRole.AGENT, "password": "password123"},
        {"username": "bob_contractor", "role": models.UserRole.CONTRACTOR, "password": "password123"},
        {"username": "jim_inspector", "role": models.UserRole.INSPECTOR, "password": "password123"},
        {"username": "title_co", "role": models.UserRole.CUSTODIAN, "password": "password123"},
        {"username": "admin", "role": models.UserRole.ADMIN, "password": "admin123"},
    ]

    print("Seeding Users...")
    for u in users:
        existing = db.query(models.User).filter(models.User.username == u["username"]).first()
        if not existing:
            print(f"Creating {u['username']} ({u['role']})")
            hashed = auth.get_password_hash(u["password"])
            db_user = models.User(
                username=u["username"],
                role=u["role"],
                hashed_password=hashed,
                organization_id="org_1"
            )
            db.add(db_user)
        else:
            print(f"Skipping {u['username']} (Already exists)")
    
    db.commit()
    db.close()
    print("Seeding Complete.")

if __name__ == "__main__":
    seed_users()
