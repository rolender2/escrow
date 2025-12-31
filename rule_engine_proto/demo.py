from engine import EscrowAgreement, MilestoneStatus, EscrowState
import json

def run_scenario():
    print("=== SCENARIO: Real Estate Post-Inspection Repair Escrow ===\n")

    # 1. Setup
    print("1. AGENT sets up the escrow for 'Roof Repair'...")
    # Buyer: Alice, Contractor: Bob's Roofing
    escrow = EscrowAgreement(buyer_id="Alice_Buyer", provider_id="Bob_Contractor", total_amount=10000.0)
    
    # Add a single milestone for the roof
    escrow.add_milestone(name="Complete Roof Repair", amount=10000.0, evidence_types=["Photo_Proof", "Invoice"])
    print(f"   CREATED Escrow ID: {escrow.id}")
    print(f"   Milestone: 'Complete Roof Repair' ($10,000) requiring [Photo_Proof, Invoice]")

    # 2. Funding
    print("\n2. TITLE COMPANY wires funds to lock...")
    escrow.deposit_funds(10000.0)
    escrow.start_project()
    print(f"   Escrow State: {escrow.state.value}")
    print("   (Contractor starts working...)")

    # 3. Evidence Upload
    print("\n3. CONTRACTOR finishes work and uploads evidence...")
    # Simulate uploads
    milestone = escrow.milestones[0]
    milestone.add_evidence("Photo_Proof", "http://cloud.storage/roof_fixed.jpg")
    print("   - Uploaded Photo")
    milestone.add_evidence("Invoice", "http://cloud.storage/invoice_123.pdf")
    print("   - Uploaded Invoice")
    print(f"   Milestone Status: {milestone.status.value}")

    # 4. Approval
    print("\n4. INSPECTOR (or Buyer Agent) reviews and approves...")
    # In reality, this would be a secure digital signature
    milestone.approve(approver_id="Inspector_Gadget", signature="valid_crypto_signature_123")
    print(f"   Milestone Status: {milestone.status.value}")

    # 5. Settlement Generation
    print("\n5. SYSTEM automatically generates Banking Instruction...")
    try:
        instruction = escrow.generate_release_instruction(0)
        print("   SUCCESS! Instruction Generated:")
        print(json.dumps(instruction, indent=2))
        
        print(f"\n   Final Escrow State: {escrow.state.value}")
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == "__main__":
    run_scenario()
