from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Any
import uuid
import datetime
import json
import os
import shutil
from fastapi import UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from services.notification_service import notification_service

import models, schemas, database, dependencies
from services.notification_service import notification_service

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Escrow Rule Engine API")

@app.get("/health_check_new")
def health_check_new():
    return {"status": "reloaded"}

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount uploads directory
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

import hashlib
import json

# ... (Previous imports)

# ... imports
# ... imports
# ... imports
from pymongo import MongoClient
from database import audit_collection, mongo_client, mongo_db
from services.ledger_service import create_attestation, calculate_hash

# MongoDB Connection (Moved to database.py)
# mongo_client = MongoClient("mongodb://localhost:27017/")
# mongo_db = mongo_client["escrow_ledger"]
# audit_collection = mongo_db["audit_logs"]

# calculate_hash and create_attestation moved to services/ledger_service.py

# ... API Routes ...

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import auth

# ...

# Dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ...

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = datetime.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/audit-logs", response_model=List[schemas.AuditLogRead])

def get_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Read from MongoDB
    logs_cursor = audit_collection.find().sort("timestamp", -1).skip(skip).limit(limit)
    
    results = []
    for l in logs_cursor:
        results.append({
            "entity_id": l["entity_id"],
            "event_type": l["event_type"],
            "actor_id": l["actor_id"],
            "event_data": l["event_data"],
            "timestamp": l["timestamp"],
            "previous_hash": l["previous_hash"],
            "current_hash": l["current_hash"]
        })
    return results

@app.post("/escrows", response_model=schemas.Escrow)
def create_escrow(
    escrow: schemas.EscrowCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.require_role([models.UserRole.AGENT]))
):
    try:
        # 0. Terms Extraction
        terms_data = {
            "buyer": escrow.buyer_id,
            "provider": escrow.provider_id,
            "amount": escrow.total_amount,
            "milestones": [m.dict() for m in escrow.milestones]
        }
        # Initial hash (Mutable until funded)
        agreement_hash = calculate_hash(terms_data)

        # 2. Create Escrow (State = CREATED by default)
        db_escrow = models.Escrow(
            buyer_id=escrow.buyer_id,
            provider_id=escrow.provider_id,
            total_amount=escrow.total_amount,
            state=models.EscrowState.CREATED,
            version=1,
            agreement_hash=agreement_hash,
            funded_amount=0.0
        )
        db.add(db_escrow)
        db.commit()
        db.refresh(db_escrow)

        # 3. Create Milestones
        for ms in escrow.milestones:
            db_milestone = models.Milestone(
                escrow_id=db_escrow.id,
                name=ms.name,
                amount=ms.amount,
                required_evidence_types=ms.required_evidence_types,
                status=models.MilestoneStatus.CREATED # Initial start as CREATED (waiting for first fund)
            )
            db.add(db_milestone)
        
        # 4. Audit Log (Attestation)
        # Attributed to the Authenticated Agent
        create_attestation(db, db_escrow.id, models.AuditEvent.CREATE, current_user.username, current_user.role, terms_data, agreement_hash, 1)
        
        db.commit()
        db.refresh(db_escrow)
        
        # Notify Custodian
        notification_service.emit_notification(
            event_type=models.AuditEvent.CREATE,
            escrow_id=db_escrow.id,
            actor_role=current_user.role,
            data={"users": {"CUSTODIAN": "title_co", "AGENT": "alice_agent"}}
        )
        
        return db_escrow
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/escrows", response_model=List[schemas.Escrow])
def read_escrows(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    escrows = db.query(models.Escrow).offset(skip).limit(limit).all()
    # Simple migration/shim: if funded_amount is None (old records), assume equal to total for FUNDED/ACTIVE
    # But for new logic we rely on default=0.0
    return escrows

@app.get("/escrows/{escrow_id}", response_model=schemas.Escrow)
def read_escrow(escrow_id: str, db: Session = Depends(get_db)):
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == escrow_id).first()
    if db_escrow is None:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return db_escrow

