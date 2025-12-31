import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from nexus.modules.database import database

logger = logging.getLogger("nexus.audit")

class AuditManager:
    """
    Centralized Audit System.
    Logs every critical action (C/R/U/D) with User ID and Session ID.
    """
    
    async def log_event(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        session_id: Optional[str] = None,
        details: Dict[str, Any] = None,
        ip_address: str = None
    ):
        """
        Writes an audit record to the DB.
        """
        try:
            query = """
            INSERT INTO audit_logs 
            (user_id, session_id, action, resource_type, resource_id, details, ip_address)
            VALUES (:uid, :sid, :act, :rtype, :rid, :det, :ip)
            """
            
            # Sanitize details for JSON
            details_json = json.dumps(details, default=str) if details else "{}"
            
            await database.execute(query, {
                "uid": user_id,
                "sid": session_id,
                "act": action,
                "rtype": resource_type,
                "rid": str(resource_id),
                "det": details_json,
                "ip": ip_address
            })
            
            logger.info(f"AUDIT [{user_id}] {action} {resource_type}:{resource_id}")
            
        except Exception as e:
            # Fallback: Don't crash the app if audit fails, but log heavily
            logger.critical(f"AUDIT FAILURE: {e} - Data: {user_id} {action} {resource_type}")

audit_manager = AuditManager()
