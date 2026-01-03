import requests
import time
import models
import auth
from database import SessionLocal

# Configuration
BASE_URL = "http://localhost:8000"

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
            user.role = role
    db.commit()
    db.close()

def main():
    print("--- Starting Payment Layer Verification ---")
    
    # 0. Seed Users
    seed_users()
    
    # 1. Reset System
    print("\n[1] Resetting System...")
    requests.post(f"{BASE_URL}/reset", headers={"Authorization": f"Bearer {get_token('alice_agent', 'password123')}"})
    
    agent_token = get_token("alice_agent", "password123")
    custodian_token = get_token("title_co", "password123")
    inspector_token = get_token("rob_inspector", "password123")
    contractor_token = get_token("rick_contractor", "password123")
    
    # 2. Create Escrow
    print("\n[2] Creating Escrow...")
    escrow_data = {
        "buyer_id": "alice_buyer",
        "provider_id": "rick_contractor",
        "total_amount": 10000.0,
        "milestones": [{"name": "Milestone 1", "amount": 10000.0, "required_evidence_types": ["PHOTO"]}]
    }
    res = requests.post(f"{BASE_URL}/escrows", json=escrow_data, headers={"Authorization": f"Bearer {agent_token}"})
    escrow_id = res.json()["id"]
    milestone_id = res.json()["milestones"][0]["id"]
    print(f"Escrow Created: {escrow_id}")

    # 3. Fund
    print("\n[3] Funding Escrow...")
    requests.post(f"{BASE_URL}/escrows/{escrow_id}/confirm_funds", json={"confirmation_code": "WIRE", "custodian_id": "title_co"}, headers={"Authorization": f"Bearer {custodian_token}"})
    
    # 4. Contractor Work
    print("\n[4] Contractor Uploads Evidence...")
    files = {'file': ('proof.jpg', b'image data', 'image/jpeg')}
    requests.post(f"{BASE_URL}/milestones/{milestone_id}/evidence/upload", 
                 data={"evidence_type": "PHOTO", "source_type": "PHOTO"},
                 files=files,
                 headers={"Authorization": f"Bearer {contractor_token}"})
                 
    requests.post(f"{BASE_URL}/milestones/{milestone_id}/submit", headers={"Authorization": f"Bearer {contractor_token}"})
    
    # 5. Inspector Approve -> triggers Payment Instruction
    print("\n[5] Inspector Approves Release...")
    res = requests.post(f"{BASE_URL}/milestones/{milestone_id}/approve", 
                        json={"approver_id": "rob", "signature": "sig_123"},
                        headers={"Authorization": f"Bearer {inspector_token}"})
                        
    if res.status_code == 200:
        print("PASS: Milestone Approved.")
    else:
        print(f"FAIL: Approval Error: {res.text}")
        return

    # 6. Check Payment Instructions (Agent View)
    print("\n[6] Checking Payment Instructions (Agent)...")
    res = requests.get(f"{BASE_URL}/escrows/{escrow_id}/payment-instructions", headers={"Authorization": f"Bearer {agent_token}"})
    instructions = res.json()
    if not instructions:
        print("FAIL: No instructions found.")
        return
        
    instr = instructions[0]
    instr_id = instr["id"]
    print(f"Instruction Found: {instr['status']} | Amount: {instr['amount']}")
    
    if instr["status"] == "INSTRUCTED":
        print("PASS: Status is INSTRUCTED.")
    else:
        print(f"FAIL: Status is {instr['status']}")

    # 7. Custodian Marks SENT
    print(f"\n[7] Custodian Marks SENT ({instr_id})...")
    res = requests.post(f"{BASE_URL}/payment-instructions/{instr_id}/mark-sent", headers={"Authorization": f"Bearer {custodian_token}"})
    if res.status_code == 200:
        print("PASS: Mark SENT success.")
        if res.json()["status"] == "SENT":
            print("PASS: Status updated to SENT.")
    else:
        print(f"FAIL: Mark SENT error: {res.text}")

    # 8. Negative Test: Contractor tries to Mark SETTLED
    print("\n[8] Negative Test: Contractor tries to Mark SETTLED...")
    res = requests.post(f"{BASE_URL}/payment-instructions/{instr_id}/mark-settled", headers={"Authorization": f"Bearer {contractor_token}"})
    if res.status_code == 403:
        print("PASS: Contractor blocked (403).")
    else:
        print(f"FAIL: Contractor NOT blocked. Code: {res.status_code}")

    # 9. Custodian Marks SETTLED
    print(f"\n[9] Custodian Marks SETTLED...")
    res = requests.post(f"{BASE_URL}/payment-instructions/{instr_id}/mark-settled", headers={"Authorization": f"Bearer {custodian_token}"})
    if res.status_code == 200:
        print("PASS: Mark SETTLED success.")
    else:
        print(f"FAIL: Mark SETTLED error: {res.text}")

    # 10. Verify Notifications
    print("\n[10] Verifying Notifications...")
    res = requests.get(f"{BASE_URL}/notifications", headers={"Authorization": f"Bearer {agent_token}"})
    notifs = res.json()
    
    # Expect: INSTRUCTED, SENT, SETTLED
    types = [n["event_type"] for n in notifs if n["escrow_id"] == escrow_id]
    print(f"Notification Types Found: {types}")
    
    if "PAYMENT_INSTRUCTED" in types and "PAYMENT_SENT" in types and "PAYMENT_SETTLED" in types:
        print("PASS: All Payment Notifications received by Agent.")
    else:
        print("FAIL: Missing expected notifications.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    main()
