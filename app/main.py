from fastapi import Form
from app.services.pdf_extraction_service import PDFExtractionService
from typing import Literal
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from app.models.invoice import Invoice, InvoiceStatus
from app.workflow.orchestrator import InvoiceWorkflowOrchestrator

from app.database.connection import SessionLocal
from app.database.db_models import InvoiceDB

from app.services.audit_service import AuditService


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

app = FastAPI(
    title="Nimbus Invoice Agent",
    description="Multi-Agent Invoice Processing System",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "data" / "invoices"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# --------------------------------------------------
# HUMAN REVIEW REQUEST MODEL
# --------------------------------------------------

class ReviewDecision(BaseModel):
    decision: Literal["approve", "reject"]

    reviewer: str = Field(
        default="human_reviewer",
        min_length=1
    )

    reason: str = Field(min_length=3)


# --------------------------------------------------
# HOME ENDPOINT
# --------------------------------------------------

@app.get("/")
async def home():

    return {
        "message": "Welcome to Nimbus Invoice Agent!",
        "status": "running",
        "project": "Nimbus Retail Invoice Processing",
    }


# --------------------------------------------------
# HEALTH CHECK ENDPOINT
# --------------------------------------------------

@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "service": "invoice-agent",
    }


# --------------------------------------------------
# UPLOAD INVOICE DOCUMENT ENDPOINT
# --------------------------------------------------

@app.post("/invoices/upload")
async def upload_invoice(file: UploadFile = File(...)):

    try:

        # Get original filename safely
        original_filename = Path(
            file.filename or "invoice"
        ).name

        # Check file extension
        file_extension = Path(
            original_filename
        ).suffix.lower()

        if file_extension not in ALLOWED_EXTENSIONS:

            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Upload PDF, JPG, JPEG, or PNG."
            )

        # Read maximum allowed size plus one byte
        file_content = await file.read(MAX_FILE_SIZE + 1)

        if not file_content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        if len(file_content) > MAX_FILE_SIZE:

            raise HTTPException(
                status_code=413,
                detail="File size exceeds the 10 MB limit."
            )

        # Generate a unique filename
        stored_filename = (
            f"{uuid4().hex}{file_extension}"
        )

        # Determine destination path
        destination = UPLOAD_DIR / stored_filename

        # Save uploaded document
        destination.write_bytes(file_content)

        return {
            "message": "Invoice document uploaded successfully.",
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "file_size_bytes": len(file_content),
            "file_type": file_extension,
            "upload_status": "success",
            "storage_location": "data/invoices",
            "extraction_status": "not_performed",
            "next_step": "Submit extracted invoice details to /invoices/process."
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Invoice upload failed: {error}"
        )

    finally:
        await file.close()


# --------------------------------------------------
# PROCESS INVOICE ENDPOINT
# --------------------------------------------------

@app.post("/invoices/process")
async def process_invoice(invoice: Invoice):

    orchestrator = InvoiceWorkflowOrchestrator()

    try:

        packet = orchestrator.process_invoice(invoice)

        return packet.model_dump(mode="json")

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Invoice processing failed: {error}"
        )


# --------------------------------------------------
# HUMAN REVIEW QUEUE ENDPOINT
# --------------------------------------------------

@app.get("/invoices/review-queue")
async def get_review_queue():

    db = SessionLocal()

    try:

        invoices = (
            db.query(InvoiceDB)
            .filter(
                InvoiceDB.requires_human_review.is_(True)
            )
            .all()
        )

        return {
            "total": len(invoices),

            "invoices": [
                {
                    "invoice_id": invoice.invoice_id,
                    "vendor_name": invoice.vendor_name,
                    "total_amount": str(invoice.total_amount),
                    "status": invoice.status,
                    "review_reason": invoice.review_reason,
                }

                for invoice in invoices
            ],
        }

    finally:
        db.close()


# --------------------------------------------------
# GET INVOICE BY ID ENDPOINT
# --------------------------------------------------

@app.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str):

    db = SessionLocal()

    try:

        invoice = db.get(
            InvoiceDB,
            invoice_id
        )

        if invoice is None:

            raise HTTPException(
                status_code=404,
                detail="Invoice not found."
            )

        return {
            "invoice_id": invoice.invoice_id,
            "vendor_name": invoice.vendor_name,
            "vendor_gst_number": invoice.vendor_gst_number,
            "invoice_number": invoice.invoice_number,
            "purchase_order_number": invoice.purchase_order_number,
            "subtotal": str(invoice.subtotal),
            "gst_amount": str(invoice.gst_amount),
            "total_amount": str(invoice.total_amount),
            "status": invoice.status,
            "requires_human_review": invoice.requires_human_review,
            "review_reason": invoice.review_reason,
        }

    finally:
        db.close()


