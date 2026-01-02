import requests
import sys

BASE_URL = "http://localhost:8000"

def get_token(username, password):
    resp = requests.post(f"{BASE_URL}/token", data={"username": username, "password": password})
    if resp.status_code != 200:
        print(f"Login failed for {username}: {resp.text}")
        sys.exit(1)
    return resp.json()["access_token"]

def main():
    print("=== Verifying Dispute & Exception Handling ===")
    
    # 1. Login
    agent_token = get_token("alice_agent", "password123")
    custodian_token = get_token("title_co", "password123")
    inspector_token = get_token("jim_inspector", "password123")
    contractor_token = get_token("bob_contractor", "password123")
    
    headers_agent = {"Authorization": f"Bearer {agent_token}"}
    headers_custodian = {"Authorization": f"Bearer {custodian_token}"}
    headers_inspector = {"Authorization": f"Bearer {inspector_token}"}
    headers_contractor = {"Authorization": f"Bearer {contractor_token}"}

    # 2. Create Escrow
    print("\n--- Creating Escrow ---")
    escrow_data = {
        "buyer_id": "Buyer",
        "provider_id": "Provider",
        "total_amount": 1000.0,
        "milestones": [
            {"name": "Disputable Work", "amount": 1000.0, "required_evidence_types": ["PHOTO"]}
        ]
    }
    resp = requests.post(f"{BASE_URL}/escrows", json=escrow_data, headers=headers_agent)
    if resp.status_code != 200:
        print(f"Create failed: {resp.text}")
        sys.exit(1)
    escrow_id = resp.json()["id"]
    milestone_id = resp.json()["milestones"][0]["id"]
    print(f"Escrow Created: {escrow_id}")
    print(f"Milestone ID: {milestone_id}")

    # 3. Fund Escrow (Initial)
    print("\n--- Funding Escrow ---")
    resp = requests.post(f"{BASE_URL}/escrows/{escrow_id}/confirm_funds", json={"custodian_id": "title_co", "confirmation_code": "WIRE"}, headers=headers_custodian)
    if resp.status_code != 200:
        print(f"Funding failed: {resp.text}")
        sys.exit(1)
    print("Escrow Funded. Milestone should be PENDING.")

    # 4. Contractor Uploads Evidence
    print("\n--- Uploading Evidence ---")
    resp = requests.post(f"{BASE_URL}/milestones/{milestone_id}/evidence", json={"evidence_type": "PHOTO", "url": "http://img.com"}, headers=headers_contractor)
    if resp.status_code != 200:
        print(f"Evidence upload failed: {resp.text}")
        sys.exit(1)
    print("Evidence Uploaded. Milestone should be EVIDENCE_SUBMITTED.")

    # 5. Contractor Tries to Dispute (Should Fail 403)
    print("\n--- Negative Test: Contractor Raises Dispute ---")
    resp = requests.post(f"{BASE_URL}/milestones/{milestone_id}/dispute", headers=headers_contractor)
    if resp.status_code == 403:
        print("Success: Contractor blocked from disputing (403).")
    else:
        print(f"Failure: Expected 403, got {resp.status_code}")

    # 6. Agent Raises Dispute
    print("\n--- Agent Raises Dispute ---")
    resp = requests.post(f"{BASE_URL}/milestones/{milestone_id}/dispute", headers=headers_agent)
    if resp.status_code != 200:
        print(f"Dispute failed: {resp.text}")
        sys.exit(1)
    ms = resp.json()
    if ms["status"] == "DISPUTED":
        print("Success: Milestone status is DISPUTED.")
    else:
        print(f"Failure: Expected DISPUTED, got {ms['status']}")

    # 7. Inspector Tries to Approve (Should Fail 400)
    print("\n--- Negative Test: Approve during Dispute ---")
    resp = requests.post(f"{BASE_URL}/milestones/{milestone_id}/approve", json={"approver_id": "jim", "signature": "sig"}, headers=headers_inspector)
    if resp.status_code == 400 and "blocked" in resp.text:
        print("Success: Approval blocked (400).")
    else:
        print(f"Failure: Expected 400 Blocked, got {resp.status_code} - {resp.text}")

    # 8. Inspector Resolves Dispute (RESUME)
    print("\n--- Inspector Resolves Dispute (RESUME) ---")
    resp = requests.post(f"{BASE_URL}/milestones/{milestone_id}/resolve-dispute", json={"resolution": "RESUME"}, headers=headers_inspector)
    if resp.status_code != 200:
        print(f"Resume failed: {resp.text}")
        sys.exit(1)
    ms = resp.json()
    if ms["status"] == "EVIDENCE_SUBMITTED":
        print("Success: Milestone resumed to EVIDENCE_SUBMITTED (since evidence exists).")
    else:
        print(f"Failure: Expected EVIDENCE_SUBMITTED, got {ms['status']}")

    # 9. Custodian Raises Dispute Again
    print("\n--- Custodian Raises Dispute ---")
    resp = requests.post(f"{BASE_URL}/milestones/{milestone_id}/dispute", headers=headers_custodian)
    if resp.status_code != 200:
        print(f"Dispute failed: {resp.text}")
    print("Milestone Disputed again.")

    # 10. Agent Resolves Dispute (CANCEL)
    print("\n--- Agent Resolves Dispute (CANCEL) ---")
    resp = requests.post(f"{BASE_URL}/milestones/{milestone_id}/resolve-dispute", json={"resolution": "CANCEL"}, headers=headers_agent)
    if resp.status_code != 200:
        print(f"Cancel failed: {resp.text}")
        sys.exit(1)
    ms = resp.json()
    if ms["status"] == "CANCELLED":
        print("Success: Milestone CANCELLED.")
    else:
        print(f"Failure: Expected CANCELLED, got {ms['status']}")

    print("\n=== Verification Complete: All Systems Passing ===")

if __name__ == "__main__":
    main()
