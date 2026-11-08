from app.database.connection import SessionLocal
from app.database.repository import InvoiceRepository

from app.models.invoice import Invoice
from app.models.packets import InvoicePacket, ValidationResult

from app.agents.intake_agent import InvoiceIntakeAgent
from app.agents.extraction_agent import InvoiceExtractionAgent
from app.agents.gst_agent import GSTValidationAgent
from app.agents.po_agent import POValidationAgent
from app.agents.policy_agent import PolicyCheckingAgent
from app.agents.exception_agent import ExceptionHandlingAgent
from app.agents.router_agent import InvoiceRouterAgent
from app.services.audit_service import AuditService


class InvoiceWorkflowOrchestrator:

    def __init__(self):

        self.intake_agent = InvoiceIntakeAgent()
        self.extraction_agent = InvoiceExtractionAgent()
        self.gst_agent = GSTValidationAgent()
        self.po_agent = POValidationAgent()
        self.policy_agent = PolicyCheckingAgent()
        self.exception_agent = ExceptionHandlingAgent()
        self.router_agent = InvoiceRouterAgent()
        self.audit_service = AuditService()

        print("Invoice Workflow Orchestrator initialized.")

    def check_duplicate(
        self,
        packet: InvoicePacket
    ) -> InvoicePacket:
        """
        Check whether this invoice already exists in the database.
        """

        invoice = packet.invoice

        # Skip duplicate lookup if GSTIN is missing.
        # The GST agent will handle missing GSTIN validation.
        if not invoice.vendor_gst_number:
            print("Duplicate check skipped: GSTIN is missing.")
            return packet

        db = None

        try:
            # Open database session
            db = SessionLocal()

            repository = InvoiceRepository(db)

            # Search for an existing invoice
            duplicate = repository.find_duplicate(
                invoice.vendor_gst_number.strip().upper(),
                invoice.invoice_number.strip()
            )

            if duplicate:

                reason = (
                    f"Duplicate invoice detected. "
                    f"Existing invoice ID: {duplicate.invoice_id}."
                )

                packet.requires_human_review = True
                invoice.requires_human_review = True

                packet.review_reasons.append(reason)
                invoice.review_reason.append(reason)

                packet.duplicate_validation = ValidationResult(
                    check_name="Duplicate Invoice Validation",
                    passed=False,
                    message=reason
                )

                print(
                    f"Duplicate invoice detected: {invoice.invoice_id}"
                )

            else:

                packet.duplicate_validation = ValidationResult(
                    check_name="Duplicate Invoice Validation",
                    passed=True,
                    message="No duplicate invoice found."
                )

                print(
                    f"No duplicate found for {invoice.invoice_id}."
                )

        except Exception as error:

            reason = (
                "Duplicate-check database failure. "
                "Human review required."
            )

            packet.requires_human_review = True
            invoice.requires_human_review = True

            packet.processing_errors.append(
                f"{reason} Details: {error}"
            )

            packet.review_reasons.append(reason)
            invoice.review_reason.append(reason)

            packet.duplicate_validation = ValidationResult(
                check_name="Duplicate Invoice Validation",
                passed=False,
                message=reason
            )

            print(reason)

        finally:

            if db is not None:
                try:
                    db.close()
                except Exception as error:
                    packet.requires_human_review = True
                    invoice.requires_human_review = True

                    reason = (
                        "Database session cleanup failed. "
                        "Human review required."
                    )

                    packet.processing_errors.append(
                        f"{reason} Details: {error}"
                    )

                    packet.review_reasons.append(reason)
                    invoice.review_reason.append(reason)

        return packet
    
    def record_status_change(
        self,
        packet: InvoicePacket,
        old_status,
        changed_by: str,
        reason: str
    ):
        """
        Record invoice status changes.
        If audit logging fails, stop automatic processing.
        """

        new_status = packet.invoice.status

        if old_status == new_status:
            return

        try:
            self.audit_service.record_status_change(
                invoice_id=packet.invoice.invoice_id,
                old_status=old_status.value if old_status else None,
                new_status=new_status.value,
                changed_by=changed_by,
                reason=reason
            )

        except Exception as error:

            failure_reason = (
                f"Audit logging failed. Human review required. Details: {error}"
            )

            packet.processing_errors.append(failure_reason)
            packet.review_reasons.append(failure_reason)

            packet.requires_human_review = True
            packet.invoice.requires_human_review = True

            # Fail closed if the audit database is unavailable.
            from app.models.invoice import InvoiceStatus

            packet.invoice.status = InvoiceStatus.UNDER_REVIEW

            print(failure_reason)

    def persist_invoice(self, packet: InvoicePacket):
        """Save the processed invoice to the database."""

        db = None

        try:
            db = SessionLocal()
            repository = InvoiceRepository(db)

            repository.save_invoice(packet.invoice)

            print(
                f"Invoice {packet.invoice.invoice_id} "
                "persisted successfully."
            )

        except Exception as error:
            from app.models.invoice import InvoiceStatus

            reason = f"Invoice database persistence failed: {error}"
            packet.processing_errors.append(reason)
            packet.review_reasons.append(reason)
            packet.requires_human_review = True
            packet.invoice.requires_human_review = True
            packet.invoice.status = InvoiceStatus.UNDER_REVIEW
            packet.routing_decision = "human_review"
            packet.routing_reason = "Database persistence failure."

            print(reason)

        finally:
            if db is not None:
                db.close()

    
    def process_invoice(
        self,
        invoice: Invoice
    ) -> InvoicePacket:
        """Process an invoice through the complete agent workflow."""

        # Step 1: Receive invoice
        packet = self.intake_agent.receive_invoice(invoice)

        # Step 2: Check for duplicates
        packet = self.check_duplicate(packet)

        if (
            packet.processing_errors
            or (
                packet.duplicate_validation is not None
                and not packet.duplicate_validation.passed
            )
        ):
            old_status = packet.invoice.status
            packet = self.exception_agent.handle_exceptions(packet)

            audit_reason = "; ".join(
                packet.review_reasons + packet.processing_errors
            ) or "Duplicate invoice detected."

            self.record_status_change(
                packet, old_status, "exception_agent", audit_reason
            )

            packet = self.router_agent.route_invoice(packet)
            return packet

        # Step 3: Extract and validate invoice data
        packet = self.extraction_agent.extract_invoice(packet)

        # Step 4: Validate GST
        packet = self.gst_agent.validate_gst(packet)

        # Step 5: Validate purchase order
        old_status = packet.invoice.status
        packet = self.po_agent.validate_po(packet)

        print("DEBUG - PO number:", repr(packet.invoice.purchase_order_number))
        print("DEBUG - PO validation:", packet.po_validation.passed)
        print("DEBUG - PO message:", packet.po_validation.message)
        print("DEBUG - Status after PO:", packet.invoice.status.value)

        self.record_status_change(
            packet,
            old_status,
            "po_agent",
            packet.po_validation.message
        )

        if packet.processing_errors:
            packet.routing_decision = "human_review"
            packet.routing_reason = "Audit logging failure."
            return packet

        # Step 6: Check business policies
        packet = self.policy_agent.check_policies(packet)

        # Step 7: Handle exceptions
        old_status = packet.invoice.status
        packet = self.exception_agent.handle_exceptions(packet)

        audit_reason = (
            "; ".join(packet.review_reasons)
            or "No validation exceptions; invoice passed initial checks."
        )

        self.record_status_change(
            packet,
            old_status,
            "exception_agent",
            audit_reason
        )

        if packet.processing_errors:
            packet.routing_decision = "human_review"
            packet.routing_reason = "Audit logging failure."
            return packet

        # Step 8: Route invoice
        packet = self.router_agent.route_invoice(packet)

        # Step 9: Save invoice to database
        self.persist_invoice(packet)

        return packet