# --------------------------------------------------
# GET INVOICE AUDIT HISTORY ENDPOINT
# --------------------------------------------------

@app.get("/invoices/{invoice_id}/audit-history")
async def get_invoice_audit_history(invoice_id: str):

    db = SessionLocal()

    try:

        invoice = db.get(
            InvoiceDB,
            invoice_id
        )

        if invoice is None:

            raise HTTPException(
                status_code=404,
                detail="Invoice not found."
            )

        audit_service = AuditService()

        history = audit_service.get_invoice_history(
            invoice_id
        )

        return {
            "invoice_id": invoice_id,
            "total": len(history),

            "history": [
                {
                    "audit_id": record.audit_id,
                    "invoice_id": record.invoice_id,
                    "old_status": record.old_status,
                    "new_status": record.new_status,
                    "changed_by": record.changed_by,
                    "reason": record.reason,
                    "created_at": (
                        record.created_at.isoformat()
                        if record.created_at
                        else None
                    ),
                }

                for record in history
            ],
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve audit history: {error}"
        )

    finally:
        db.close()


# --------------------------------------------------
# HUMAN APPROVAL / REJECTION ENDPOINT
# --------------------------------------------------

@app.post("/invoices/{invoice_id}/decision")
async def review_invoice(
    invoice_id: str,
    decision: ReviewDecision
):

    db = SessionLocal()

    try:

        invoice = db.get(
            InvoiceDB,
            invoice_id
        )

        if invoice is None:

            raise HTTPException(
                status_code=404,
                detail="Invoice not found."
            )

        if not invoice.requires_human_review:

            raise HTTPException(
                status_code=400,
                detail="Invoice is not awaiting human review."
            )

        old_status = invoice.status

        if decision.decision == "approve":

            new_status = InvoiceStatus.APPROVED.value
            message = "Invoice approved successfully."

        else:

            new_status = InvoiceStatus.REJECTED.value
            message = "Invoice rejected successfully."

        invoice.status = new_status
        invoice.requires_human_review = False

        from app.database.audit_model import AuditLogDB

        audit_record = AuditLogDB(
            invoice_id=invoice_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=decision.reviewer,
            reason=decision.reason,
        )

        db.add(audit_record)

        db.commit()

        return {
            "message": message,
            "invoice_id": invoice_id,
            "old_status": old_status,
            "new_status": new_status,
            "reviewed_by": decision.reviewer,
            "reason": decision.reason,
            "payment_initiated": False,
        }

    except HTTPException:

        db.rollback()
        raise

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Review decision failed: {error}"
        )

    finally:
        db.close()


# --------------------------------------------------
# EXTRACT AND PROCESS PDF INVOICE
# --------------------------------------------------

@app.post("/invoices/extract-and-process")
async def extract_and_process_invoice(
    file: UploadFile = File(...)
):
    """
    Extract fields from a text-based PDF and process the invoice
    through the existing multi-agent workflow.

    Incomplete extraction fails closed without creating an
    invoice record or initiating any payment.
    """

    original_filename = Path(file.filename or "invoice.pdf").name
    extension = Path(original_filename).suffix.lower()

    if extension != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="This endpoint accepts PDF files only."
        )

    content = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded PDF is empty."
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="PDF exceeds the 10 MB limit."
        )

    # Basic PDF signature validation.
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF."
        )

    destination = UPLOAD_DIR / f"{uuid4().hex}.pdf"

    try:
        destination.write_bytes(content)

        extractor = PDFExtractionService()
        result = extractor.extract(destination)

        if result["requires_human_review"]:
            return {
                "status": "extraction_review_required",
                "message": (
                    "PDF extraction is incomplete. "
                    "Manual correction is required before processing."
                ),
                "extraction": result["data"],
                "confidence": result["confidence"],
                "issues": result["issues"],
                "payment_initiated": False,
            }

        invoice_data = dict(result["data"])
        invoice_data["extraction_confidence"] = result["confidence"]

        # Validate against the existing Invoice model.
        invoice = Invoice.model_validate(invoice_data)

        orchestrator = InvoiceWorkflowOrchestrator()
        packet = orchestrator.process_invoice(invoice)

        return {
            "status": "processed",
            "extraction_confidence": result["confidence"],
            "invoice": packet.model_dump(mode="json"),
            "payment_initiated": False,
        }

    except HTTPException:
        raise

    except Exception:
        # Fail closed: never continue processing after a technical error.
        raise HTTPException(
            status_code=500,
            detail=(
                "PDF extraction or invoice processing failed. "
                "Manual investigation is required."
            ),
        )
