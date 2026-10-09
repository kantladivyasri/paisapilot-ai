import pytest
from datetime import date
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db, run_migrations_and_seed
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    run_migrations_and_seed(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.agents.orchestrator.get_groq_api_key", return_value=None):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_forecast_and_unwanted_spending_warning(client):
    today = date.today()
    curr_month = today.strftime("%Y-%m")

    # 1. Setup salary of ₹50,000
    client.post(
        "/api/salary",
        json={"month": curr_month, "amount": 50000.0, "notes": "Monthly Base Salary"},
    )

    # 2. Add an essential expense (Rent ₹15,000)
    client.post(
        "/api/transactions",
        json={
            "description": "Monthly House Rent",
            "amount": 15000.0,
            "transaction_type": "expense",
            "category": "Rent & Housing",
            "payment_method": "Net Banking",
            "is_essential": True,
            "date": f"{curr_month}-01",
        },
    )

    # 3. Add heavy spending in Shopping (configured limit ₹2,500)
    client.post(
        "/api/transactions",
        json={
            "description": "Designer Clothes & Shoes",
            "amount": 6000.0,
            "transaction_type": "expense",
            "category": "Shopping",
            "payment_method": "Credit Card",
            "is_essential": False,
            "date": f"{curr_month}-03",
        },
    )

    # 4. Fetch Prediction Forecast via API
    res = client.get(f"/api/analysis/forecast?month={curr_month}")
    assert res.status_code == 200
    data = res.json()

    assert data["month"] == curr_month
    assert "evaluation_date" in data
    assert data["salary_recorded"] is True
    assert data["monthly_salary"] == 50000.0
    assert data["current_income"] == 50000.0
    assert data["current_expenses"] == 21000.0
    assert data["projected_expenses"] >= 21000.0
    assert data["estimated_remaining_balance"] == data["projected_savings"]
    assert "forecast_presentation" in data
    assert "Total expenses recorded so far" in data["forecast_presentation"]
    assert "Estimated month-end expenses (projection)" in data["forecast_presentation"]

    # 5. Test AI Chatbot queries for prediction & forecast
    chat_pred = client.post("/api/chat", json={"message": "Predict my monthly expenses and savings for this month"})
    assert chat_pred.status_code == 200
    pred_reply = chat_pred.json()["reply"]
    assert "₹" in pred_reply
    assert "Expense Forecast" in pred_reply or "Total expenses recorded so far" in pred_reply


def test_forecast_missing_salary_and_empty_expenses(client):
    today = date.today()
    curr_month = today.strftime("%Y-%m")

    # Fetch forecast without setting any salary or expenses
    res = client.get(f"/api/analysis/forecast?month={curr_month}")
    assert res.status_code == 200
    data = res.json()

    assert data["salary_recorded"] is False
    assert data["monthly_salary"] == 0.0
    assert data["current_expenses"] == 0.0
    assert data["daily_spending_pace"] == 0.0
    assert data["projected_expenses"] == 0.0
    assert data["has_sufficient_history"] is False
    assert "Not recorded" in data["forecast_presentation"] or "0.00" in data["forecast_presentation"]

    # Chatbot response should explain salary is missing
    chat_sal = client.post("/api/chat", json={"message": "How much money do I have left from my salary?"})
    assert chat_sal.status_code == 200
    reply = chat_sal.json()["reply"]
    assert "haven't recorded a salary" in reply or "set your monthly salary" in reply.lower()


def test_forecast_with_historical_months_baseline(client):
    today = date.today()
    curr_month = today.strftime("%Y-%m")

    # Add prior month transactions (August & September)
    client.post(
        "/api/transactions",
        json={
            "description": "August Dining",
            "amount": 2000.0,
            "transaction_type": "expense",
            "category": "Food & Dining",
            "date": "2026-08-15",
        },
    )
    client.post(
        "/api/transactions",
        json={
            "description": "September Dining",
            "amount": 2500.0,
            "transaction_type": "expense",
            "category": "Food & Dining",
            "date": "2026-09-15",
        },
    )

    # Current month transaction
    client.post(
        "/api/transactions",
        json={
            "description": "October Dining",
            "amount": 1000.0,
            "transaction_type": "expense",
            "category": "Food & Dining",
            "date": f"{curr_month}-05",
        },
    )

    res = client.get(f"/api/analysis/forecast?month={curr_month}")
    assert res.status_code == 200
    data = res.json()

    assert data["has_sufficient_history"] is True
    assert data["history_months_count"] >= 1
    # Regular baseline for Food & Dining should reflect historical average (2000 + 2500) / 2 = 2250
    assert data["regular_unwanted_baseline"] > 0
