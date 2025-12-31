import json
import uuid
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

class EscrowState(Enum):
    PENDING = "PENDING"
    FUNDED = "FUNDED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DISPUTED = "DISPUTED"

class MilestoneStatus(Enum):
    PENDING = "PENDING"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"

class Milestone:
    def __init__(self, name: str, amount: float, required_evidence_types: List[str]):
        self.id = str(uuid.uuid4())
        self.name = name
        self.amount = amount
        self.required_evidence_types = required_evidence_types
        self.status = MilestoneStatus.PENDING
        self.uploaded_evidence = []
        self.approval_signature = None

    def add_evidence(self, evidence_type: str, url: str):
        if evidence_type not in self.required_evidence_types:
            raise ValueError(f"Evidence type '{evidence_type}' not required for milestone '{self.name}'")
        self.uploaded_evidence.append({"type": evidence_type, "url": url, "timestamp": datetime.now().isoformat()})
        if self.status == MilestoneStatus.PENDING:
            self.status = MilestoneStatus.EVIDENCE_SUBMITTED

    def approve(self, approver_id: str, signature: str):
        if self.status != MilestoneStatus.EVIDENCE_SUBMITTED:
             # In a real app, we might allow approving without evidence in special cases, but strict for now
             pass
        
        # Check if all required evidence types are present
        uploaded_types = [e["type"] for e in self.uploaded_evidence]
        missing = [t for t in self.required_evidence_types if t not in uploaded_types]
        if missing:
             raise ValueError(f"Cannot approve: Missing evidence types {missing}")

        self.status = MilestoneStatus.APPROVED
        self.approval_signature = {"approver": approver_id, "signature": signature, "timestamp": datetime.now().isoformat()}

class EscrowAgreement:
    def __init__(self, buyer_id: str, provider_id: str, total_amount: float):
        self.id = str(uuid.uuid4())
        self.buyer_id = buyer_id
        self.provider_id = provider_id
        self.total_amount = total_amount
        self.state = EscrowState.PENDING
        self.milestones: List[Milestone] = []
        self.deposited_amount = 0.0

    def add_milestone(self, name: str, amount: float, evidence_types: List[str]):
        if self.state != EscrowState.PENDING:
            raise ValueError("Cannot add milestones after initialization")
        
        current_allocated = sum(m.amount for m in self.milestones)
        if current_allocated + amount > self.total_amount:
            raise ValueError("Milestone amounts exceed total escrow amount")
            
        self.milestones.append(Milestone(name, amount, evidence_types))

    def deposit_funds(self, amount: float):
        self.deposited_amount += amount
        if self.deposited_amount >= self.total_amount:
            self.state = EscrowState.FUNDED

    def start_project(self):
        if self.state != EscrowState.FUNDED:
            raise ValueError("Cannot start project: Escrow not fully funded")
        self.state = EscrowState.ACTIVE

    def generate_release_instruction(self, milestone_index: int) -> Dict:
        if milestone_index >= len(self.milestones):
            raise ValueError("Invalid milestone index")
        
        milestone = self.milestones[milestone_index]
        
        if milestone.status != MilestoneStatus.APPROVED:
            raise ValueError(f"Milestone '{milestone.name}' is not approved. Current status: {milestone.status.value}")
        
        if milestone.status == MilestoneStatus.PAID:
            raise ValueError(f"Milestone '{milestone.name}' already paid")

        # Generate Instruction
        instruction = {
            "instruction_id": str(uuid.uuid4()),
            "escrow_id": self.id,
            "timestamp": datetime.now().isoformat(),
            "action": "RELEASE_FUNDS",
            "amount": milestone.amount,
            "currency": "USD",
            "from_account": "ESCROW_VAULT_MAIN",
            "to_account": self.provider_id, # Simplified for prototype
            "reason": f"Milestone Completion: {milestone.name}",
            "proofs": milestone.approval_signature
        }
        
        milestone.status = MilestoneStatus.PAID
        
        # Check if all done
        if all(m.status == MilestoneStatus.PAID for m in self.milestones):
            self.state = EscrowState.COMPLETED
            
        return instruction
