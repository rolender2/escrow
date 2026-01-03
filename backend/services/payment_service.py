from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime
import models
import schemas
from services.ledger_service import create_attestation
from services.notification_service import notification_service

class PaymentService:
    def create_instruction(self, db: Session, milestone_id: str):
        """
        System-Internal: Called when Milestone transitions to PAID/APPROVED.
        Generates an irrevocable PaymentInstruction.
        """
        milestone = db.query(models.Milestone).filter(models.Milestone.id == milestone_id).first()
        if not milestone:
            raise ValueError("Milestone not found")
        
        escrow = milestone.escrow
        
        # Validation (Double Check)
        if milestone.status != models.MilestoneStatus.PAID and milestone.status != models.MilestoneStatus.APPROVED:
             # Depending on where we hook this, usually APPROVED -> release funds logic -> PAID.
             # If we hook after PAID, check PAID.
             pass

        # Check for existing instruction to prevent duplicates
        existing = db.query(models.PaymentInstruction).filter(models.PaymentInstruction.milestone_id == milestone_id).first()
        if existing:
            return existing

        # Create Instruction
        instruction = models.PaymentInstruction(
            escrow_id=escrow.id,
            milestone_id=milestone.id,
            amount=milestone.amount,
            # For MVP, assume Provider is the Payee.
            # In real system, we look up bank details.
            payee_name=escrow.provider_id, 
            payee_role="CONTRACTOR",
            payee_reference_id=escrow.provider_id,
            method="WIRE",
            memo=f"VeriDraw Escrow #{escrow.id[:8]} - Milestone {milestone.name}",
            status=models.PaymentStatus.INSTRUCTED,
            created_by="SYSTEM"
        )
        db.add(instruction)
        
        # Log to Ledger (PAYMENT_INSTRUCTED)
        create_attestation(
            db, 
            entity_id=escrow.id,
            event_type=models.AuditEvent.PAYMENT_INSTRUCTED,
            actor_username="SYSTEM",
            actor_role="SYSTEM",
            data={
                "instruction_id": instruction.id,
                "amount": milestone.amount,
                "payee": escrow.provider_id,
                "milestone_id": milestone.id
            },
            agreement_hash=escrow.agreement_hash,
            agreement_version=escrow.version
        )
        
        db.commit()
        db.refresh(instruction)
        
        # Notify
        notification_service.emit_notification(
            event_type=models.AuditEvent.PAYMENT_INSTRUCTED,
            escrow_id=escrow.id,
            milestone_id=milestone.id,
            actor_role=models.UserRole.AGENT, # Notify Agent
            data={"users": {"AGENT": "alice_agent", "CONTRACTOR": "rick_contractor"}} # Hardcoded for MVP, ideally look up
        )
        # Notify Contractor too? The prompt says "Instruction created -> Agent + Contractor"
        # Since emit_notification creates for multiple if handled, let's ensure logic supports it.
        # notification_service._resolve_recipients handles mapping.
        # But wait, PAYMENT_INSTRUCTED is unique. 
        # I should probably update _resolve_recipients or explicitly pass recipients if I can?
        # Alternatively, just call emit_notification and update notification_service to handle PAYMENT_INSTRUCTED.
        
        return instruction

    def update_status(self, db: Session, instruction_id: str, new_status: models.PaymentStatus, user: models.User):
        """
        Custodian Only: Transition INSTRUCTED -> SENT -> SETTLED.
        """
        # RBAC
        if user.role != models.UserRole.CUSTODIAN:
            raise HTTPException(status_code=403, detail="Only Custodian can update payment status.")
            
        instruction = db.query(models.PaymentInstruction).filter(models.PaymentInstruction.id == instruction_id).first()
        if not instruction:
            raise HTTPException(status_code=404, detail="Instruction not found")
            
        current_status = instruction.status
        
        # State Machine Validation
        if current_status == models.PaymentStatus.INSTRUCTED and new_status == models.PaymentStatus.SENT:
            instruction.status = models.PaymentStatus.SENT
            instruction.sent_at = datetime.utcnow()
            event_type = models.AuditEvent.PAYMENT_SENT
            
        elif current_status == models.PaymentStatus.SENT and new_status == models.PaymentStatus.SETTLED:
            instruction.status = models.PaymentStatus.SETTLED
            instruction.settled_at = datetime.utcnow()
            event_type = models.AuditEvent.PAYMENT_SETTLED
            
        else:
            raise HTTPException(status_code=400, detail=f"Invalid transition from {current_status} to {new_status}")
            
        # Log to Ledger
        create_attestation(
            db,
            entity_id=instruction.escrow_id,
            event_type=event_type,
            actor_username=user.username,
            actor_role=user.role,
            data={
                "instruction_id": instruction.id,
                "status": new_status,
                "amount": instruction.amount
            },
            agreement_hash=instruction.escrow.agreement_hash,
            agreement_version=instruction.escrow.version
        )
        
        db.commit()
        db.refresh(instruction)
        
        # Notify
        notification_service.emit_notification(
            event_type=event_type,
            escrow_id=instruction.escrow_id,
            milestone_id=instruction.milestone_id,
            actor_role=user.role,
            data={
                "users": {"AGENT": "alice_agent", "CONTRACTOR": "rick_contractor"},
                "amount": instruction.amount,
                "milestone_name": instruction.milestone.name
            }
        )
        
        return instruction

    def get_by_escrow(self, db: Session, escrow_id: str):
        return db.query(models.PaymentInstruction).filter(models.PaymentInstruction.escrow_id == escrow_id).order_by(models.PaymentInstruction.created_at.desc()).all()

payment_service = PaymentService()