@app.post("/milestones/{milestone_id}/evidence", response_model=schemas.Evidence)
def upload_evidence(
    milestone_id: str, 
    evidence: schemas.EvidenceCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.require_role([models.UserRole.CONTRACTOR]))
):
    db_milestone = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    # Validate Milestone is active (PENDING)
    if db_milestone.status == models.MilestoneStatus.DISPUTED:
        raise HTTPException(status_code=400, detail="Milestone is under dispute. Action blocked.")
    if db_milestone.status == models.MilestoneStatus.CREATED:
        raise HTTPException(status_code=400, detail="Milestone not yet funded (Status: CREATED)")

    # Validate Hash Binding implies checking parent integrity
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == db_milestone.escrow_id).first()
    if not db_escrow.agreement_hash:
         raise HTTPException(status_code=400, detail="Agreement not valid (No Hash)")

    # Check if type is allowed
    required_types = db_milestone.required_evidence_types
    if evidence.evidence_type not in required_types:
        raise HTTPException(status_code=400, detail=f"Evidence type '{evidence.evidence_type}' not required for this milestone")

    db_evidence = models.Evidence(
        milestone_id=milestone_id,
        evidence_type=evidence.evidence_type,
        url=evidence.url
    )
    db.add(db_evidence)
    
    # Update status if pending
    if db_milestone.status == models.MilestoneStatus.PENDING:
        db_milestone.status = models.MilestoneStatus.EVIDENCE_SUBMITTED
        
    db.commit()
    db.refresh(db_evidence)
    
    # Audit Log
    create_attestation(db, db_milestone.escrow_id, models.AuditEvent.UPLOAD_EVIDENCE, current_user.username, current_user.role, {"milestone_id": milestone_id, "type": evidence.evidence_type}, db_escrow.agreement_hash, db_escrow.version)
    
    return db_evidence

@app.post("/escrows/{escrow_id}/confirm_funds", response_model=schemas.Escrow)
def confirm_funds(
    escrow_id: str, 
    confirmation: schemas.FundConfirmation, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.require_role([models.UserRole.CUSTODIAN]))
):
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == escrow_id).first()
    if not db_escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    
    # Logic Split: Initial Funding vs Delta Funding
    is_initial = (db_escrow.state == models.EscrowState.CREATED)
    
    # Currently funded amount (default 0 if None)
    current_funded = db_escrow.funded_amount if db_escrow.funded_amount else 0.0
    needed_total = db_escrow.total_amount
    
    if not is_initial and current_funded >= needed_total:
        raise HTTPException(status_code=400, detail="Escrow already fully funded.")

    # One-Time Gate (For Initial). For Delta, we might allow multiple confirms.
    # The dependencies.validate_one_time_custody checks if state != CREATED.
    # So if it's Delta funding (State=FUNDED), that check would fail. We must bypass it for Delta.
    if is_initial:
        dependencies.validate_one_time_custody(db_escrow)
        db_escrow.state = models.EscrowState.FUNDED
    else:
        # Delta Funding Validation
        if db_escrow.state not in [models.EscrowState.FUNDED, models.EscrowState.ACTIVE]:
             raise HTTPException(status_code=400, detail="Cannot add funds to halted/completed escrow.")

    # Update Funded Amount to match Total
    delta = needed_total - current_funded
    db_escrow.funded_amount = needed_total
    
    # Activation: Move CREATED milestones to PENDING
    # This activates the new work
    new_milestones = db.query(models.Milestone).filter(
        models.Milestone.escrow_id == escrow_id,
        models.Milestone.status == models.MilestoneStatus.CREATED
    ).all()
    for ms in new_milestones:
        ms.status = models.MilestoneStatus.PENDING

    # Lock Hash logic (preserved from V1)
    if not db_escrow.agreement_hash:
        raise HTTPException(status_code=500, detail="Agreement Integrity Error")

    create_attestation(db, escrow_id, models.AuditEvent.CONFIRM_FUNDS, current_user.username, current_user.role, {
        "code": confirmation.confirmation_code,
        "delta_confirmed": delta,
        "new_funded_amount": db_escrow.funded_amount
    }, db_escrow.agreement_hash, db_escrow.version)
    
    db.commit()
    db.refresh(db_escrow)
    
    # Notify Agent
    notification_service.emit_notification(
        event_type=models.AuditEvent.CONFIRM_FUNDS,
        escrow_id=db_escrow.id,
        actor_role=current_user.role,
        data={"users": {"AGENT": "alice_agent"}}
    )
    
    return db_escrow

@app.post("/milestones/{milestone_id}/approve", response_model=schemas.Milestone)
def approve_milestone(
    milestone_id: str, 
    approval: schemas.ApprovalRequest, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.require_role([models.UserRole.INSPECTOR]))
):
    db_milestone = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
        
    # Hard Block: Dispute
    if db_milestone.status == models.MilestoneStatus.DISPUTED:
        raise HTTPException(status_code=400, detail="Milestone is under dispute. Action blocked.")

    # Security Check: Ensure Escrow is Funded/Active
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == db_milestone.escrow_id).first()
    # PENDING -> APPROVED transition requires ACTIVE (Funded) state
    if db_escrow.state not in [models.EscrowState.FUNDED, models.EscrowState.ACTIVE]:
        raise HTTPException(status_code=400, detail="Security Alert: Cannot approve release. Escrow validation failed (Not Funded).")

    # Validate HASH BINDING
    if not db_escrow.agreement_hash:
        raise HTTPException(status_code=500, detail="Critical: Agreement Hash Missing")
    
    # Validate Evidence
    uploaded_evidences = db.query(models.Evidence).filter(models.Evidence.milestone_id == milestone_id).all()
    uploaded_types = [e.evidence_type for e in uploaded_evidences]
    missing = [t for t in db_milestone.required_evidence_types if t not in uploaded_types]
    if missing:
        raise HTTPException(status_code=400, detail=f"Cannot approve. Missing evidence: {missing}")

    # Idempotency Check
    if db_milestone.status in [models.MilestoneStatus.APPROVED, models.MilestoneStatus.PAID]:
         return db_milestone

    # ATOMIC TRANSITION: ACTIVE -> PAID (via Approval)
    # The spec says "Instruction generation triggered only by ACTIVE -> PAID"
    # So we move strictly to PAID and generate instruction.
    db_milestone.status = models.MilestoneStatus.PAID
    db_milestone.approval_signature = {
        "approver": current_user.username,
        "signature": approval.signature,
        "timestamp": str(datetime.datetime.utcnow())
    }
    
    # Audit Log (Attestation)
    create_attestation(db, db_milestone.escrow_id, models.AuditEvent.APPROVE, current_user.username, current_user.role, {"milestone_id": milestone_id}, db_escrow.agreement_hash, db_escrow.version)

    # INTERNAL SYSTEM ACTION: Generate Banking Instruction
    instruction = generate_instruction_internal(db_escrow, db_milestone, db, current_user)
    
    db.commit()
    db.refresh(db_milestone)
    
    # Notify Participants (Agent & Contractor)
    notification_service.emit_notification(
       event_type=models.AuditEvent.PAYMENT_RELEASED,
       escrow_id=db_escrow.id,
       milestone_id=milestone_id,
       actor_role=current_user.role,
       data={"users": {
           "AGENT": "alice_agent", 
           "CONTRACTOR": "rick_contractor"
       }}
    )
    
    return db_milestone

def generate_instruction_internal(db_escrow, db_milestone, db, approver_user):
    # System-Only Logic
    instruction = schemas.BankingInstruction(
        instruction_id=str(uuid.uuid4()),
        agreement_id=db_escrow.id,
        agreement_version=f"v{db_escrow.version}",
        agreement_hash=db_escrow.agreement_hash,
        payee=db_escrow.provider_id,
        amount=db_milestone.amount,
        currency="USD",
        approvals=[db_milestone.approval_signature],
        attestation=f"All conditions defined in Agreement v{db_escrow.version} have been satisfied."
    )
    # Log Payment Release
    create_attestation(db, db_escrow.id, models.AuditEvent.PAYMENT_RELEASED, "SYSTEM_INSTRUCTION", "SYSTEM", {
        "instruction_id": instruction.instruction_id,
        "payee": instruction.payee,
        "amount": instruction.amount
    }, db_escrow.agreement_hash, db_escrow.version)
    return instruction

