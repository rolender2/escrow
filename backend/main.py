from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Any
import uuid
import datetime
import json

import models, schemas, database

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

def create_audit_log(db: Session, entity_id: str, event_type: str, actor_id: str, data: dict):
    """Creates a cryptographically chained audit log entry in MongoDB."""
    # 1. Get previous log hash from Mongo
    last_log = audit_collection.find_one(
        {"entity_id": entity_id},
        sort=[("timestamp", -1)]
    )
    prev_hash = last_log["current_hash"] if last_log else "0" * 64
    
    # 2. Compute current hash
    current_payload = {
        "prev": prev_hash,
        "entity": entity_id,
        "event": event_type,
        "actor": actor_id,
        "data": data
    }
    current_hash = calculate_hash(current_payload)
    
    # 3. Save to Mongo
    log_entry = {
        "entity_id": entity_id,
        "event_type": str(event_type),
        "actor_id": actor_id,
        "previous_hash": prev_hash,
        "current_hash": current_hash,
        "event_data": data,
        "timestamp": datetime.datetime.utcnow()
    }
    audit_collection.insert_one(log_entry)
    return log_entry

# ... API Routes ...

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
def create_escrow(escrow: schemas.EscrowCreate, db: Session = Depends(get_db)):
    # 1. Calculate Agreement Hash (Terms)
    terms_data = {
        "buyer": escrow.buyer_id,
        "provider": escrow.provider_id,
        "amount": escrow.total_amount,
        "milestones": [m.dict() for m in escrow.milestones]
    }
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
    create_audit_log(db, db_escrow.id, models.AuditEvent.CREATE, "AGENT_API", terms_data)
    
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
def upload_evidence(milestone_id: str, evidence: schemas.EvidenceCreate, db: Session = Depends(get_db)):
    db_milestone = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    
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
    create_audit_log(db, db_milestone.escrow_id, models.AuditEvent.UPLOAD_EVIDENCE, "CONTRACTOR_API", {"milestone_id": milestone_id, "type": evidence.evidence_type})
    
    return db_evidence

@app.post("/escrows/{escrow_id}/confirm_funds", response_model=schemas.Escrow)
def confirm_funds(escrow_id: str, confirmation: schemas.FundConfirmation, db: Session = Depends(get_db)):
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == escrow_id).first()
    if not db_escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
        
    if db_escrow.state != models.EscrowState.CREATED:
        raise HTTPException(status_code=400, detail=f"Cannot fund escrow in state {db_escrow.state}")

    # Role Check: In real app, verify user is CUSTODIAN
    # For prototype, we just log the actor
    
    db_escrow.state = models.EscrowState.FUNDED
    # Also activate milestones? or wait for start? Let's say FUNDED implies ACTIVE for this simplified flow, 
    # but strictly it might be separate. We'll set to FUNDED.
    
    create_audit_log(db, escrow_id, models.AuditEvent.CONFIRM_FUNDS, confirmation.custodian_id, {"code": confirmation.confirmation_code})
    
    db.commit()
    db.refresh(db_escrow)
    return db_escrow

@app.post("/milestones/{milestone_id}/approve", response_model=schemas.Milestone)
def approve_milestone(milestone_id: str, approval: schemas.ApprovalRequest, db: Session = Depends(get_db)):
    db_milestone = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    # Security Check: Ensure Escrow is Funded
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == db_milestone.escrow_id).first()
    if db_escrow.state not in [models.EscrowState.FUNDED, models.EscrowState.ACTIVE]:
        raise HTTPException(status_code=400, detail="Security Alert: Cannot approve release. Escrow validation failed (Not Funded).")

    # Validate Evidence
    # (Simplified logic: check if all required types exist in DB for this milestone)
    uploaded_evidences = db.query(models.Evidence).filter(models.Evidence.milestone_id == milestone_id).all()
    uploaded_types = [e.evidence_type for e in uploaded_evidences]
    
    missing = [t for t in db_milestone.required_evidence_types if t not in uploaded_types]
    if missing:
        raise HTTPException(status_code=400, detail=f"Cannot approve. Missing evidence: {missing}")

    db_milestone.status = models.MilestoneStatus.APPROVED
    db_milestone.approval_signature = {
        "approver": approval.approver_id,
        "signature": approval.signature,
        "timestamp": str(datetime.datetime.utcnow())
    }
    
    # Audit Log
    create_audit_log(db, db_milestone.escrow_id, models.AuditEvent.APPROVE, approval.approver_id, {"milestone_id": milestone_id})
    
    db.commit()
    db.refresh(db_milestone)
    return db_milestone

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
@app.get("/escrows/{escrow_id}/instruction/{milestone_id}", response_model=schemas.BankingInstruction)
def generate_instruction(escrow_id: str, milestone_id: str, db: Session = Depends(get_db)):
    db_milestone = db.query(models.Milestone).filter(models.Milestone.id == milestone_id, models.Milestone.escrow_id == escrow_id).first()
    if not db_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
        
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == escrow_id).first()
    if db_escrow.is_disputed or db_escrow.state == models.EscrowState.HALTED:
        raise HTTPException(status_code=400, detail="Escrow is HALTED or DISPUTED. Cannot release.")
    
    if db_milestone.status != models.MilestoneStatus.APPROVED and db_milestone.status != models.MilestoneStatus.PAID:
        raise HTTPException(status_code=400, detail="Milestone not approved")

    # In a real app, 'approvals' would be a list of all signatures collected.
    # Here we just wrap the single milestone approval.
    approvals_list = []
    if db_milestone.approval_signature:
        approvals_list.append(db_milestone.approval_signature)

    instruction = schemas.BankingInstruction(
        instruction_id=str(uuid.uuid4()),
        agreement_id=escrow_id,
        agreement_version=f"v{db_escrow.version}",
        agreement_hash=db_escrow.agreement_hash or "HASH_NOT_CALCULATED",
        payee=db_escrow.provider_id,
        amount=db_milestone.amount,
        currency="USD",
        approvals=approvals_list,
        attestation=f"All conditions defined in Agreement v{db_escrow.version} have been satisfied."
    )
    
    # In a real app, we'd mark it PAID *after* confirmation from bank, 
    # but for prototype we mark it here or assume the next step handles it.
    if db_milestone.status == models.MilestoneStatus.APPROVED:
        db_milestone.status = models.MilestoneStatus.PAID
        
        # 5. Audit Log (Payment Release)
        create_audit_log(db, escrow_id, models.AuditEvent.PAYMENT_RELEASED, "SYSTEM_INSTRUCTION", {
            "instruction_id": instruction.instruction_id,
            "payee": instruction.payee,
            "amount": instruction.amount
        })
        
        db.commit()
        
    return instruction

@app.post("/escrows/{escrow_id}/dispute", response_model=schemas.Escrow)
def dispute_escrow(escrow_id: str, db: Session = Depends(get_db)):
    db_escrow = db.query(models.Escrow).filter(models.Escrow.id == escrow_id).first()
    if not db_escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
        
    db_escrow.state = models.EscrowState.DISPUTED
    db_escrow.is_disputed = True
    
    # Audit Log
    create_audit_log(db, escrow_id, models.AuditEvent.DISPUTE, "SYSTEM_OR_USER", {"reason": "Manual Dispute Triggered"})
    
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
