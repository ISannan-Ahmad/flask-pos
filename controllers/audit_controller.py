import json
from models import AuditLog
from extensions import db


class AuditController:
    @staticmethod
    def log(user_id, action, table_name, record_id, old_value=None, new_value=None):
        """Log a critical system change to the audit trail."""
        entry = AuditLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
        )
        db.session.add(entry)
        # Don't commit here — let the caller commit as part of their transaction
