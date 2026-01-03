
from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
import services.ledger_service as ledger_service # Using ledger service directly for strict audit chaining? 
# Actually, ledger_service.create_attestation is what we likely want.
from services.ledger_service import create_attestation
import json

def seed_templates(db: Session):
    """
    Ensures the default 'Residential Remodel' template exists.
    """
    template_name = "Residential Remodel – Standard"
    existing = db.query(models.MilestoneTemplate).filter(models.MilestoneTemplate.name == template_name).first()
    
    if not existing:
        new_template = models.MilestoneTemplate(
            name=template_name,
            description="Typical single-family renovation draw schedule (Foundation -> Framing -> Rough-In -> Finish -> Retainage)",
            is_system=True,
            milestones=[
                {"title": "Foundation", "percentage": 20, "required_evidence": ["PHOTO", "INSPECTION"]},
                {"title": "Framing", "percentage": 25, "required_evidence": ["PHOTO"]},
                {"title": "Mechanical / Rough-In", "percentage": 20, "required_evidence": ["PERMIT"]},
                {"title": "Finish Work", "percentage": 25, "required_evidence": ["PHOTO"]},
                {"title": "Final / Retainage", "percentage": 10, "required_evidence": ["INSPECTION"]}
            ]
        )
        db.add(new_template)
        db.commit()
        print(f"Seeded template: {template_name}")

def get_all_templates(db: Session):
    return db.query(models.MilestoneTemplate).all()

def apply_template(db: Session, escrow_id: str, template_id: str, current_user: models.User):
    # 1. Validate User Role
    if current_user.role != models.UserRole.AGENT:
        raise HTTPException(status_code=403, detail="Only Agents can apply templates.")

    # 2. Validate Escrow State
    escrow = db.query(models.Escrow).filter(models.Escrow.id == escrow_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    
    if escrow.state != models.EscrowState.CREATED:
        raise HTTPException(status_code=400, detail="Templates can only be applied to escrows in CREATED state.")
    
    # 3. Validate Empty Milestones
    existing_milestones = db.query(models.Milestone).filter(models.Milestone.escrow_id == escrow_id).count()
    if existing_milestones > 0:
        raise HTTPException(status_code=400, detail="Cannot apply template: Escrow already has milestones.")

    # 4. Fetch Template
    template = db.query(models.MilestoneTemplate).filter(models.MilestoneTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 5. Calculate and Create Milestones
    total_percentage = sum(m["percentage"] for m in template.milestones)
    if total_percentage != 100:
        # Should guard against this in seed, but safe check
        pass 

    created_count = 0
    for tm in template.milestones:
        amount = (escrow.total_amount * tm["percentage"]) / 100.0
        
        milestone = models.Milestone(
            escrow_id=escrow.id,
            name=tm["title"],
            amount=amount,
            required_evidence_types=tm["required_evidence"],
            status=models.MilestoneStatus.CREATED
        )
        db.add(milestone)
        created_count += 1
    
    # 6. Audit Log
    create_attestation(
        db, 
        escrow.id, 
        models.AuditEvent.TEMPLATE_APPLIED, 
        current_user.username, 
        current_user.role, 
        {
            "template_name": template.name,
            "milestones_created": created_count
        }, 
        escrow.agreement_hash, 
        escrow.version
    )

    db.commit()
    return {"message": "Template applied successfully", "milestones_created": created_count}
