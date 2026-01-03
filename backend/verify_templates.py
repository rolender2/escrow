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

def main():
    print("--- Starting Milestone Templates Verification ---")
    
    agent_token = get_token("alice_agent", "password123")
    contractor_token = get_token("rick_contractor", "password123")
    
    # 1. List Templates
    print("\n[1] Listing Templates...")
    res = requests.get(f"{BASE_URL}/templates")
    templates = res.json()
    print(f"Found {len(templates)} templates.")
    
    target_template = next((t for t in templates if "Residential Remodel" in t["name"]), None)
    if not target_template:
        print("FAIL: 'Residential Remodel' template not found.")
        return
    print(f"Target Template: {target_template['name']} ({target_template['id']})")

    # 2. Create Empty Escrow (Agent)
    print("\n[2] Creating Empty Escrow (Agent)...")
    escrow_data = {
        "buyer_id": "alice_buyer",
        "provider_id": "rick_contractor",
        "total_amount": 50000.0,
        "milestones": [] # Empty
    }
    # Note: Logic in create_escrow handles empty milestones by creating just the escrow
    res = requests.post(f"{BASE_URL}/escrows", json=escrow_data, headers={"Authorization": f"Bearer {agent_token}"})
    if res.status_code != 200:
        print(f"FAIL: Create Escrow failed: {res.text}")
        return
    escrow_id = res.json()["id"]
    print(f"Escrow Created: {escrow_id}")

    # 3. Apply Template
    print("\n[3] Applying Template...")
    img_payload = {"template_id": target_template["id"]}
    res = requests.post(f"{BASE_URL}/escrows/{escrow_id}/apply-template", 
                       json=img_payload, 
                       headers={"Authorization": f"Bearer {agent_token}"})
    
    if res.status_code == 200:
        data = res.json()
        print(f"PASS: Template Applied. Milestones Created: {data.get('milestones_created')}")
    else:
        print(f"FAIL: Apply Template failed: {res.text}")
        return

    # 4. Verify Milestones
    print("\n[4] Verifying Milestones Created...")
    res = requests.get(f"{BASE_URL}/escrows/{escrow_id}", headers={"Authorization": f"Bearer {agent_token}"})
    escrow = res.json()
    milestones = escrow["milestones"]
    print(f"Milestones Count: {len(milestones)}")
    
    if len(milestones) == 5:
        print("PASS: Correct number of milestones (5).")
        # Check amounts
        expected_foundation = 10000.0 # 20% of 50k
        foundation_ms = next((m for m in milestones if "Foundation" in m["name"]), None)
        if foundation_ms and foundation_ms["amount"] == expected_foundation:
            print(f"PASS: Foundation amount correct ({foundation_ms['amount']}).")
        else:
            print(f"FAIL: Foundation amount mismatch. Expected {expected_foundation}, got {foundation_ms['amount'] if foundation_ms else 'None'}")
    else:
        print(f"FAIL: Expected 5 milestones, got {len(milestones)}")

    # 5. Verify Audit Log
    print("\n[5] Verifying Audit Log...")
    res = requests.get(f"{BASE_URL}/audit-logs", headers={"Authorization": f"Bearer {agent_token}"})
    logs = res.json()
    template_event = next((l for l in logs if l["event_type"] == "TEMPLATE_APPLIED" and l["entity_id"] == escrow_id), None)
    
    if template_event:
        print("PASS: TEMPLATE_APPLIED event found in ledger.")
        print(f"Details: {template_event['event_data']}")
    else:
        print("FAIL: TEMPLATE_APPLIED event MISSING.")

    # 6. Negative Test: Apply to Non-Empty
    print("\n[6] Negative Test: Apply to Non-Empty Escrow...")
    # Escrow now has milestones. Verify we can't apply again.
    res = requests.post(f"{BASE_URL}/escrows/{escrow_id}/apply-template", 
                       json=img_payload, 
                       headers={"Authorization": f"Bearer {agent_token}"})
    if res.status_code == 400:
        print("PASS: Blocked applying to non-empty escrow.")
    else:
        print(f"FAIL: Should have blocked (400), got {res.status_code}")

    # 7. Negative Test: Contractor Apply
    print("\n[7] Negative Test: Contractor attempts to apply...")
    # Create new empty escrow first
    escrow_data_2 = {
        "buyer_id": "alice_buyer",
        "provider_id": "rick_contractor",
        "total_amount": 20000.0,
        "milestones": []
    }
    res = requests.post(f"{BASE_URL}/escrows", json=escrow_data_2, headers={"Authorization": f"Bearer {agent_token}"})
    escrow_curr_id = res.json()["id"]
    
    res = requests.post(f"{BASE_URL}/escrows/{escrow_curr_id}/apply-template", 
                       json=img_payload, 
                       headers={"Authorization": f"Bearer {contractor_token}"})
    if res.status_code == 403: # or 401 depending on how we handled role check (dependencies.require_role raises 403 usually)
        print("PASS: Contractor blocked (403).")
    else:
        print(f"FAIL: Contractor NOT blocked. Code: {res.status_code}")

    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    main()
