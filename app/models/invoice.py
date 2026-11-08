from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field


class InvoiceStatus(str, Enum):
    RECEIVED = "received"
    EXTRACTED = "extracted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXCEPTION = "exception"


class Invoice(BaseModel):
    invoice_id: str
    vendor_name: str
    vendor_gst_number: str | None = None

    invoice_number: str
    invoice_date: date

    purchase_order_number: str | None = None

    subtotal: Decimal = Field(ge=0)
    gst_amount: Decimal = Field(ge=0)
    total_amount: Decimal = Field(gt=0)

    extraction_confidence: float = Field(ge=0, le=1)

    status: InvoiceStatus = InvoiceStatus.RECEIVED

    requires_human_review: bool = False
    review_reason: list[str] = Field(default_factory=list)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )