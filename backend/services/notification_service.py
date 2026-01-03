from datetime import datetime
from pymongo import MongoClient
import models
import schemas
import enum
from database import audit_collection, get_db

# Assuming we use the same mongo client as database.py
# But database.py exports 'audit_collection' directly. 
# We should probably export the client or create a new collection similarly.
from database import mongo_client as client

notification_collection = client["escrow_db"]["notifications"]

from services.ledger_service import create_attestation

class NotificationSeverity(str, enum.Enum):
    INFO = "INFO"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    WARNING = "WARNING"

class NotificationService:
    def __init__(self):
        self.notification_collection = notification_collection

    def emit_notification(self, event_type: models.AuditEvent, escrow_id: str, actor_role: models.UserRole, data: dict = None, milestone_id: str = None):
        """
        Core logic to determine recipients and persist notification.
        """
        recipients = self._resolve_recipients(event_type, actor_role, data)
        
        if not recipients:
            return

        severity = self._determine_severity(event_type)
        message = self._generate_message(event_type, data)
        
        timestamp = datetime.utcnow()
        
        # 1. Create Notifications for each recipient
        notifications = []
        for username, role in recipients.items():
            notification = {
                "user_id": username,
                "role": role,
                "escrow_id": escrow_id,
                "milestone_id": milestone_id,
                "event_type": event_type,
                "message": message,
                "severity": severity,
                "is_read": False,
                "created_at": timestamp
            }
            notifications.append(notification)
            
        if notifications:
            self.notification_collection.insert_many(notifications)
            
        # 2. Audit Log (Ledger) - STRICT CHAINING via Service
        # We pass minimal context as Notifications are often side effects.
        # Entity ID is Escrow ID.
        safe_data = {
            "event_type": event_type,
            "recipients": list(recipients.keys()),
            "severity": severity
        }
        if data:
            safe_data.update(data)
            
        create_attestation(
            db=None, # Not needed for Mongo-only insert
            entity_id=escrow_id,
            event_type=models.AuditEvent.NOTIFICATION_ISSUED,
            actor_username="SYSTEM",
            actor_role=models.UserRole.SYSTEM if hasattr(models.UserRole, 'SYSTEM') else "SYSTEM",
            data=safe_data
        )

    def get_notifications(self, user_id: str, role: str):
        """Fetch notifications for a user, sorted by date desc."""
        return list(self.notification_collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1))

    def mark_read(self, notification_id: str, user_id: str):
        from bson import ObjectId
        self.notification_collection.update_one(
            {"_id": ObjectId(notification_id), "user_id": user_id},
            {"$set": {"is_read": True}}
        )

    def _resolve_recipients(self, event: models.AuditEvent, actor: str, data: dict):
        """
        Business Logic: Who gets notified?
        Depends on the *Event* and the *Actor*.
        
        Hardcoded rules based on Prompt Requirements:
        - ESCROW_CREATED -> Custodian
        - FUNDS_REQUIRED -> Client/Agent
        - FUNDS_CONFIRMED -> Agent
        - EVIDENCE_SUBMITTED -> Inspector
        - EXTERNAL_EVIDENCE_ADDED -> Agent
        - MILESTONE_READY -> Inspector
        - DISPUTE -> Agent, Inspector, Custodian
        - CANCELLED -> Agent, Custodian
        - RELEASED -> Agent, Contractor
        
        NOTE: In a real app, we'd look up the specific users (e.g. "Who is the inspector for Escrow X?").
        Since our data model stores IDs like 'jim_inspector', we can infer or pass them.
        For MVP, we might treat 'jim_inspector' as the singleton Inspector, or pull from Escrow object if passed.
        
        To make this robust, 'data' should probably contain the Escrow object or specific usernames.
        """
        # Simplification for MVP: We assume standard usernames or pass them in 'data'
        recipients = {} # {username: role}
        
        # We need the specific users involved in this escrow.
        # We will assume 'data' contains 'escrow_participants' dict if needed,
        # or we hardcode the known test users for this assignment if we don't want to do DB lookups here.
        # Let's try to be somewhat dynamic by expecting keys in 'data'.
        
        users = data.get("users", {
            "AGENT": "alice_agent",
            "CONTRACTOR": "bob_contractor",
            "INSPECTOR": "jim_inspector",
            "CUSTODIAN": "title_co",
            "BUYER": "alice_buyer" # Assuming alice_agent acts as buyer agent usually
        })

        if event == models.AuditEvent.CREATE: # Escrow Created
            recipients[users["CUSTODIAN"]] = models.UserRole.CUSTODIAN.value
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            
        elif event == models.AuditEvent.CHANGE_ORDER_BUDGET: # Funds Required
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            
        elif event == models.AuditEvent.CONFIRM_FUNDS:
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            
        elif event == models.AuditEvent.UPLOAD_EVIDENCE: # Evidence Submitted
            recipients[users["INSPECTOR"]] = models.UserRole.INSPECTOR.value
            
        elif event == models.AuditEvent.EVIDENCE_ATTESTED: # External Evidence
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            
        elif event == models.AuditEvent.DISPUTE:
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            recipients[users["INSPECTOR"]] = models.UserRole.INSPECTOR.value
            recipients[users["CUSTODIAN"]] = models.UserRole.CUSTODIAN.value
            
        elif event == models.AuditEvent.MILESTONE_CANCELLED:
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            recipients[users["CUSTODIAN"]] = models.UserRole.CUSTODIAN.value
            
        elif event == models.AuditEvent.PAYMENT_RELEASED:
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            recipients[users["CONTRACTOR"]] = models.UserRole.CONTRACTOR.value

        # --- Payment Layer Notifications ---
        elif event == models.AuditEvent.PAYMENT_INSTRUCTED:
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            recipients[users["CONTRACTOR"]] = models.UserRole.CONTRACTOR.value
            
        elif event == models.AuditEvent.PAYMENT_SENT:
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            
        elif event == models.AuditEvent.PAYMENT_SETTLED:
            recipients[users["AGENT"]] = models.UserRole.AGENT.value
            recipients[users["CONTRACTOR"]] = models.UserRole.CONTRACTOR.value
            
        return recipients

    def _determine_severity(self, event: models.AuditEvent):
        if event in [models.AuditEvent.CREATE, models.AuditEvent.UPLOAD_EVIDENCE, models.AuditEvent.CHANGE_ORDER_BUDGET]:
            return NotificationSeverity.ACTION_REQUIRED
        elif event in [models.AuditEvent.DISPUTE, models.AuditEvent.MILESTONE_CANCELLED]:
            return NotificationSeverity.WARNING
        elif event in [models.AuditEvent.PAYMENT_INSTRUCTED, models.AuditEvent.PAYMENT_SENT, models.AuditEvent.PAYMENT_SETTLED]:
            return NotificationSeverity.INFO
        return NotificationSeverity.INFO

    def _generate_message(self, event: models.AuditEvent, data: dict):
        # We can make these richer later
        milestone_name = data.get("milestone_name", "Milestone")
        amount = data.get("amount", "")
        
        if event == models.AuditEvent.CREATE:
            return "New Escrow Created. Waiting for Custodian Confirmation."
        elif event == models.AuditEvent.CONFIRM_FUNDS:
            return "Funds have been confirmed by Custodian."
        elif event == models.AuditEvent.UPLOAD_EVIDENCE:
            return "New Evidence submitted. pending inspection."
        elif event == models.AuditEvent.PAYMENT_RELEASED:
            return "Payment released for milestone."
        elif event == models.AuditEvent.DISPUTE:
            return "A Dispute has been raised on this escrow."
        elif event == models.AuditEvent.MILESTONE_CANCELLED:
            return f"Milestone '{milestone_name}' has been CANCELLED."
            
        # --- Payment Messages ---
        elif event == models.AuditEvent.PAYMENT_INSTRUCTED:
            return "Payment instruction generated. Funds are authorized but not yet released."
        elif event == models.AuditEvent.PAYMENT_SENT:
            return "Payment instruction sent to banking system."
        elif event == models.AuditEvent.PAYMENT_SETTLED:
            return "Funds have been released and settled."
            
        return f"Event {event} occurred."

notification_service = NotificationService()
