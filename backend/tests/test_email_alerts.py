import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import EmailAlertLog

client = TestClient(app)


def test_user_email_alert_status_and_test_dispatch():
    unique_suffix = f"email_{uuid.uuid4().hex[:8]}"
    reg = client.post(
        "/api/auth/register",
        json={
            "username": f"u_{unique_suffix}",
            "email": f"{unique_suffix}@example.com",
            "password": "Password123",
            "name": "Email Alert User",
            "phone_number": "+91 9999900000",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check alert status includes email
    status_res = client.get("/api/alerts/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["has_email"] is True
    assert status_data["email"] == f"{unique_suffix}@example.com"
    assert "recent_email_alerts" in status_data

    # 2. Test send verification email
    test_res = client.post(
        "/api/alerts/send-test-email",
        headers=headers,
    )
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert test_data["status"] == "success"
    assert "dispatched" in test_data["message"]
    assert test_data["log"]["email"] == f"{unique_suffix}@example.com"
    assert test_data["log"]["status"] == "delivered"

    # 3. Check email logs endpoint
    logs_res = client.get("/api/alerts/email-logs", headers=headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    assert logs[0]["email"] == f"{unique_suffix}@example.com"
    assert "Nidhi Pilot Email Alert" in logs[0]["subject"]


def test_email_gateway_config_api():
    unique_suffix = f"smtp_{uuid.uuid4().hex[:8]}"
    reg = client.post(
        "/api/auth/register",
        json={
            "username": f"u_{unique_suffix}",
            "email": f"{unique_suffix}@example.com",
            "password": "Password123",
            "name": "SMTP Config User",
        },
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get initial email config
    get_res = client.get("/api/alerts/email-config", headers=headers)
    assert get_res.status_code == 200
    assert "is_configured" in get_res.json()

    # 2. Update email gateway config with Gmail settings
    update_res = client.post(
        "/api/alerts/email-config",
        json={
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "test_alerts@gmail.com",
            "smtp_password": "abcd efgh ijkl mnop",
            "smtp_from": "test_alerts@gmail.com",
            "smtp_tls": True,
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    up_data = update_res.json()
    assert up_data["is_configured"] is True
    assert up_data["provider"] == "Gmail"
    assert up_data["smtp_host"] == "smtp.gmail.com"
    assert "test" in up_data["smtp_user_masked"]

    from app.services.email_service import save_email_gateway_credentials
    save_email_gateway_credentials(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="",
        smtp_password="",
        smtp_from="",
        smtp_tls=True,
    )


def test_budget_overrun_triggers_email_notification():
    unique_suffix = f"overrun_{uuid.uuid4().hex[:8]}"
    reg = client.post(
        "/api/auth/register",
        json={
            "username": f"u_{unique_suffix}",
            "email": f"{unique_suffix}@example.com",
            "password": "Password123",
            "name": "Overrun Email User",
        },
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set Food category limit to 1500
    cats_res = client.get("/api/categories", headers=headers)
    food_cat = next((c for c in cats_res.json() if c["name"] == "Food & Dining"), None)
    assert food_cat is not None
    client.put(
        f"/api/categories/{food_cat['id']}",
        json={"budget_limit": 1500.0},
        headers=headers,
    )

    # Post an expense that exceeds budget (2400 > 1500)
    current_date = "2026-10-10"
    client.post(
        "/api/transactions",
        json={
            "description": "Team lunch buffet",
            "amount": 2400.0,
            "transaction_type": "expense",
            "category": "Food & Dining",
            "date": current_date,
            "payment_method": "UPI",
        },
        headers=headers,
    )

    # Verify email alert was dispatched and logged
    logs_res = client.get("/api/alerts/email-logs", headers=headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    latest_email = logs[0]
    assert latest_email["email"] == f"{unique_suffix}@example.com"
    assert "Food & Dining" in latest_email["subject"] or "Food & Dining" in latest_email["html_body"]
    assert "Budget Exceeded" in latest_email["subject"]
