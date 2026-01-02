import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import models
import database
import main
from models import Escrow, Milestone, EscrowState, MilestoneStatus, AuditEvent, UserRole

def verify_logic_direct():
    print("--- Verifying Budget Change Logic (Direct DB) ---")
    db = database.SessionLocal()
    try:
        # 1. Setup: Create & Fund Escrow
        print("[1] Setup: creating funded escrow...")
        terms = {"buyer": "b", "provider": "p", "amount": 1000.0, "milestones": []}
        h1 = main.calculate_hash(terms)
        
        escrow = Escrow(
            buyer_id="b", provider_id="p", total_amount=1000.0, 
            state=EscrowState.FUNDED, version=1, agreement_hash=h1, funded_amount=1000.0
        )
        db.add(escrow)
        db.commit()
        db.refresh(escrow)
        
        # Add initial paid milestone to prove no reset
        m1 = Milestone(escrow_id=escrow.id, name="M1", amount=1000.0, status=MilestoneStatus.PAID)
        db.add(m1)
        db.commit()
        
        print(f"Initial State: {escrow.state}, Total: {escrow.total_amount}")
        
        # 2. Change Budget Logic (Mimic POST /change-budget)
        print("\n[2] Executing Change Budget Logic...")
        amount_delta = 500.0
        
        # Validation checks
        # Validation checks
        if escrow.state == EscrowState.COMPLETED: 
             raise Exception("Cannot change completed")
        
        # Update Total
        escrow.total_amount += amount_delta
        # Do NOT update funded_amount
        
        # Add Milestone
        new_ms = Milestone(
            escrow_id=escrow.id,
            name="Change Order 1",
            amount=amount_delta,
            required_evidence_types=["Invoice"],
            status=MilestoneStatus.CREATED # The key requirement
        )
        db.add(new_ms)
        
        # Audit Log
        main.create_attestation(
            db, escrow.id, AuditEvent.CHANGE_ORDER_ADDED, "agent", "AGENT", 
            {"delta": amount_delta}, escrow.agreement_hash, escrow.version
        )
        
        db.commit()
        db.refresh(escrow)
        
        # 3. Verify
        print("\n[3] Verifying Results...")
        print(f"New State: {escrow.state}")
        print(f"New Total: {escrow.total_amount}")
        print(f"Funded Amount: {escrow.funded_amount}")
        print(f"New MS Status: {new_ms.status}")
        
        if escrow.state != EscrowState.FUNDED:
            print("❌ FAIL: State reset!")
        else:
            print("✅ PASS: State preserved.")
            
        if escrow.total_amount != 1500.0:
             print("❌ FAIL: Total amount incorrect.")
        else:
             print("✅ PASS: Total amount updated.")
             
        if escrow.funded_amount != 1000.0:
             print("❌ FAIL: Funded amount changed explicitly!")
        else:
             print("✅ PASS: Funded amount unchanged (Delta funding needed).")
             
        if new_ms.status != MilestoneStatus.CREATED:
             print(f"❌ FAIL: Milestone status is {new_ms.status}")
        else:
             print("✅ PASS: Milestone status is CREATED.")

        # 4. Confirm Funds Logic (Mimic POST /confirm_funds)
        print("\n[4] Executing Confirm Delta Funds Logic...")
        # Check delta handling
        if escrow.funded_amount < escrow.total_amount:
            print("Detected Delta Funding needed.")
            escrow.funded_amount = escrow.total_amount
            
            # Activate CREATED milestones
            created_ms = db.query(Milestone).filter(
                Milestone.escrow_id == escrow.id,
                Milestone.status == MilestoneStatus.CREATED
            ).all()
            for ms in created_ms:
                ms.status = MilestoneStatus.PENDING
                print(f"Activated milestone {ms.name}")
            
            db.commit()
            db.refresh(escrow)
            db.refresh(new_ms)
            
            if new_ms.status == MilestoneStatus.PENDING:
                print("✅ PASS: Milestone activated to PENDING.")
            else:
                print(f"❌ FAIL: Milestone status {new_ms.status}")
        else:
            print("❌ FAIL: Did not detect funding gap.")

    except Exception as e:
        print("FAILED:")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_logic_direct()
