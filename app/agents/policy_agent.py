from decimal import Decimal

from app.models.invoice import InvoiceStatus
from app.models.packets import InvoicePacket, ValidationResult


class PolicyCheckingAgent:

    def __init__(self):
        self.agent_name = "policy_agent"
        self.approval_limit = Decimal("50000.00")

    def check_policies(self, packet: InvoicePacket) -> InvoicePacket:

        packet.current_agent = self.agent_name

        invoice = packet.invoice

        # Rule 1: High-value invoices require human approval
        if invoice.total_amount > self.approval_limit:

            reason = (
                "Invoice amount exceeds ₹50,000. "
                "Human approval is mandatory."
            )

            self._flag_for_review(packet, reason)

            packet.policy_checks.append(
                ValidationResult(
                    check_name="High Value Invoice Policy",
                    passed=False,
                    message=reason
                )
            )

        else:
            packet.policy_checks.append(
                ValidationResult(
                    check_name="High Value Invoice Policy",
                    passed=True,
                    message="Invoice is within the automatic amount threshold."
                )
            )

        # Preserve any review flags raised by earlier agents
        if packet.requires_human_review:
            invoice.requires_human_review = True

        print(
            f"Policy checking completed for invoice {invoice.invoice_id}."
        )

        return packet

    def _flag_for_review(
        self,
        packet: InvoicePacket,
        reason: str
    ) -> None:

        packet.requires_human_review = True
        packet.invoice.requires_human_review = True

        packet.review_reasons.append(reason)
        packet.invoice.review_reason.append(reason)