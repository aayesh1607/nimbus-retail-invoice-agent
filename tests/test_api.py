
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_api_documentation():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()


def test_required_endpoints_exist():
    response = client.get("/openapi.json")
    paths = response.json()["paths"]

    required_endpoints = [
        "/health",
        "/invoices/upload",
        "/invoices/process",
        "/invoices/review-queue",
        "/invoices/{invoice_id}",
        "/invoices/{invoice_id}/audit-history",
        "/invoices/{invoice_id}/decision",
    ]

    for endpoint in required_endpoints:
        assert endpoint in paths, f"Missing endpoint: {endpoint}"


def test_review_queue_endpoint():
    response = client.get("/invoices/review-queue")

    assert response.status_code == 200
    assert "total" in response.json()
    assert "invoices" in response.json()


def test_nonexistent_invoice_returns_404():
    response = client.get("/invoices/TEST-NOT-FOUND-999")

    assert response.status_code == 404


def test_invalid_invoice_submission_returns_422():
    response = client.post("/invoices/process", json={})

    assert response.status_code == 422


def test_decision_for_nonexistent_invoice_returns_404():
    response = client.post(
        "/invoices/TEST-NOT-FOUND-999/decision",
        json={
            "decision": "approve",
            "reviewer": "test_reviewer",
            "reason": "Testing nonexistent invoice handling."
        }
    )

    assert response.status_code == 404


def test_extract_and_process_endpoint_exists():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/invoices/extract-and-process" in response.json()["paths"]


def test_extract_and_process_rejects_non_pdf():
    response = client.post(
        "/invoices/extract-and-process",
        files={
            "file": (
                "invoice.txt",
                b"Not a PDF document",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_extract_and_process_rejects_invalid_pdf():
    response = client.post(
        "/invoices/extract-and-process",
        files={
            "file": (
                "invoice.pdf",
                b"Not a real PDF",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
