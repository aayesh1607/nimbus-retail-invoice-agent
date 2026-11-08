
from app.database.db_models import InvoiceDB
from app.models.invoice import Invoice


class InvoiceRepository:

    def __init__(self, db_session):
        self.db = db_session

    def save_invoice(self, invoice: Invoice) -> InvoiceDB:
        """
        Save an invoice to the database.
        """

        db_invoice = InvoiceDB(
            invoice_id=invoice.invoice_id,
            vendor_name=invoice.vendor_name,
            vendor_gst_number=invoice.vendor_gst_number,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            purchase_order_number=invoice.purchase_order_number,
            subtotal=invoice.subtotal,
            gst_amount=invoice.gst_amount,
            total_amount=invoice.total_amount,
            extraction_confidence=invoice.extraction_confidence,
            status=invoice.status.value,
            requires_human_review=invoice.requires_human_review,
            review_reason=invoice.review_reason,
            created_at=invoice.created_at.replace(tzinfo=None),
        )

        try:
            self.db.add(db_invoice)
            self.db.commit()
            self.db.refresh(db_invoice)

            print(f"Invoice {invoice.invoice_id} saved successfully.")

            return db_invoice

        except Exception:
            self.db.rollback()
            raise

    def get_invoice_by_id(self, invoice_id: str):
        """
        Retrieve an invoice using its ID.
        """
    def find_duplicate(
        self,
        vendor_gst_number: str,
        invoice_number: str
    ):
        """
        Check whether the vendor has already submitted this invoice.
        """

        return self.db.query(InvoiceDB).filter(
            InvoiceDB.vendor_gst_number == vendor_gst_number,
            InvoiceDB.invoice_number == invoice_number
        ).first()

        return self.db.get(InvoiceDB, invoice_id)
