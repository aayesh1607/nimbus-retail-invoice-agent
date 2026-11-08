
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pypdf import PdfReader


class PDFExtractionService:
    """
    Extract invoice fields from text-based PDFs.

    This service does not perform OCR or validate GST/PO records.
    Those checks belong to the existing invoice workflow.
    """

    FIELD_PATTERNS = {
        "invoice_id": r"(?im)^\s*Invoice\s*ID\s*:\s*(.+?)\s*$",
        "vendor_name": r"(?im)^\s*Vendor\s*Name\s*:\s*(.+?)\s*$",
        "vendor_gst_number": r"(?im)^\s*(?:Vendor\s*)?GST(?:IN| Number)?\s*:\s*(.+?)\s*$",
        "invoice_number": r"(?im)^\s*Invoice\s*Number\s*:\s*(.+?)\s*$",
        "invoice_date": r"(?im)^\s*Invoice\s*Date\s*:\s*(.+?)\s*$",
        "purchase_order_number": r"(?im)^\s*(?:Purchase\s*Order(?:\s*Number)?|PO\s*Number)\s*:\s*(.+?)\s*$",
        "subtotal": r"(?im)^\s*Subtotal\s*:\s*(.+?)\s*$",
        "gst_amount": r"(?im)^\s*GST\s*Amount\s*:\s*(.+?)\s*$",
        "total_amount": r"(?im)^\s*Total\s*Amount\s*:\s*(.+?)\s*$",
    }

    REQUIRED_FIELDS = (
        "invoice_id",
        "vendor_name",
        "invoice_number",
        "invoice_date",
        "subtotal",
        "gst_amount",
        "total_amount",
    )

    @staticmethod
    def _amount(value: str) -> Decimal:
        cleaned = re.sub(r"[₹,\s]", "", value)
        try:
            return Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid monetary amount: {value}") from exc

    def extract(self, pdf_path: str | Path) -> dict:
        path = Path(pdf_path)

        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")

        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)

        if not text.strip():
            return {
                "data": {},
                "confidence": 0.0,
                "requires_human_review": True,
                "issues": ["No readable PDF text. OCR may be required."],
            }

        raw = {}
        for field, pattern in self.FIELD_PATTERNS.items():
            match = re.search(pattern, text)
            if match:
                raw[field] = match.group(1).strip()

        issues = []
        missing = [field for field in self.REQUIRED_FIELDS if not raw.get(field)]
        if missing:
            issues.append("Missing required fields: " + ", ".join(missing))

        data = dict(raw)

        if "invoice_date" in data:
            try:
                data["invoice_date"] = date.fromisoformat(data["invoice_date"])
            except ValueError:
                issues.append("Invoice date must use YYYY-MM-DD.")
                data.pop("invoice_date")

        for field in ("subtotal", "gst_amount", "total_amount"):
            if field in data:
                try:
                    data[field] = self._amount(data[field])
                except ValueError as exc:
                    issues.append(str(exc))
                    data.pop(field)

        # Confidence is a simple field-completeness estimate,
        # not a statistical measure of extraction accuracy.
        confidence = sum(
            field in data for field in self.REQUIRED_FIELDS
        ) / len(self.REQUIRED_FIELDS)

        if issues:
            confidence = min(confidence, 0.79)

        return {
            "data": data,
            "confidence": round(confidence, 2),
            "requires_human_review": bool(issues),
            "issues": issues,
        }
