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
    CREATED = "CREATED"
    PENDING = "PENDING"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    DISPUTED = "DISPUTED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class EvidenceOrigin(str, Enum):
    CONTRACTOR = "CONTRACTOR"
    THIRD_PARTY = "THIRD_PARTY"

class EvidenceSourceType(str, Enum):
    PHOTO = "PHOTO"
    PDF = "PDF"
    ESIGN = "ESIGN"
    URL = "URL"

# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserBase(BaseModel):
    username: str
    role: str # We might want strict Enum validation here, but str is fine for Pydantic <-> SQLAlchemy matching
    
class UserCreate(UserBase):
    password: str
    organization_id: Optional[str] = None

class User(UserBase):
    id: str
    is_active: bool
    organization_id: Optional[str] = None
    class Config:
        orm_mode = True

# --- Evidence ---
class EvidenceBase(BaseModel):
    evidence_type: str
    url: str
    origin: Optional[EvidenceOrigin] = EvidenceOrigin.CONTRACTOR
    source_type: Optional[EvidenceSourceType] = EvidenceSourceType.PHOTO
    submitted_by_role: Optional[str] = None

class EvidenceCreate(EvidenceBase):
    pass

class Evidence(EvidenceBase):
    id: str
    milestone_id: str
    timestamp: datetime
    class Config:
        orm_mode = True

class ExternalEvidenceRequest(BaseModel):
    # For file uploads, these come from Form Data, but for validation we can keep structure conceptual
    source_type: EvidenceSourceType
    # File is handled separately in FastAPI via UploadFile

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

class EscrowUpdate(BaseModel):
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
    funded_amount: float = 0.0
    class Config:
        orm_mode = True

class ChangeBudgetRequest(BaseModel):
    amount_delta: float
    milestone_name: str
    evidence_type: str = "Invoice"

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

class DisputeResolutionRequest(BaseModel):
    resolution: str # "RESUME" or "CANCEL"

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

# --- Payment Instructions ---
class PaymentStatus(str, Enum):
    INSTRUCTED = "INSTRUCTED"
    SENT = "SENT"
    SETTLED = "SETTLED"

class PaymentInstructionBase(BaseModel):
    payee_name: str
    payee_role: str
    amount: float
    currency: str
    method: str
    memo: str

class PaymentInstruction(PaymentInstructionBase):
    id: str
    escrow_id: str
    milestone_id: str
    status: PaymentStatus
    created_at: datetime
    sent_at: Optional[datetime]
    settled_at: Optional[datetime]
    
    class Config:
        orm_mode = True

class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus
