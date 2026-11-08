
from datetime import date
from decimal import Decimal

from app.models.invoice import Invoice, InvoiceStatus
from app.models.packets import InvoicePacket

from app.agents.extraction_agent import InvoiceExtractionAgent
from app.agents.gst_agent import GSTValidationAgent
from app.agents.po_agent import POValidationAgent
from app.agents.policy_agent import PolicyCheckingAgent


def make_invoice(**overrides):
    """Create a fictional invoice for isolated agent tests."""

    data = {
        "invoice_id": "TEST-INV-001",
        "vendor_name": "ABC Retail Supplies",
        "vendor_gst_number": "27ABCDE1234F1Z5",
        "invoice_number": "TEST-001",
        "invoice_date": date(2026, 11, 8),
        "purchase_order_number": "PO-1001",
        "subtotal": Decimal("10000.00"),
        "gst_amount": Decimal("1800.00"),
        "total_amount": Decimal("11800.00"),
        "extraction_confidence": 0.95,
    }

    data.update(overrides)
    return Invoice(**data)


def make_packet(**overrides):
    return InvoicePacket(invoice=make_invoice(**overrides))


def test_valid_invoice_extraction():
    packet = InvoiceExtractionAgent().extract_invoice(make_packet())

    assert packet.requires_human_review is False
    assert packet.invoice.requires_human_review is False


def test_valid_gst():
    packet = GSTValidationAgent().validate_gst(make_packet())

    assert packet.gst_validation.passed is True
    assert packet.requires_human_review is False


def test_unknown_gst_requires_review():
    packet = make_packet(
        vendor_gst_number="03ABCDE1234F1Z5"
    )

    packet = GSTValidationAgent().validate_gst(packet)

    assert packet.gst_validation.passed is False
    assert packet.requires_human_review is True


def test_missing_gst_requires_review():
    packet = make_packet(vendor_gst_number=None)

    packet = GSTValidationAgent().validate_gst(packet)

    assert packet.gst_validation.passed is False
    assert packet.requires_human_review is True


def test_valid_purchase_order():
    packet = POValidationAgent().validate_po(make_packet())

    assert packet.po_validation.passed is True
    assert packet.requires_human_review is False


def test_missing_purchase_order():
    packet = make_packet(purchase_order_number=None)

    packet = POValidationAgent().validate_po(packet)

    assert packet.po_validation.passed is False
    assert packet.requires_human_review is True
    assert packet.invoice.status == InvoiceStatus.EXCEPTION


def test_mismatched_purchase_order():
    packet = make_packet(
        vendor_name="Different Vendor"
    )

    packet = POValidationAgent().validate_po(packet)

    assert packet.po_validation.passed is False
    assert packet.requires_human_review is True
    assert packet.invoice.status == InvoiceStatus.EXCEPTION


def test_high_value_invoice_requires_approval():
    packet = make_packet(
        subtotal=Decimal("60000.00"),
        gst_amount=Decimal("10800.00"),
        total_amount=Decimal("70800.00"),
    )

    packet = PolicyCheckingAgent().check_policies(packet)

    assert packet.requires_human_review is True
    assert packet.invoice.requires_human_review is True
    assert packet.policy_checks[0].passed is False


def test_normal_value_passes_policy():
    packet = PolicyCheckingAgent().check_policies(make_packet())

    assert packet.requires_human_review is False
    assert packet.policy_checks[0].passed is True


def test_low_extraction_confidence():
    packet = make_packet(extraction_confidence=0.65)

    packet = InvoiceExtractionAgent().extract_invoice(packet)

    assert packet.requires_human_review is True
    assert any(
        "confidence" in reason.lower()
        for reason in packet.review_reasons
    )


def test_incorrect_invoice_total():
    packet = make_packet(
        total_amount=Decimal("12000.00")
    )

    packet = InvoiceExtractionAgent().extract_invoice(packet)

    assert packet.requires_human_review is True
    assert any(
        "total" in reason.lower()
        for reason in packet.review_reasons
    )
