
from pathlib import Path
from reportlab.pdfgen import canvas

output = Path("data/invoices/sample_invoice_test.pdf")
output.parent.mkdir(parents=True, exist_ok=True)

lines = [
    "Invoice ID: INV-PDF-001",
    "Vendor Name: ABC Supplies",
    "Vendor GSTIN: 03ABCDE1234F1Z5",
    "Invoice Number: ABC-PDF-001",
    "Invoice Date: 2026-11-08",
    "Purchase Order Number: PO-1001",
    "Subtotal: 10000.00",
    "GST Amount: 1800.00",
    "Total Amount: 11800.00",
]

pdf = canvas.Canvas(str(output))
pdf.setFont("Helvetica", 12)

y = 780
for line in lines:
    pdf.drawString(50, y, line)
    y -= 28

pdf.save()
print(f"Sample PDF created: {output}")
