
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    JSON,
    Numeric,
    String,
)

from app.database.connection import Base


class InvoiceDB(Base):

    __tablename__ = "invoices"

    invoice_id = Column(String, primary_key=True, index=True)

    vendor_name = Column(String, nullable=False)
    vendor_gst_number = Column(String, nullable=True)

    invoice_number = Column(String, nullable=False, index=True)
    invoice_date = Column(Date, nullable=False)

    purchase_order_number = Column(String, nullable=True)

    subtotal = Column(Numeric(12, 2), nullable=False)
    gst_amount = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)

    extraction_confidence = Column(Float, nullable=False)

    status = Column(String, nullable=False)

    requires_human_review = Column(
        Boolean,
        default=False,
        nullable=False
    )

    review_reason = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), nullable=False)
