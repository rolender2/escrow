import requests
import time
import datetime
from sqlalchemy import create_engine
import models
import database
import auth
from database import SessionLocal

# Configuration
BASE_URL = "http://localhost:8000"

# Note: We use SessionLocal from database directly


def get_token(username, password):
    response = requests.post(f"{BASE_URL}/token", data={"username": username, "password": password})
    if response.status_code != 200:
        print(f"Failed to login {username}: {response.text}")
        return None
    return response.json()["access_token"]

def seed_users():
    db = SessionLocal()
    users = [
        ("alice_agent", "password123", "AGENT"),
        ("title_co", "password123", "CUSTODIAN"),
        ("rob_inspector", "password123", "INSPECTOR"),
        ("rick_contractor", "password123", "CONTRACTOR")
    ]
    for username, password, role in users:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            print(f"Creating user {username}...")
            hashed_password = auth.get_password_hash(password)
            db_user = models.User(username=username, hashed_password=hashed_password, role=role)
            db.add(db_user)
        else:
            # Update password just in case
            user.hashed_password = auth.get_password_hash(password)
            user.role = role # Ensure role is correct
            
    db.commit()
    db.close()

def main():
    print("--- Starting Notification System Verification ---")
    
    # 0. Seed Users
    seed_users()
    
    # 1. Reset System
    print("\n[1] Resetting System...")
    requests.post(f"{BASE_URL}/reset", headers={"Authorization": f"Bearer {get_token('alice_agent', 'password123')}"})
    
    # Tokens
    agent_token = get_token("alice_agent", "password123")
    custodian_token = get_token("title_co", "password123")
    inspector_token = get_token("rob_inspector", "password123")
    
    # 2. Create Escrow (Agent) -> Should notify Custodian
    print("\n[2] Creating Escrow (Agent)...")
    escrow_data = {
        "buyer_id": "alice_buyer",
        "provider_id": "rick_contractor",
        "total_amount": 10000.0,
        "milestones": [
            {"name": "Step 1", "amount": 5000.0, "required_evidence_types": ["PHOTO"]},
            {"name": "Step 2", "amount": 5000.0, "required_evidence_types": ["PDF"]}
        ]
    }
    res = requests.post(f"{BASE_URL}/escrows", json=escrow_data, headers={"Authorization": f"Bearer {agent_token}"})
    if res.status_code != 200:
        print(f"Failed to create escrow: {res.text}")
        return
    escrow_id = res.json()["id"]
    print(f"Escrow Created: {escrow_id}")

    # Check Custodian Notification
    print("\n[Check] Verifying Custodian Notification (CREATE)...")
    res = requests.get(f"{BASE_URL}/notifications", headers={"Authorization": f"Bearer {custodian_token}"})
    notes = res.json()
    create_note = next((n for n in notes if n["escrow_id"] == escrow_id and n["event_type"] == "CREATE"), None)
    if create_note:
        print("PASS: Custodian received 'CREATE' notification.")
        print(f"Message: {create_note['message']} | Severity: {create_note['severity']}")
    else:
        print("FAIL: Custodian did NOT receive notification.")
        print(f"Notes found: {notes}")
            
    # Check Agent Notification (CREATE) - Added in Fix
    print("\n[Check] Verifying Agent Notification (CREATE)...")
    res = requests.get(f"{BASE_URL}/notifications", headers={"Authorization": f"Bearer {agent_token}"})
    notifications = res.json()
    if not notifications:
         # Note: This might fail if agent has older notifications from other runs
         # filter for this escrow
         my_notes = [n for n in notifications if n["escrow_id"] == escrow_id and n["event_type"] == "CREATE"]
         if not my_notes:
             print("FAIL: Agent received NO notifications for this escrow.")
         else:
             print("PASS: Agent received 'CREATE' notification.")
             print(f"Message: {my_notes[0]['message']}")
    else:
        # Check first or filter
        my_notes = [n for n in notifications if n["escrow_id"] == escrow_id and n["event_type"] == "CREATE"]
        if my_notes:
            print("PASS: Agent received 'CREATE' notification.")
            print(f"Message: {my_notes[0]['message']}")
        else:
            print(f"FAIL: Agent Notification mismatch. Got {notifications[0]['event_type']}")

    # 3. Confirm Funds (Custodian) -> Should notify Agent
    print("\n[3] Confirming Funds (Custodian)...")
    res = requests.post(f"{BASE_URL}/escrows/{escrow_id}/confirm_funds", 
                        json={"confirmation_code": "WIRE_123", "custodian_id": "title_co"}, 
                        headers={"Authorization": f"Bearer {custodian_token}"})
    if res.status_code != 200:
        print(f"Failed to funds: {res.text}")
        return

    # Check Agent Notification
    print("\n[Check] Verifying Agent Notification (FUNDS_CONFIRMED)...")
    res = requests.get(f"{BASE_URL}/notifications", headers={"Authorization": f"Bearer {agent_token}"})
    notes = res.json()
    fund_note = next((n for n in notes if n["escrow_id"] == escrow_id and n["event_type"] == "CONFIRM_FUNDS"), None)
    if fund_note:
        print("PASS: Agent received 'FUNDS_CONFIRMED' notification.")
    else:
        print("FAIL: Agent did NOT receive notification.")
        
    # 4. Upload Evidence (Contractor - skipped, using Agent mock setup or assume Contractor exists)
    # Actually need Contractor token
    contractor_token = get_token("rick_contractor", "password123")
    
    # Need Milestone ID
    res = requests.get(f"{BASE_URL}/escrows/{escrow_id}", headers={"Authorization": f"Bearer {agent_token}"})
    milestone = res.json()["milestones"][0]
    milestone_id = milestone["id"]
    required_type = milestone["required_evidence_types"][0]
    
    print(f"\n[4] Uploading Evidence (Contractor) for {required_type}...")
    # Using the new /upload endpoint
    files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
    res = requests.post(f"{BASE_URL}/milestones/{milestone_id}/evidence/upload", 
                        data={"evidence_type": required_type, "source_type": "PHOTO"},
                        files=files,
                        headers={"Authorization": f"Bearer {contractor_token}"})
    if res.status_code != 200:
        print(f"Failed to upload: {res.text}")
        # Could be status CREATED? Funds confirmed means milestones PENDING.
        pass
        
    # Explicit Submit (Finish Submission)
    print("\n[5] Finishing Submission (Contractor)...")
    res = requests.post(f"{BASE_URL}/milestones/{milestone_id}/submit", headers={"Authorization": f"Bearer {contractor_token}"})
    if res.status_code != 200:
        print(f"Submit failed: {res.text}")

    # Check Inspector Notification
    print("\n[Check] Verifying Inspector Notification (UPLOAD_EVIDENCE)...")
    res = requests.get(f"{BASE_URL}/notifications", headers={"Authorization": f"Bearer {inspector_token}"})
    notes = res.json()
    upload_note = next((n for n in notes if n["milestone_id"] == milestone_id and n["event_type"] == "UPLOAD_EVIDENCE"), None)
    if upload_note:
        print("PASS: Inspector received 'UPLOAD_EVIDENCE' notification.")
    else:
        print("FAIL: Inspector did NOT receive notification.")

    # 5. Mark Read
    if upload_note:
        print("\n[6] Marking Notification Read...")
        note_id = upload_note["_id"]
        requests.post(f"{BASE_URL}/notifications/{note_id}/read", headers={"Authorization": f"Bearer {inspector_token}"})
        
        # Verify Read
        res = requests.get(f"{BASE_URL}/notifications", headers={"Authorization": f"Bearer {inspector_token}"})
        updated_note = next((n for n in res.json() if n["_id"] == note_id), None)
        if updated_note and updated_note["is_read"]:
             print("PASS: Notification marked as read.")
        else:
             print("FAIL: Notification not marked read.")

    # 6. Verify Ledger
    print("\n[7] Verifying Audit Ledger for NOTIFICATION_ISSUED...")
    res = requests.get(f"{BASE_URL}/audit-logs", headers={"Authorization": f"Bearer {agent_token}"}) # Agent can view logs? Yes
    logs = res.json()
    notif_logs = [l for l in logs if l["event_type"] == "NOTIFICATION_ISSUED"]
    if len(notif_logs) >= 3:
        print(f"PASS: Found {len(notif_logs)} NOTIFICATION_ISSUED events in ledger.")
    else:
        print(f"FAIL: Found only {len(notif_logs)} notification events. Expected >= 3.")
        
    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    main()
