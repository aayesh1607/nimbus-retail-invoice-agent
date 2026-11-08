from app.models.invoice import InvoiceStatus
from app.models.packets import InvoicePacket


class InvoiceRouterAgent:

    def __init__(self):
        self.agent_name = "router_agent"

    def route_invoice(self, packet: InvoicePacket) -> InvoicePacket:

        packet.current_agent = self.agent_name

        invoice = packet.invoice

        # Technical failures must never proceed automatically
        if packet.processing_errors:
            packet.requires_human_review = True
            packet.routing_decision = "human_review"
            packet.routing_reason = (
                "Technical processing failure. Manual investigation required."
            )
            invoice.status = InvoiceStatus.UNDER_REVIEW

        # Missing or mismatched PO goes to the exception queue
        elif invoice.status == InvoiceStatus.EXCEPTION:
            packet.routing_decision = "exception_queue"
            packet.routing_reason = (
                "Purchase order or another validation exception needs resolution."
            )

        # All other review conditions go to a human
        elif packet.requires_human_review:
            packet.routing_decision = "human_review"
            packet.routing_reason = (
                "One or more business rules require human review or approval."
            )
            invoice.status = InvoiceStatus.UNDER_REVIEW

        # No flags: continue to the next controlled stage
        else:
            packet.routing_decision = "ready_for_next_stage"
            packet.routing_reason = (
                "Initial validation checks passed. Awaiting the next controlled stage."
            )

        print(
            f"Invoice {invoice.invoice_id} routed to: "
            f"{packet.routing_decision}"
        )

        return packet