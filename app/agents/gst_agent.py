import re

from app.models.packets import InvoicePacket, ValidationResult


class GSTValidationAgent:

    def __init__(self):
        self.agent_name = "gst_agent"

        # Mock GST registry for development and testing
        self.mock_gst_registry = {
            "27ABCDE1234F1Z5": "ABC Retail Supplies",
            "07PQRSX5678L1Z2": "XYZ Distributors",
        }

    def validate_gst(self, packet: InvoicePacket) -> InvoicePacket:
        packet.current_agent = self.agent_name

        invoice = packet.invoice
        gstin = invoice.vendor_gst_number

        # Check whether GSTIN is available
        if not gstin:
            return self._flag_for_review(
                packet,
                "GSTIN is missing from the invoice."
            )

        # Check GSTIN format (15 characters)
        gstin = gstin.strip().upper()

        if not re.fullmatch(
            r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]",
            gstin
        ):
            return self._flag_for_review(
                packet,
                "GSTIN format is invalid or suspicious."
            )

        # Check against mock registry
        registered_vendor = self.mock_gst_registry.get(gstin)

        if registered_vendor is None:
            return self._flag_for_review(
                packet,
                "GSTIN is not found in the mock GST registry. "
                "Human verification is required."
            )

        # Check vendor name
        if registered_vendor.lower() != invoice.vendor_name.strip().lower():
            return self._flag_for_review(
                packet,
                "GSTIN vendor name does not match the invoice vendor."
            )

        packet.gst_validation = ValidationResult(
            check_name="GST Validation",
            passed=True,
            message="GSTIN format and mock registry vendor match."
        )

        print(f"GST validation passed for {invoice.invoice_id}.")

        return packet

    def _flag_for_review(
        self,
        packet: InvoicePacket,
        reason: str
    ) -> InvoicePacket:

        packet.requires_human_review = True
        packet.invoice.requires_human_review = True

        packet.review_reasons.append(reason)
        packet.invoice.review_reason.append(reason)

        packet.gst_validation = ValidationResult(
            check_name="GST Validation",
            passed=False,
            message=reason
        )

        print(f"GST validation requires review: {reason}")

        return packet