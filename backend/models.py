from sqlalchemy import Column, String, Float, Enum, ForeignKey, DateTime, JSON, Integer, Boolean
from sqlalchemy.orm import relationship
import enum
import uuid
from datetime import datetime
from database import Base

class EscrowState(str, enum.Enum):
    CREATED = "CREATED"       # Initial state, funds NOT yet confirmed
    FUNDED = "FUNDED"         # Funds confirmed by Custodian
    ACTIVE = "ACTIVE"         # Work in progress
    COMPLETED = "COMPLETED"
    DISPUTED = "DISPUTED"
    HALTED = "HALTED"         # Stopped due to dispute

class UserRole(str, enum.Enum):
    AGENT = "AGENT"
    CONTRACTOR = "CONTRACTOR"
    INSPECTOR = "INSPECTOR"
    CUSTODIAN = "CUSTODIAN"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(Enum(UserRole))
    organization_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

class AuditEvent(str, enum.Enum):
    CREATE = "CREATE"
    CONFIRM_FUNDS = "CONFIRM_FUNDS"
    UPLOAD_EVIDENCE = "UPLOAD_EVIDENCE"
    APPROVE = "APPROVE"
    DISPUTE = "DISPUTE"
    PAYMENT_RELEASED = "PAYMENT_RELEASED"
    AGREEMENT_CHANGE = "AGREEMENT_CHANGE"
    CHANGE_ORDER_BUDGET = "CHANGE_ORDER_BUDGET"
    CHANGE_ORDER_SCOPE = "CHANGE_ORDER_SCOPE"
    CHANGE_ORDER_ADDED = "CHANGE_ORDER_ADDED"
    EVIDENCE_ATTESTED = "EVIDENCE_ATTESTED"
    NOTIFICATION_ISSUED = "NOTIFICATION_ISSUED"
    DISPUTE_RESOLVED = "DISPUTE_RESOLVED"
    MILESTONE_CANCELLED = "MILESTONE_CANCELLED"

class EvidenceOrigin(str, enum.Enum):
    CONTRACTOR = "CONTRACTOR"
    THIRD_PARTY = "THIRD_PARTY"

class EvidenceSourceType(str, enum.Enum):
    PHOTO = "PHOTO"
    PDF = "PDF"
    ESIGN = "ESIGN"
    URL = "URL"

class MilestoneStatus(str, enum.Enum):
    CREATED = "CREATED" # Waiting for funding
    PENDING = "PENDING"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    DISPUTED = "DISPUTED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class Escrow(Base):
    __tablename__ = "escrows"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String, index=True)
    provider_id = Column(String, index=True)
    total_amount = Column(Float)
    funded_amount = Column(Float, default=0.0)
    state = Column(Enum(EscrowState), default=EscrowState.CREATED)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # -- Phase 3: Immutability & Versioning --
    version = Column(Integer, default=1)
    previous_version_hash = Column(String, nullable=True) # Hash of the previous version row
    agreement_hash = Column(String, nullable=True)        # Hash of *this* version's terms
    is_disputed = Column(Boolean, default=False)
    
    milestones = relationship("Milestone", back_populates="escrow")

class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    escrow_id = Column(String, ForeignKey("escrows.id"))
    name = Column(String)
    amount = Column(Float)
    required_evidence_types = Column(JSON) # List of strings e.g. ["Photo", "Invoice"]
    status = Column(Enum(MilestoneStatus), default=MilestoneStatus.PENDING)
    
    # Store approval signature here for simplicity
    approval_signature = Column(JSON, nullable=True) 

    escrow = relationship("Escrow", back_populates="milestones")
    evidence = relationship("Evidence", back_populates="milestone")

class Evidence(Base):
    __tablename__ = "evidences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    milestone_id = Column(String, ForeignKey("milestones.id"))
    evidence_type = Column(String) # Keeping for backward compat / UI labels (e.g. "Invoice")
    url = Column(String)
    
    # New Fields for External Evidence
    origin = Column(Enum(EvidenceOrigin), default=EvidenceOrigin.CONTRACTOR)
    source_type = Column(Enum(EvidenceSourceType), default=EvidenceSourceType.PHOTO)
    submitted_by_role = Column(String, nullable=True) # e.g. "INSPECTOR"

    timestamp = Column(DateTime, default=datetime.utcnow)

    milestone = relationship("Milestone", back_populates="evidence")