@app.post("/escrows/{escrow_id}/change-budget", response_model=schemas.Escrow)
def change_budget(
    escrow_id: str,
    change_req: schemas.ChangeBudgetRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.require_role([models.UserRole.AGENT, models.UserRole.ADMIN]))
):
    try:
        """
        Append-Only Budget Increase (Change Order v1).
        Adds new milestone, increases Total, keeps Funded same (creating a Delta).
        Does NOT reset state.
        """
        db_escrow = db.query(models.Escrow).filter(models.Escrow.id == escrow_id).first()
        if not db_escrow:
            raise HTTPException(status_code=404, detail="Escrow not found")
            
        if db_escrow.state == models.EscrowState.COMPLETED: # or PAID
             raise HTTPException(status_code=400, detail="Cannot change budget of fully PAID escrow.")

        if change_req.amount_delta <= 0:
            raise HTTPException(status_code=400, detail="Amount delta must be positive.")

        # 1. Append New Milestone (Status = CREATED)
        # This effectively "parks" the work until funded.
        new_milestone = models.Milestone(
            escrow_id=db_escrow.id,
            name=change_req.milestone_name,
            amount=change_req.amount_delta,
            required_evidence_types=[change_req.evidence_type],
            status=models.MilestoneStatus.CREATED 
        )
        db.add(new_milestone)
        db.flush() # get ID

        # 2. Update Total Amount (Funded Amount stays same -> Logic Gap created)
        db_escrow.total_amount += change_req.amount_delta
        
        # 3. Audit Log
        # We link to the specific new milestone ID
        create_attestation(db, escrow_id, models.AuditEvent.CHANGE_ORDER_ADDED, current_user.username, current_user.role, 
            {
                "delta_amount": change_req.amount_delta,
                "milestone_id": new_milestone.id,
                "milestone_name": new_milestone.name,
                "prev_hash": db_escrow.agreement_hash # Linking to current state
            }, db_escrow.agreement_hash, db_escrow.version)
        
        db.commit()
        db.refresh(db_escrow)
        
        # Notify funds required (Agent) - wait, this adds milestone but usually requires funding confirmation?
        # The prompt says: "FUNDS_REQUIRED -> Client / Agent". This corresponds to CHANGE_ORDER_BUDGET.
        notification_service.emit_notification(
            event_type=models.AuditEvent.CHANGE_ORDER_BUDGET,
            escrow_id=escrow_id,
            actor_role=current_user.role,
            data={"users": {"AGENT": "alice_agent"}, "delta_amount": change_req.amount_delta}
        )
        
        return db_escrow
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit-logs", response_model=List[schemas.AuditLogRead])
def get_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Return logs ordered by timestamp (descending) to show latest activity first
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    # Map to schema manually or rely on ORM if schemas match. 
    # Our schema AuditLogCreate might need a read-version with 'timestamp' and 'hash'.
    # Let's define a Read schema inline or use a dict for simplicity in this MVP.
    return [
        {
            "entity_id": l.entity_id,
            "event_type": l.event_type,
            "actor_id": l.actor_id,
            "event_data": l.event_data,
            "timestamp": l.timestamp,
            "previous_hash": l.previous_hash,
            "current_hash": l.current_hash
        }
        for l in logs
    ]

@app.post("/escrows/{escrow_id}/dispute", response_model=schemas.Escrow)
def dispute_escrow(escrow_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(dependencies.get_current_user)):
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == escrow_id).first()
    if not db_escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
        
    db_escrow.state = models.EscrowState.DISPUTED
    db_escrow.is_disputed = True
    
    # Audit Log
    create_attestation(db, escrow_id, models.AuditEvent.DISPUTE, current_user.username, current_user.role, 
        {"reason": "Manual Dispute Triggered"}, db_escrow.agreement_hash, db_escrow.version)
    
    db.commit()
    db.refresh(db_escrow)
    
    # Notify Dispute
    notification_service.emit_notification(
        event_type=models.AuditEvent.DISPUTE,
        escrow_id=escrow_id,
        actor_role=current_user.role,
        data={"users": {"AGENT": "alice_agent", "INSPECTOR": "rob_inspector", "CUSTODIAN": "title_co"}}
    )
    
    return db_escrow

