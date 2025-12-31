
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Escrow
from backend.database import SQLALCHEMY_DATABASE_URL
from pymongo import MongoClient

def check_dbs():
    print("Checking PostgreSQL...")
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        escrows = db.query(Escrow).all()
        print(f"Found {len(escrows)} escrows in PostgreSQL table 'escrows'.")
        for e in escrows:
            print(f" - {e.id} ({e.state})")
        db.close()
    except Exception as e:
        print(f"Error checking PostgreSQL: {e}")

    print("\nChecking MongoDB...")
    try:
        mongo_client = MongoClient("mongodb://localhost:27017/")
        db = mongo_client["escrow_ledger"]
        collections = db.list_collection_names()
        print(f"Collections in 'escrow_ledger': {collections}")
        
        if "audit_logs" in collections:
            count = db["audit_logs"].count_documents({})
            print(f"Found {count} documents in 'audit_logs'.")
    except Exception as e:
        print(f"Error checking MongoDB: {e}")

if __name__ == "__main__":
    check_dbs()
