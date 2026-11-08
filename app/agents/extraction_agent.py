from decimal import Decimal
from app.models.invoice import Invoice
from app.models.packets import InvoicePacket


class InvoiceExtractionAgent:

    def __init__(self):
        self.agent_name = "extraction_agent"

    def extract_invoice(self, packet: InvoicePacket) -> InvoicePacket:
        """
        Validate extracted invoice data and check extraction confidence.
        """

        packet.current_agent = self.agent_name

        invoice = packet.invoice

        # Check extraction confidence
        if invoice.extraction_confidence < 0.8:
            packet.requires_human_review = True

            reason = (
                "Extraction confidence is below the required threshold of 0.8."
            )

            packet.review_reasons.append(reason)
            invoice.requires_human_review = True
            invoice.review_reason.append(reason)

        # Check financial calculation
        calculated_total = (
            invoice.subtotal + invoice.gst_amount
        )

        if calculated_total != invoice.total_amount:
            packet.requires_human_review = True

            reason = "Invoice total does not match subtotal plus GST."

            packet.review_reasons.append(reason)
            invoice.requires_human_review = True
            invoice.review_reason.append(reason)

        print(
            f"Extraction completed for invoice {invoice.invoice_id}."
        )

        return packet