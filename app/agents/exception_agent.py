from app.models.invoice import InvoiceStatus
from app.models.packets import InvoicePacket


class ExceptionHandlingAgent:

    def __init__(self):
        self.agent_name = "exception_agent"

    def handle_exceptions(
        self,
        packet: InvoicePacket
    ) -> InvoicePacket:

        packet.current_agent = self.agent_name

        # Collect all review reasons without duplicates
        reasons = list(dict.fromkeys(
            packet.review_reasons
            + packet.invoice.review_reason
            + packet.processing_errors
        ))

        # Technical failures must fail closed
        if packet.processing_errors:
            packet.requires_human_review = True

        if packet.requires_human_review or reasons:

            packet.requires_human_review = True
            packet.invoice.requires_human_review = True

            packet.review_reasons = reasons
            packet.invoice.review_reason = reasons

            # Preserve PO exceptions
            if packet.invoice.status != InvoiceStatus.EXCEPTION:
                packet.invoice.status = InvoiceStatus.UNDER_REVIEW

            print(
                f"Invoice {packet.invoice.invoice_id} "
                "requires human review."
            )

        else:
            packet.invoice.status = InvoiceStatus.EXTRACTED

            print(
                f"Invoice {packet.invoice.invoice_id} "
                "has no identified exceptions."
            )

        return packet