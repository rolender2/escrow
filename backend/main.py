from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Any
import uuid
import datetime
import json

import models, schemas, database, dependencies

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Escrow Rule Engine API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
from pymongo import MongoClient

# MongoDB Connection
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["escrow_ledger"]
audit_collection = mongo_db["audit_logs"]

def calculate_hash(data: Any) -> str:
    """Returns SHA-256 hash of JSON-encoded data."""
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()

def create_attestation(db, entity_id, event_type, actor_username, actor_role, data, agreement_hash=None, agreement_version=None):
    """Creates a cryptographically chained attestation (audit log) in MongoDB."""
    # 1. Get previous log hash from Mongo
    last_entry = audit_collection.find_one(sort=[("timestamp", -1)])
    prev_hash = last_entry["current_hash"] if last_entry else "0" * 64
    
    # 2. Calculate Current Hash
    # We include all strict fields in the hash payload
    current_payload = {
        "prev": prev_hash,
        "entity": entity_id,
        "event": event_type,
        "actor": actor_username,
        "role": str(actor_role) if actor_role else "SYSTEM",
        "data": data,
        "agreement_hash": agreement_hash,
        "version": agreement_version
    }
    current_hash = calculate_hash(current_payload)
    
    # 3. Save to Mongo (Ledger First)
    log_entry = {
        "entity_id": entity_id,
        "event_type": event_type.value if hasattr(event_type, "value") else str(event_type),
        "actor_id": actor_username, # Keeping generic field name for API compatibility
        "actor_role": str(actor_role) if actor_role else "SYSTEM",
        "previous_hash": prev_hash,
        "current_hash": current_hash,
        "event_data": data,
        "agreement_hash": agreement_hash,
        "agreement_version": agreement_version,
        "timestamp": datetime.datetime.utcnow()
    }
    audit_collection.insert_one(log_entry)
    return log_entry

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
    # 1. Calculate Agreement Hash (Terms)
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
        agreement_hash=agreement_hash
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
            status=models.MilestoneStatus.PENDING
        )
        db.add(db_milestone)
    
    # 4. Audit Log (Genesis)
    # Attributed to the Authenticated Agent
    # 4. Audit Log (Attestation)
    # Attributed to the Authenticated Agent
    create_attestation(db, db_escrow.id, models.AuditEvent.CREATE, current_user.username, current_user.role, terms_data, agreement_hash, 1)
    
    db.commit()
    db.refresh(db_escrow)
    return db_escrow

@app.get("/escrows", response_model=List[schemas.Escrow])
def read_escrows(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    escrows = db.query(models.Escrow).offset(skip).limit(limit).all()
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
    
    # One-Time Gate & State Validation
    dependencies.validate_one_time_custody(db_escrow)

    # Lock Agreement Hash (terms become immutable)
    # Re-calculate or assume 'agreement_hash' from creation is valid if version is 1.
    # For safety, we verify it matches (or just lock it if it was null, but we set it on create).
    if not db_escrow.agreement_hash:
        # Should have been set on create, but if not, logic error.
        raise HTTPException(status_code=500, detail="Agreement Integrity Error: Missing Hash")

    db_escrow.state = models.EscrowState.FUNDED
    
    # Audit Log (Attestation)
    # Audit Log (Attestation)
    create_attestation(db, escrow_id, models.AuditEvent.CONFIRM_FUNDS, current_user.username, current_user.role, {
        "code": confirmation.confirmation_code,
        "agreement_hash": db_escrow.agreement_hash
    }, db_escrow.agreement_hash, db_escrow.version)
    
    db.commit()
    db.refresh(db_escrow)
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
    # Audit Log (Attestation)
    create_attestation(db, db_milestone.escrow_id, models.AuditEvent.APPROVE, current_user.username, current_user.role, {"milestone_id": milestone_id}, db_escrow.agreement_hash, db_escrow.version)

    # INTERNAL SYSTEM ACTION: Generate Banking Instruction
    instruction = generate_instruction_internal(db_escrow, db_milestone, db, current_user)
    
    db.commit()
    db.refresh(db_milestone)
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
    # Log Payment Release
    create_attestation(db, db_escrow.id, models.AuditEvent.PAYMENT_RELEASED, "SYSTEM_INSTRUCTION", "SYSTEM", {
        "instruction_id": instruction.instruction_id,
        "payee": instruction.payee,
        "amount": instruction.amount
    }, db_escrow.agreement_hash, db_escrow.version)
    return instruction

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
# Removed public generate_instruction endpoint. Logic is now internal.

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
    return db_escrow

@app.post("/reset")
def reset_system(db: Session = Depends(get_db)):
    """Wipes all data for a clean slate."""
    # 1. Clear Mongo (Ledger)
    audit_collection.delete_many({})
    
    # 2. Clear Postgres (State)
    # Delete in order of dependencies (Child -> Parent)
    db.query(models.Evidence).delete()
    db.query(models.Milestone).delete()
    db.query(models.Escrow).delete()
    
    db.commit()
    return {"message": "System Reset Complete"}
