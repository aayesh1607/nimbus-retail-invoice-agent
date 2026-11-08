
from app.database.audit_model import AuditLogDB


class AuditRepository:

    def __init__(self, db_session):
        self.db = db_session

    def log_status_change(
        self,
        invoice_id: str,
        old_status: str | None,
        new_status: str,
        changed_by: str,
        reason: str | None = None
    ) -> AuditLogDB:
        """
        Record an invoice status change.
        """

        audit_record = AuditLogDB(
            invoice_id=invoice_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason
        )

        try:
            self.db.add(audit_record)
            self.db.commit()
            self.db.refresh(audit_record)

            print(
                f"Audit log created for invoice {invoice_id}: "
                f"{old_status} -> {new_status}"
            )

            return audit_record

        except Exception:
            self.db.rollback()
            raise

    def get_invoice_history(self, invoice_id: str):
        """
        Retrieve all audit records for an invoice.
        """

        return (
            self.db.query(AuditLogDB)
            .filter(AuditLogDB.invoice_id == invoice_id)
            .order_by(AuditLogDB.audit_id.asc())
            .all()
        )
