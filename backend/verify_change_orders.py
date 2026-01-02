import requests
import json
import sys
import os

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
        {"username": "title_co", "role": "CUSTODIAN"},
        {"username": "inspector_gadget", "role": "INSPECTOR"}
    ]
    for u in users:
        if not db.query(models.User).filter(models.User.username == u["username"]).first():
            # hash password 'password123'
            hashed = auth.get_password_hash("password123")
            db_user = models.User(username=u["username"], role=u["role"], hashed_password=hashed)
            db.add(db_user)
    db.commit()
    db.close()
    print("Users seeded.")

def get_auth_headers(username, role="AGENT"):
    # Generate real JWT locally using shared secret
    token = auth.create_access_token(data={"sub": username, "role": role})
    return {"Authorization": f"Bearer {token}"}

def create_escrow(amount=5000):
    # Create
    # Create
    res = requests.post(f"{BASE_URL}/escrows", 
        headers=get_auth_headers("alice_agent", "AGENT"),
        json={
        "buyer_id": "buyer_bob",
        "provider_id": "provider_pat",
        "total_amount": amount,
        "milestones": [
            {"name": "Phase 1", "amount": amount, "required_evidence_types": ["Invoice"]}
        ]
    })
    if res.status_code != 200:
        print("Create failed", res.text)
        exit(1)
    return res.json()['id']

def confirm_funds(escrow_id):
    res = requests.post(
        f"{BASE_URL}/escrows/{escrow_id}/confirm_funds", 
        headers=get_auth_headers("title_co", "CUSTODIAN"),
        json={"custodian_id": "title_co", "confirmation_code": "WIRE_123"}
    )
    if res.status_code != 200:
        print("Confirm failed", res.text)
        exit(1)

def verify_state(escrow_id, expected_state):
    res = requests.get(f"{BASE_URL}/escrows/{escrow_id}")
    state = res.json()['state']
    if state != expected_state:
        print(f"❌ State Mismatch: Got {state}, Expected {expected_state}")
        exit(1)
    print(f"✅ State Verified: {state}")

def verify_budget_change():
    """
    Scenario 5 (Refined): Budget Change (Append-Only, No Reset)
    1. Create & Fund Escrow ($5000). State -> FUNDED.
    2. Add Budget Change (+$1500).
    3. Verify:
       - Total Amount = 6500.
       - Funded Amount = 5000.
       - State = FUNDED (Not Reset).
       - New Milestone Status = CREATED.
       - Audit Log = CHANGE_ORDER_ADDED.
    4. Confirm Funds (Delta).
       - Funded Amount = 6500.
       - New Milestone Status = PENDING.
    """
    print("\n--- Testing Budget Change Order (Append-Only) ---")
    
    # 1. Create & Fund
    escrow_id = create_escrow(5000)
    confirm_funds(escrow_id)
    verify_state(escrow_id, "FUNDED")
    
    e = requests.get(f"{BASE_URL}/escrows/{escrow_id}").json()
    print(f"Initial: Total=${e['total_amount']}, Funded=${e.get('funded_amount', 0)}")

    # 2. Change Budget (Append-Only)
    print("\n[Action] Requesting Budget Increase (+1500)...")
    res = requests.post(
        f"{BASE_URL}/escrows/{escrow_id}/change-budget",
        headers=get_auth_headers("alice_agent", "AGENT"),
        json={
            "amount_delta": 1500,
            "milestone_name": "Extra Grid Work",
            "evidence_type": "Invoice"
        }
    )
    if res.status_code != 200:
        print(f"Failed to change budget: {res.text}")
        exit(1)
        
    e = requests.get(f"{BASE_URL}/escrows/{escrow_id}").json()
    
    # 3. Verify No Reset
    print(f"Post-Change: Total=${e['total_amount']}, Funded=${e.get('funded_amount', 0)}")
    
    if e['state'] != "FUNDED":
        print(f"❌ FAIL: State reset to {e['state']}. Should remain FUNDED.")
        exit(1)
    else:
        print("✅ PASS: State preserved (No Reset).")
        
    if e['total_amount'] != 6500:
        print(f"❌ FAIL: Total amount mismatch {e['total_amount']}")
        exit(1)
        
    # Check Milestone Status
    new_ms = e['milestones'][-1]
    if new_ms['status'] != "CREATED":
        print(f"❌ FAIL: New milestone status is {new_ms['status']}, expected CREATED")
        exit(1)
    else:
        print(f"✅ PASS: New milestone '{new_ms['name']}' is CREATED (Waiting for funds).")

    # Check Audit Log
    logs = requests.get(f"{BASE_URL}/audit-logs").json()
    change_log = next((l for l in logs if l['event_type'] == "CHANGE_ORDER_ADDED" and l['entity_id'] == escrow_id), None)
    if not change_log:
        print("❌ FAIL: No CHANGE_ORDER_ADDED log found.")
        exit(1)
    else:
        print(f"✅ PASS: Audit Log found: {change_log['event_type']}")
        
    # 4. Confirm Delta Funds
    print("\n[Action] Confirming Delta Funds...")
    # Custodian validates the delta wired.
    res = requests.post(
        f"{BASE_URL}/escrows/{escrow_id}/confirm_funds",
        headers=get_auth_headers("title_co", "CUSTODIAN"),
        json={
            "custodian_id": "title_co",
            "confirmation_code": "WIRE_DELTA_123"
        }
    )
    if res.status_code != 200:
        print(f"Failed to confirm funds: {res.text}")
        exit(1)
        
    e = requests.get(f"{BASE_URL}/escrows/{escrow_id}").json()
    print(f"Post-Confirm: Total=${e['total_amount']}, Funded=${e.get('funded_amount', 0)}")

    if e['funded_amount'] != 6500:
        print(f"❌ FAIL: Funded amount not updated. Got {e['funded_amount']}")
        exit(1)
        
    new_ms = e['milestones'][-1]
    if new_ms['status'] != "PENDING":
        print(f"❌ FAIL: Milestone status didn't update to PENDING. Got {new_ms['status']}")
        exit(1)
    else:
        print("✅ PASS: New funds confirmed. Work active.")

if __name__ == "__main__":
    seed_users()
    verify_budget_change()
