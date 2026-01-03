from datetime import datetime
import json
import hashlib
from typing import Any
from pymongo import MongoClient
import models
from database import audit_collection

def calculate_hash(data: Any) -> str:
    """Returns SHA-256 hash of JSON-encoded data."""
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()

def create_attestation(db, entity_id, event_type, actor_username, actor_role, data, agreement_hash=None, agreement_version=None):
    """Creates a cryptographically chained attestation (audit log) in MongoDB."""
    # 1. Get previous log hash from Mongo
    last_entry = audit_collection.find_one(sort=[("timestamp", -1)])
    prev_hash = last_entry["current_hash"] if last_entry and "current_hash" in last_entry else "0" * 64
    
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
        "timestamp": datetime.utcnow()
    }
    audit_collection.insert_one(log_entry)
    return log_entry
