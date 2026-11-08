
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base
from app.database.db_models import InvoiceDB
from app.database.repository import InvoiceRepository
from app.models.invoice import Invoice


@pytest.fixture
def db_session():
    """
    Create an isolated, in-memory SQLite database.
    No production database records are affected.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = TestingSession()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_invoice(
    invoice_id="DB-TEST-001",
    invoice_number="DB-INV-001",
):
    return Invoice(
        invoice_id=invoice_id,
        vendor_name="ABC Retail Supplies",
        vendor_gst_number="27ABCDE1234F1Z5",
        invoice_number=invoice_number,
        invoice_date=date(2026, 11, 8),
        purchase_order_number="PO-1001",
        subtotal=Decimal("10000.00"),
        gst_amount=Decimal("1800.00"),
        total_amount=Decimal("11800.00"),
        extraction_confidence=0.95,
    )


def test_save_invoice(db_session):
    repository = InvoiceRepository(db_session)
    invoice = make_invoice()

    saved = repository.save_invoice(invoice)

    assert saved.invoice_id == "DB-TEST-001"
    assert saved.vendor_name == "ABC Retail Supplies"
    assert saved.total_amount == Decimal("11800.00")


def test_get_invoice_by_id(db_session):
    repository = InvoiceRepository(db_session)
    repository.save_invoice(make_invoice())

    found = repository.get_invoice_by_id("DB-TEST-001")

    assert found is not None
    assert found.invoice_id == "DB-TEST-001"


def test_nonexistent_invoice_returns_none(db_session):
    repository = InvoiceRepository(db_session)

    found = repository.get_invoice_by_id("DOES-NOT-EXIST")

    assert found is None


def test_duplicate_invoice_detection(db_session):
    repository = InvoiceRepository(db_session)
    repository.save_invoice(make_invoice())

    duplicate = repository.find_duplicate(
        "27ABCDE1234F1Z5",
        "DB-INV-001",
    )

    assert duplicate is not None
    assert duplicate.invoice_id == "DB-TEST-001"


def test_different_invoice_number_not_duplicate(db_session):
    repository = InvoiceRepository(db_session)
    repository.save_invoice(make_invoice())

    duplicate = repository.find_duplicate(
        "27ABCDE1234F1Z5",
        "DIFFERENT-INV-002",
    )

    assert duplicate is None


def test_different_vendor_not_duplicate(db_session):
    repository = InvoiceRepository(db_session)
    repository.save_invoice(make_invoice())

    duplicate = repository.find_duplicate(
        "07PQRSX5678L1Z2",
        "DB-INV-001",
    )

    assert duplicate is None


def test_review_status_is_persisted(db_session):
    repository = InvoiceRepository(db_session)

    invoice = make_invoice()
    invoice.requires_human_review = True
    invoice.review_reason.append(
        "Human approval required."
    )

    repository.save_invoice(invoice)

    saved = db_session.get(InvoiceDB, invoice.invoice_id)

    assert saved.requires_human_review is True
    assert "Human approval required." in saved.review_reason
