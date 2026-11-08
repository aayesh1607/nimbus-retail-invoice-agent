
from app.database.connection import SessionLocal
from app.database.audit_repository import AuditRepository


class AuditService:

    def __init__(self):
        self.agent_name = "audit_service"

    def record_status_change(
        self,
        invoice_id: str,
        old_status: str | None,
        new_status: str,
        changed_by: str,
        reason: str | None = None
    ):
        """
        Record an invoice status transition in the database.
        """

        # No need to record unchanged statuses
        if old_status == new_status:
            return None

        db = SessionLocal()

        try:
            repository = AuditRepository(db)

            audit_record = repository.log_status_change(
                invoice_id=invoice_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
                reason=reason
            )

            return audit_record

        finally:
            db.close()

    def get_invoice_history(self, invoice_id: str):
        """
        Retrieve the complete audit history of an invoice.
        """

        db = SessionLocal()

        try:
            repository = AuditRepository(db)

            return repository.get_invoice_history(invoice_id)

        finally:
            db.close()