@app.post("/milestones/{milestone_id}/dispute", response_model=schemas.Milestone)
def raise_milestone_dispute(
    milestone_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.require_role([models.UserRole.AGENT, models.UserRole.INSPECTOR, models.UserRole.CUSTODIAN]))
):
    db_milestone = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
    # Validation: Explicitly Forbidden for Contractor (Handled by RPAC, but double check logic if needed)
    if current_user.role == models.UserRole.CONTRACTOR:
        raise HTTPException(status_code=403, detail="Contractors cannot raise disputes.")

    # Validation: Status must be PENDING or EVIDENCE_SUBMITTED
    if db_milestone.status not in [models.MilestoneStatus.PENDING, models.MilestoneStatus.EVIDENCE_SUBMITTED]:
        raise HTTPException(status_code=400, detail=f"Cannot dispute milestone in state {db_milestone.status}")

    # Action: Set DISPUTED
    db_milestone.status = models.MilestoneStatus.DISPUTED
    
    # Ledger Event
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == db_milestone.escrow_id).first()
    create_attestation(db, db_escrow.id, "DISPUTE_RAISED", current_user.username, current_user.role, {
        "milestone_id": milestone_id,
        "milestone_name": db_milestone.name
    }, db_escrow.agreement_hash, db_escrow.version)
    
    db.commit()
    db.refresh(db_milestone)
    
    # Notify Dispute Raised
    notification_service.emit_notification(
        event_type=models.AuditEvent.DISPUTE,
        escrow_id=db_escrow.id,
        milestone_id=milestone_id,
        actor_role=current_user.role,
        data={"users": {"AGENT": "alice_agent", "INSPECTOR": "rob_inspector", "CUSTODIAN": "title_co"}}
    )
    
    return db_milestone

