from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.models.invoice import Invoice


class ValidationResult(BaseModel):
    check_name: str
    passed: bool
    message: str
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class InvoicePacket(BaseModel):
    invoice: Invoice

    gst_validation: ValidationResult | None = None
    po_validation: ValidationResult | None = None
    duplicate_validation: ValidationResult | None = None

    policy_checks: list[ValidationResult] = Field(
        default_factory=list
    )

    requires_human_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)

    processing_errors: list[str] = Field(default_factory=list)

    current_agent: str = "intake_agent"

    # Router Agent fields
    routing_decision: str | None = None
    routing_reason: str | None = None