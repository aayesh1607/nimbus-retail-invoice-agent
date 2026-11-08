
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
)

from app.database.connection import Base


class AuditLogDB(Base):

    __tablename__ = "audit_logs"

    audit_id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    invoice_id = Column(
        String,
        nullable=False,
        index=True
    )

    old_status = Column(
        String,
        nullable=True
    )

    new_status = Column(
        String,
        nullable=False
    )

    changed_by = Column(
        String,
        nullable=False
    )

    reason = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
