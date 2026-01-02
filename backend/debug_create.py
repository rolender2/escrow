import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import models
import database
import traceback
from models import Escrow, Milestone, EscrowState, MilestoneStatus, UserRole
import main # Ensure main is imported to init mongo

def test_attestation():
    db = database.SessionLocal()
    try:
        print("Testing create_attestation...")
        
        # Check Mongo
        print("Mongo status:", main.mongo_client.server_info())
        
        main.create_attestation(
             db, "test_entity", models.AuditEvent.CREATE, "alice", models.UserRole.AGENT, 
             {"foo": "bar"}, "hash123", 1
        )
        print("Attestation Success!")
        
    except Exception as e:
        print("Attestation FAILED:")
        print(e)
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_attestation()
