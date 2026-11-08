from decimal import Decimal

from app.models.invoice import InvoiceStatus
from app.models.packets import InvoicePacket, ValidationResult


class POValidationAgent:

    def __init__(self):
        self.agent_name = "po_agent"

        # Mock purchase-order database for development
        self.mock_po_registry = {
            "PO-1001": {
                "vendor_name": "ABC Retail Supplies",
                "subtotal": Decimal("10000.00"),
            },
            "PO-1002": {
                "vendor_name": "XYZ Distributors",
                "subtotal": Decimal("25000.00"),
            },
        }

    def validate_po(self, packet: InvoicePacket) -> InvoicePacket:

        packet.current_agent = self.agent_name

        invoice = packet.invoice
        po_number = invoice.purchase_order_number

        # Check whether PO number exists
        if not po_number:
            return self._flag_exception(
                packet,
                "Purchase order number is missing."
            )

        # Look up purchase order
        po_record = self.mock_po_registry.get(po_number)

        if po_record is None:
            return self._flag_exception(
                packet,
                f"Purchase order {po_number} was not found."
            )

        # Check vendor name
        if (
            po_record["vendor_name"].strip().lower()
            != invoice.vendor_name.strip().lower()
        ):
            return self._flag_exception(
                packet,
                "Invoice vendor does not match the PO vendor."
            )

        # Check invoice subtotal against PO amount
        if invoice.subtotal != po_record["subtotal"]:
            return self._flag_exception(
                packet,
                "Invoice subtotal does not match the PO amount."
            )

        # All checks passed
        packet.po_validation = ValidationResult(
            check_name="Purchase Order Validation",
            passed=True,
            message="PO number, vendor and subtotal match."
        )

        print(f"PO validation passed for {invoice.invoice_id}.")

        return packet

    def _flag_exception(
        self,
        packet: InvoicePacket,
        reason: str
    ) -> InvoicePacket:

        packet.requires_human_review = True
        packet.invoice.requires_human_review = True

        packet.review_reasons.append(reason)
        packet.invoice.review_reason.append(reason)

        # Missing or mismatched PO must enter exception status
        packet.invoice.status = InvoiceStatus.EXCEPTION

        packet.po_validation = ValidationResult(
            check_name="Purchase Order Validation",
            passed=False,
            message=reason
        )

        print(f"PO exception: {reason}")

        return packet