@app.post("/milestones/{milestone_id}/resolve-dispute", response_model=schemas.Milestone)
def resolve_milestone_dispute(
    milestone_id: str,
    resolution: schemas.DisputeResolutionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.require_role([models.UserRole.AGENT, models.UserRole.INSPECTOR, models.UserRole.CUSTODIAN]))
):
    db_milestone = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
        
    if db_milestone.status != models.MilestoneStatus.DISPUTED:
        raise HTTPException(status_code=400, detail="Milestone is not currently disputed.")

    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == db_milestone.escrow_id).first()

    if resolution.resolution == "RESUME":
        # Resume Logic: Return to Pre-Dispute State
        # Heuristic: If evidence exists -> EVIDENCE_SUBMITTED, else PENDING
        has_evidence = db.query(models.Evidence).filter(models.Evidence.milestone_id == milestone_id).first()
        new_status = models.MilestoneStatus.EVIDENCE_SUBMITTED if has_evidence else models.MilestoneStatus.PENDING
        db_milestone.status = new_status
        
        create_attestation(db, db_escrow.id, "DISPUTE_RESOLVED", current_user.username, current_user.role, {
            "milestone_id": milestone_id,
            "resolution": "RESUME",
            "new_status": new_status
        }, db_escrow.agreement_hash, db_escrow.version)

    elif resolution.resolution == "CANCEL":
        # Cancel Logic
        db_milestone.status = models.MilestoneStatus.CANCELLED
        
        create_attestation(db, db_escrow.id, "DISPUTE_RESOLVED", current_user.username, current_user.role, {
            "milestone_id": milestone_id,
            "resolution": "CANCEL"
        }, db_escrow.agreement_hash, db_escrow.version)
        
        # Notify Cancelled
        notification_service.emit_notification(
            event_type=models.AuditEvent.MILESTONE_CANCELLED,
            escrow_id=db_escrow.id,
            milestone_id=milestone_id,
            actor_role=current_user.role,
            data={"users": {"AGENT": "alice_agent", "CUSTODIAN": "title_co"}, "milestone_name": db_milestone.name}
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid resolution type")
        
    db.commit()
    db.refresh(db_milestone)
    return db_milestone

@app.post("/reset")
def reset_system(db: Session = Depends(get_db)):
    """Wipes all data for a clean slate."""
    # 1. Clear Mongo (Ledger & Notifications)
    audit_collection.delete_many({})
    notification_service.notification_collection.delete_many({})
    
    # 2. Clear Postgres (State)
    # Delete in order of dependencies (Child -> Parent)
    db.query(models.Evidence).delete()
    db.query(models.Milestone).delete()
    db.query(models.Escrow).delete()
    
    db.commit()

    # 3. Clear Local Files
    # Delete all files in 'uploads/' but keep the directory
    folder = 'uploads'
    if os.path.exists(folder):
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")

    return {"message": "System Reset Complete"}

@app.post("/milestones/{id}/external-evidence", response_model=schemas.Evidence)
def attach_external_evidence(
    id: str,
    source_type: schemas.EvidenceSourceType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # 1. RBAC: Only Inspector, Agent, Custodian
    if current_user.role == models.UserRole.CONTRACTOR:
        raise HTTPException(status_code=403, detail="Contractors cannot submit third-party external evidence.")
    
    # 2. Get Milestone
    milestone = db.query(models.Milestone).filter(models.Milestone.id == id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
        
    db_escrow = milestone.escrow
    
    # 3. Validation: Status Checks
    if milestone.status in [models.MilestoneStatus.DISPUTED, models.MilestoneStatus.PAID, models.MilestoneStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Cannot attach evidence to this milestone state.")
        
    # 4. Handle File Upload
    # Verify extension (basic check)
    filename = file.filename.lower()
    if not (filename.endswith('.pdf') or filename.endswith('.jpg') or filename.endswith('.png') or filename.endswith('.jpeg')):
        raise HTTPException(status_code=400, detail="Only PDF, JPG, and PNG files are allowed.")
        
    # Generate safe filename
    safe_filename = f"{id}_{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join("uploads", safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
        
    # Generate URL (Localhost for MVP)
    file_url = f"http://localhost:8000/uploads/{safe_filename}"
    
    # 5. Create Evidence Record (ADDITIVE ONLY)
    new_evidence = models.Evidence(
        milestone_id=id,
        evidence_type="External Attestation", # Label
        url=file_url,
        origin=models.EvidenceOrigin.THIRD_PARTY,
        source_type=source_type,
        submitted_by_role=current_user.role
    )
    db.add(new_evidence)
    
    # 6. Log to Ledger (EVIDENCE_ATTESTED)
    create_attestation(
        db, 
        entity_id=db_escrow.id,
        event_type=models.AuditEvent.EVIDENCE_ATTESTED,
        actor_username=current_user.username,
        actor_role=current_user.role,
        data={
            "milestone_id": id,
            "origin": "THIRD_PARTY",
            "source_type": source_type,
            "url": file_url
        },
        agreement_hash=db_escrow.agreement_hash,
        agreement_version=db_escrow.version
    )
    
    db.commit()
    db.refresh(new_evidence)
    
    # Notify External Evidence
    notification_service.emit_notification(
        event_type=models.AuditEvent.EVIDENCE_ATTESTED,
        escrow_id=db_escrow.id,
        milestone_id=id,
        actor_role=current_user.role,
        data={"users": {"AGENT": "alice_agent"}}
    )
    
    return new_evidence

@app.post("/milestones/{id}/evidence/upload", response_model=schemas.Evidence)
def upload_contractor_evidence(
    id: str,
    evidence_type: str = Form(...),
    source_type: schemas.EvidenceSourceType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.require_role([models.UserRole.CONTRACTOR]))
):
    """
    Contractor File Upload Endpoint.
    Replaces the mock JSON upload. Handles file storage + state transition.
    """
    # 1. Get Milestone
    milestone = db.query(models.Milestone).filter(models.Milestone.id == id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
        
    db_escrow = milestone.escrow
    
    # 2. Validation: Status Checks
    if milestone.status not in [models.MilestoneStatus.PENDING, models.MilestoneStatus.EVIDENCE_SUBMITTED]:
         raise HTTPException(status_code=400, detail=f"Cannot upload evidence in state {milestone.status}")
         
    # 3. Validate Evidence Type
    if evidence_type not in milestone.required_evidence_types:
        raise HTTPException(status_code=400, detail=f"Evidence type '{evidence_type}' not required for this milestone")

    # 4. Handle File Upload
    # Verify extension (basic check)
    filename = file.filename.lower()
    if not (filename.endswith('.pdf') or filename.endswith('.jpg') or filename.endswith('.png') or filename.endswith('.jpeg')):
        raise HTTPException(status_code=400, detail="Only PDF, JPG, and PNG files are allowed.")
        
    # Generate safe filename
    safe_filename = f"{id}_{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join("uploads", safe_filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
        
    # Generate URL
    file_url = f"http://localhost:8000/uploads/{safe_filename}"
    
    # 5. Create Evidence Record
    new_evidence = models.Evidence(
        milestone_id=id,
        evidence_type=evidence_type,
        url=file_url,
        origin=models.EvidenceOrigin.CONTRACTOR,
        source_type=source_type,
        submitted_by_role=current_user.role
    )
    db.add(new_evidence)
    
    # 6. Update Milestone Status
    # CHANGED: We do NOT auto-submit anymore. Contractor must explicitly click "Finish Submission".
    # if milestone.status == models.MilestoneStatus.PENDING:
    #     milestone.status = models.MilestoneStatus.EVIDENCE_SUBMITTED
    
    # 7. Audit Log
    create_attestation(
        db, 
        entity_id=db_escrow.id,
        event_type=models.AuditEvent.UPLOAD_EVIDENCE,
        actor_username=current_user.username,
        actor_role=current_user.role,
        data={
            "milestone_id": id,
            "type": evidence_type,
            "url": file_url, 
            "filename": safe_filename
        },
        agreement_hash=db_escrow.agreement_hash,
        agreement_version=db_escrow.version
    )
    
    db.commit()
    db.refresh(new_evidence)
    return new_evidence

@app.post("/milestones/{id}/submit", response_model=schemas.Milestone)
def submit_milestone_evidence(
    id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(dependencies.require_role([models.UserRole.CONTRACTOR]))
):
    """
    Explicitly marks a milestone as EVIDENCE_SUBMITTED.
    Indicates Contractor is done uploading.
    """
    milestone = db.query(models.Milestone).filter(models.Milestone.id == id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
        
    if milestone.status != models.MilestoneStatus.PENDING:
        # If already submitted, just return (idempotent-ish) or error?
        # Let's return idempotently if already submitted, else error
        if milestone.status == models.MilestoneStatus.EVIDENCE_SUBMITTED:
             return milestone
        raise HTTPException(status_code=400, detail=f"Cannot submit evidence for milestone in state {milestone.status}")

    # Check if ANY evidence exists? (Optional but good validation)
    if not milestone.evidence:
         raise HTTPException(status_code=400, detail="Cannot submit without uploading evidence first.")

    milestone.status = models.MilestoneStatus.EVIDENCE_SUBMITTED
    
    # Optional: We could log an event here too "EVIDENCE_SUBMISSION_COMPLETED"
    # For now, relying on status change state.
    
    db.commit()
    db.refresh(milestone)
    
    # Notify Inspector
    notification_service.emit_notification(
        event_type=models.AuditEvent.UPLOAD_EVIDENCE,
        escrow_id=milestone.escrow_id,
        milestone_id=id,
        actor_role=current_user.role,
        data={"users": {"INSPECTOR": "rob_inspector"}}
    )
    
    return milestone

@app.get("/notifications", response_model=List[Any])
def get_notifications(
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Fetch notifications for key user."""
    # Convert Mongo objects to list and handle ObjectId serialization
    notes = notification_service.get_notifications(current_user.username, current_user.role)
    results = []
    for n in notes:
        n["_id"] = str(n["_id"])
        results.append(n)
    return results

@app.post("/notifications/{id}/read")
def mark_notification_read(
    id: str,
    current_user: models.User = Depends(dependencies.get_current_user)
):
    """Mark notification as read."""
    notification_service.mark_read(id, current_user.username)
    return {"status": "success"}
