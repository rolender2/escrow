import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def get_token(username, password):
    response = requests.post(f"{BASE_URL}/token", data={"username": username, "password": password})
    if response.status_code != 200:
        print(f"Failed to login {username}: {response.text}")
        sys.exit(1)
    return response.json()["access_token"]

def test_security():
    print("--- Starting Security Verification ---")
    
    # 1. Authenticate
    print("\n[1] Authenticating Users...")
    alice_token = get_token("alice_agent", "password123")
    bob_token = get_token("bob_contractor", "password123")
    jim_token = get_token("jim_inspector", "password123")
    title_token = get_token("title_co", "password123")
    print("Tokens acquired.")

    # 2. RBAC: Create Escrow (Agent Only)
    print("\n[2] Testing RBAC: Create Escrow")
    headers_alice = {"Authorization": f"Bearer {alice_token}"}
    headers_bob = {"Authorization": f"Bearer {bob_token}"}
    
    # Bob tries to create (Should Fail)
    res = requests.post(f"{BASE_URL}/escrows", headers=headers_bob, json={})
    if res.status_code == 403:
        print("PASS: Contractor blocked from creating escrow.")
    else:
        print(f"FAIL: Contractor NOT blocked (Status {res.status_code})")

    # Alice creates (Should Pass)
    escrow_data = {
        "buyer_id": "Buyer_1",
        "provider_id": "Provider_1",
        "total_amount": 1000.0,
        "milestones": [{"name": "Roof", "amount": 1000.0, "required_evidence_types": ["PHOTO"]}]
    }
    res = requests.post(f"{BASE_URL}/escrows", headers=headers_alice, json=escrow_data)
    if res.status_code == 200:
        escrow_id = res.json()["id"]
        milestone_id = res.json()["milestones"][0]["id"]
        print(f"PASS: Agent created escrow {escrow_id}")
    else:
        print(f"FAIL: Agent failed to create escrow: {res.text}")
        return

    # 3. One-Time Gate: Confirm Funds (Custodian Only)
    print("\n[3] Testing One-Time Gate")
    headers_title = {"Authorization": f"Bearer {title_token}"}
    
    # Confirm
    res = requests.post(f"{BASE_URL}/escrows/{escrow_id}/confirm_funds", headers=headers_title, json={"custodian_id": "title_co", "confirmation_code": "WIRE_123"})
    if res.status_code == 200:
        print("PASS: Custodian confirmed funds.")
    else:
         print(f"FAIL: Custodian check failed: {res.text}")

    # Replay (Should Fail)
    res = requests.post(f"{BASE_URL}/escrows/{escrow_id}/confirm_funds", headers=headers_title, json={"custodian_id": "title_co", "confirmation_code": "WIRE_123"})
    if res.status_code == 400:
        print("PASS: Duplicate confirmation rejected (One-Time Gate).")
    else:
        print(f"FAIL: Duplicate confirmation NOT rejected: {res.status_code}")

    # 4. Evidence (Contractor Only)
    print("\n[4] Testing Evidence Upload")
    res = requests.post(f"{BASE_URL}/milestones/{milestone_id}/evidence", headers=headers_bob, json={"evidence_type": "PHOTO", "url": "http://img.com/1.jpg"})
    if res.status_code == 200:
        print("PASS: Contractor uploaded evidence.")
    else:
        print(f"FAIL: Evidence upload failed: {res.text}")

    # 5. Approval (Inspector Only) & System Instruction
    print("\n[5] Testing Approval & System Instruction")
    headers_jim = {"Authorization": f"Bearer {jim_token}"}
    
    res = requests.post(f"{BASE_URL}/milestones/{milestone_id}/approve", headers=headers_jim, json={"approver_id": "ignored", "signature": "sig_123"})
    if res.status_code == 200:
        print("PASS: Inspector approved.")
        # Check backend state
        # The response is the milestone, verify status
        if res.json()["status"] == "PAID":
             print("PASS: Milestone Status transitioned to PAID.")
        else:
             print(f"FAIL: Milestone Status is {res.json()['status']}")
    else:
        print(f"FAIL: Approval failed: {res.text}")

    # 6. Verify Ledger (Instruction Generated?)
    print("\n[6] Verifying Ledger")
    # Anyone can read logs, maybe? No, let's use Alice
    res = requests.get(f"{BASE_URL}/audit-logs", headers=headers_alice)
    logs = res.json()
    # Look for PAYMENT_RELEASED
    payment_log = next((l for l in logs if l["event_type"] == "PAYMENT_RELEASED"), None)
    if payment_log:
        print("PASS: PAYMENT_RELEASED event found in ledger.")
        print(f"      Actor Role: {payment_log.get('actor_id')} (Should be SYSTEM/INSTRUCTION)")
    else:
        print("FAIL: No PAYMENT_RELEASED log found.")
        print("DEBUG: Available Event Types:", [l["event_type"] for l in logs[:5]])

    # 7. No Free Money
    print("\n[7] Testing 'No Free Money'")
    # Create new escrow
    res = requests.post(f"{BASE_URL}/escrows", headers=headers_alice, json=escrow_data)
    escrow_id_2 = res.json()["id"]
    ms_id_2 = res.json()["milestones"][0]["id"]
    
    # Upload evidence (allowed)
    requests.post(f"{BASE_URL}/milestones/{ms_id_2}/evidence", headers=headers_bob, json={"evidence_type": "PHOTO", "url": "http://img.com/2.jpg"})
    
    # Try to approve WITHOUT funding
    res = requests.post(f"{BASE_URL}/milestones/{ms_id_2}/approve", headers=headers_jim, json={"approver_id": "ign", "signature": "sig"})
    if res.status_code == 400:
        print("PASS: Unfunded approval rejected.")
    else:
        print(f"FAIL: Unfunded approval PASSED (Status {res.status_code})")

if __name__ == "__main__":
    try:
        import requests
        test_security()
    except ImportError:
        print("Requests library not found. Please install: pip install requests")
