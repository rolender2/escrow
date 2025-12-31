from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
from enum import Enum

class EscrowState(str, Enum):
    CREATED = "CREATED"
    FUNDED = "FUNDED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DISPUTED = "DISPUTED"
    HALTED = "HALTED"

class MilestoneStatus(str, Enum):
    PENDING = "PENDING"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"

# --- Evidence ---
class EvidenceBase(BaseModel):
    evidence_type: str
    url: str

class EvidenceCreate(EvidenceBase):
    pass

class Evidence(EvidenceBase):
    id: str
    milestone_id: str
    timestamp: datetime
    class Config:
        orm_mode = True

# --- Milestone ---
class MilestoneBase(BaseModel):
    name: str
    amount: float
    required_evidence_types: List[str]

class MilestoneCreate(MilestoneBase):
    pass

class Milestone(MilestoneBase):
    id: str
    status: MilestoneStatus
    approval_signature: Optional[Any]
    evidence: List[Evidence] = []
    class Config:
        orm_mode = True

# --- Escrow ---
class EscrowCreate(BaseModel):
    buyer_id: str
    provider_id: str
    total_amount: float
    milestones: List[MilestoneCreate]

class Escrow(BaseModel):
    id: str
    buyer_id: str
    provider_id: str
    total_amount: float
    state: EscrowState
    created_at: datetime
    version: int
    agreement_hash: Optional[str]
    is_disputed: bool
    milestones: List[Milestone] = []
    class Config:
        orm_mode = True

class AuditLogCreate(BaseModel):
    entity_id: str
    event_type: str
    actor_id: str
    event_data: Any

class AuditLogRead(AuditLogCreate):
    timestamp: datetime
    previous_hash: str
    current_hash: str
    class Config:
        orm_mode = True

class FundConfirmation(BaseModel):
    custodian_id: str
    confirmation_code: str

# --- API Specific ---
class ApprovalRequest(BaseModel):
    approver_id: str
    signature: str

class BankingInstruction(BaseModel):
    instruction_id: str
    agreement_id: str
    agreement_version: str
    agreement_hash: str
    payee: str
    amount: float
    currency: str = "USD"
    approvals: List[Any] # Specific signature objects
    attestation: str
