import requests
import sys
import os
import json

# Ensure we can import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import auth
import models
import database

BASE_URL = "http://localhost:8000"

def seed_users():
    db = database.SessionLocal()
    users = [
        {"username": "alice_agent", "role": "AGENT"},
        {"username": "bob_buyer", "role": "AGENT"}, # Reusing AGENT role as BUYER enum doesn't exist yet
        {"username": "carl_contractor", "role": "CONTRACTOR"},
        {"username": "charlie_custodian", "role": "CUSTODIAN"},
        {"username": "irene_inspector", "role": "INSPECTOR"}
    ]
    for u in users:
        if not db.query(models.User).filter(models.User.username == u["username"]).first():
            hashed = auth.get_password_hash("password") # Using simple password for tests
            # Note: UserRole Enum might need handling if strictly typed in DB insert, 
            # but usually strings work if Enum is defined in models.
            db_user = models.User(username=u["username"], role=u["role"], hashed_password=hashed)
            db.add(db_user)
            print(f"Adding user: {u['username']}")
    try:
        db.commit()
    except Exception as e:
        print(f"Error seeding users: {e}")
        db.rollback()
    db.close()
    print("Users seeded.")

def get_token(username, password):
    response = requests.post(f"{BASE_URL}/token", data={"username": username, "password": password})
    if response.status_code != 200:
        print(f"Failed to login as {username}")
        sys.exit(1)
    return response.json()["access_token"]

def verify():
    print("\n--- Verifying External Evidence Attestation ---")
    
    # 1. Setup Data
    print("\n1. Setting up new Escrow...")
    agent_token = get_token("alice_agent", "password")
    buyer_token = get_token("bob_buyer", "password")
    insp_token = get_token("irene_inspector", "password")
    contr_token = get_token("carl_contractor", "password")
    
    # Create Escrow
    headers_agent = {"Authorization": f"Bearer {agent_token}"}
    create_payload = {
        "buyer_id": "bob_buyer",
        "provider_id": "carl_contractor",
        "total_amount": 10000.0,
        "milestones": [
            {"name": "Foundation", "amount": 5000.0, "required_evidence_types": ["Photo"]},
        ]
    }
    
    escrow = requests.post(f"{BASE_URL}/escrows/", json=create_payload, headers=headers_agent).json()
    escrow_id = escrow["id"]
    milestone_id = escrow["milestones"][0]["id"]
    print(f"   Escrow Created: {escrow_id}")
    print(f"   Milestone ID: {milestone_id} (Status: {escrow['milestones'][0]['status']})")
    
    # 2. Fund Escrow (Active State)
    requests.post(f"{BASE_URL}/escrows/{escrow_id}/confirm_funds", 
                  headers={"Authorization": f"Bearer {get_token('charlie_custodian', 'password')}"}, 
                  json={"custodian_id": "charlie", "confirmation_code": "WIRE_123"})
    
    # 3. [NEGATIVE] Contractor Attempts External Evidence
    print("\n2. [Test] Contractor attempts to attach External Evidence (Expect 403)...")
    headers_contr = {"Authorization": f"Bearer {contr_token}"}
    files = {'file': ('test.pdf', b'%PDF-1.4 mock content', 'application/pdf')}
    res = requests.post(
        f"{BASE_URL}/milestones/{milestone_id}/external-evidence",
        files=files,
        data={"source_type": "PDF"},
        headers=headers_contr
    )
    if res.status_code == 403:
        print("   ✅ SUCCESS: Contractor blocked (403).")
    else:
        print(f"   ❌ FAILURE: Unexpected Status {res.status_code}")
        
    # 4. [POSITIVE] Inspector Attaches Evidence
    print("\n3. [Test] Inspector attaches External Evidence (Expect 200)...")
    headers_insp = {"Authorization": f"Bearer {insp_token}"}
    # Reset file pointer or recreate
    files = {'file': ('inspection_report.pdf', b'%PDF-1.4 mock content', 'application/pdf')}
    res = requests.post(
        f"{BASE_URL}/milestones/{milestone_id}/external-evidence",
        files=files,
        data={"source_type": "PDF"},
        headers=headers_insp
    )
    
    if res.status_code == 200:
        data = res.json()
        print(f"   ✅ SUCCESS: Evidence Attached. URL: {data['url']}")
        if data['origin'] == 'THIRD_PARTY':
            print("   ✅ SUCCESS: Origin is correctly THIRD_PARTY")
        else:
            print(f"   ❌ FAILURE: Origin is {data['origin']}")
    else:
        print(f"   ❌ FAILURE: {res.text}")
        
    # 5. Verify Ledger
    print("\n4. Verifying Audit Log Attestation...")
    logs = requests.get(f"{BASE_URL}/audit-logs").json()
    attestation = next((l for l in logs if l["event_type"] == "EVIDENCE_ATTESTED" and l["event_data"]["milestone_id"] == milestone_id), None)
    
    if attestation:
        print(f"   ✅ FOUND: Ledger Entry for EVIDENCE_ATTESTED")
        print(f"      Actor: {attestation['actor_id']}")
        print(f"      Origin: {attestation['event_data']['origin']}")
    else:
        print("   ❌ FAILURE: Ledger entry not found.")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    seed_users()
    verify()
