
from pathlib import Path

from app.services.pdf_extraction_service import PDFExtractionService


SAMPLE_PDF = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "invoices"
    / "sample_invoice_test.pdf"
)


def test_sample_pdf_exists():
    assert SAMPLE_PDF.is_file(), (
        "Sample PDF missing. Run: "
        "python tests/create_sample_invoice.py"
    )


def test_pdf_extraction_reads_invoice_fields():
    result = PDFExtractionService().extract(SAMPLE_PDF)
    data = result["data"]

    assert data["invoice_id"] == "INV-PDF-001"
    assert data["vendor_name"] == "ABC Supplies"
    assert data["invoice_number"] == "ABC-PDF-001"
    assert data["purchase_order_number"] == "PO-1001"


def test_pdf_extraction_reads_amounts():
    result = PDFExtractionService().extract(SAMPLE_PDF)
    data = result["data"]

    assert str(data["subtotal"]) == "10000.00"
    assert str(data["gst_amount"]) == "1800.00"
    assert str(data["total_amount"]) == "11800.00"


def test_complete_pdf_does_not_require_extraction_review():
    result = PDFExtractionService().extract(SAMPLE_PDF)

    assert result["confidence"] == 1.0
    assert result["requires_human_review"] is False
    assert result["issues"] == []
