import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, get_db
from app.models import Category, MobileAlertLog, RecurringExpense, SalaryRecord, Transaction, User

client = TestClient(app)


def test_user_phone_number_and_alerts_flow():
    # 1. Register a user with unique phone number and credentials
    unique_suffix = f"phone_{uuid.uuid4().hex[:8]}"
    reg_res = client.post(
        "/api/auth/register",
        json={
            "username": f"u_{unique_suffix}",
            "email": f"{unique_suffix}@example.com",
            "password": "Password123",
            "name": "Phone Test User",
            "phone_number": "+91 9876543210",
        },
    )
    assert reg_res.status_code == 201
    auth_data = reg_res.json()
    token = auth_data["access_token"]
    user_info = auth_data["user"]
    assert user_info["phone_number"] == "+91 9876543210"

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Update phone number via profile endpoint
    up_res = client.put(
        "/api/auth/profile",
        json={
            "name": "Updated Phone User",
            "phone_number": "+91 9988776655",
        },
        headers=headers,
    )
    assert up_res.status_code == 200
    assert up_res.json()["phone_number"] == "+91 9988776655"

    # Verify /api/auth/me returns updated phone number
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["phone_number"] == "+91 9988776655"


def test_recurring_expenses_crud():
    unique_suffix = f"rec_{uuid.uuid4().hex[:8]}"
    reg = client.post(
        "/api/auth/register",
        json={
            "username": f"u_{unique_suffix}",
            "email": f"{unique_suffix}@example.com",
            "password": "Password123",
            "name": "Recurring User",
            "phone_number": "+91 9123456780",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Add monthly common expenses (EMI, Bill, Insurance)
    emi_res = client.post(
        "/api/recurring-expenses",
        json={
            "title": "HDFC Car Loan EMI",
            "category": "Transportation",
            "amount": 12500.0,
            "due_day": 5,
            "payment_method": "Auto-Debit",
            "expense_type": "emi",
            "notes": "Loan acct #9872",
        },
        headers=headers,
    )
    assert emi_res.status_code == 201
    emi_data = emi_res.json()
    assert emi_data["title"] == "HDFC Car Loan EMI"
    assert emi_data["amount"] == 12500.0
    emi_id = emi_data["id"]

    ins_res = client.post(
        "/api/recurring-expenses",
        json={
            "title": "Star Health Insurance Premium",
            "category": "Healthcare",
            "amount": 3200.0,
            "due_day": 10,
            "payment_method": "Net Banking",
            "expense_type": "insurance",
            "notes": "Annual family floater instalment",
        },
        headers=headers,
    )
    assert ins_res.status_code == 201

    bill_res = client.post(
        "/api/recurring-expenses",
        json={
            "title": "BESCOM Electricity Bill",
            "category": "Bills & Utilities",
            "amount": 1850.0,
            "due_day": 15,
            "payment_method": "UPI",
            "expense_type": "bill",
        },
        headers=headers,
    )
    assert bill_res.status_code == 201

    # 2. Get list and summary
    list_res = client.get("/api/recurring-expenses", headers=headers)
    assert list_res.status_code == 200
    summary = list_res.json()
    assert summary["active_count"] == 3
    assert summary["total_monthly_commitment"] == 12500.0 + 3200.0 + 1850.0
    assert summary["breakdown_by_type"]["emi"] == 12500.0
    assert summary["breakdown_by_type"]["insurance"] == 3200.0
    assert summary["breakdown_by_type"]["bill"] == 1850.0

    # 3. Log a recurring expense as a transaction
    log_res = client.post(f"/api/recurring-expenses/{emi_id}/log-transaction", headers=headers)
    assert log_res.status_code == 200
    txn_data = log_res.json()
    assert txn_data["amount"] == 12500.0
    assert "HDFC Car Loan EMI" in txn_data["description"]
    assert txn_data["transaction_type"] == "expense"

    # 4. Update and Delete
    update_res = client.put(
        f"/api/recurring-expenses/{emi_id}",
        json={"amount": 13000.0},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["amount"] == 13000.0

    del_res = client.delete(f"/api/recurring-expenses/{emi_id}", headers=headers)
    assert del_res.status_code == 200


def test_budget_overrun_warning_and_mobile_alert_dispatch():
    unique_suffix = f"alert_{uuid.uuid4().hex[:8]}"
    reg = client.post(
        "/api/auth/register",
        json={
            "username": f"u_{unique_suffix}",
            "email": f"{unique_suffix}@example.com",
            "password": "Password123",
            "name": "Arjun Mobile",
            "phone_number": "+91 9888877777",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set Food & Dining category limit to 2000
    cats_res = client.get("/api/categories", headers=headers)
    assert cats_res.status_code == 200
    food_cat = next((c for c in cats_res.json() if c["name"] == "Food & Dining"), None)
    assert food_cat is not None
    client.put(
        f"/api/categories/{food_cat['id']}",
        json={"budget_limit": 2000.0},
        headers=headers,
    )

    # Initially alert status should not be over budget
    status_1 = client.get("/api/alerts/status", headers=headers).json()
    assert status_1["has_phone"] is True
    assert status_1["phone_number"] == "+91 9888877777"
    assert status_1["is_over_budget"] is False

    # Add an expense of ₹2,800 on Food & Dining (exceeds ₹2,000 limit by ₹800)
    current_date = "2026-10-10"
    txn_res = client.post(
        "/api/transactions",
        json={
            "description": "Dinner with friends at barbeque",
            "amount": 2800.0,
            "transaction_type": "expense",
            "category": "Food & Dining",
            "date": current_date,
            "payment_method": "UPI",
        },
        headers=headers,
    )
    assert txn_res.status_code == 201

    # Check alert status: now over budget!
    status_2 = client.get("/api/alerts/status", headers=headers).json()
    assert status_2["is_over_budget"] is True
    assert status_2["warning_count"] >= 1
    food_warning = next((w for w in status_2["warnings"] if w["category"] == "Food & Dining"), None)
    assert food_warning is not None
    assert food_warning["excess"] == 800.0

    # Verify SMS alert was dispatched and logged to user mobile number
    logs_res = client.get("/api/alerts/logs", headers=headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    latest_sms = logs[0]
    assert latest_sms["phone_number"] == "+91 9888877777"
    assert latest_sms["status"] in ["delivered", "failed"]


    # Send instant test SMS
    test_sms = client.post(
        "/api/alerts/send-test",
        headers=headers,
    )
    assert test_sms.status_code == 200
    assert "dispatched" in test_sms.json()["message"]
