import pytest
from datetime import date
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

    # 3. Add heavy unwanted/discretionary spending in Shopping & Entertainment
    # Regular baseline for Shopping is ~₹2,500. Spending ₹6,000 in early days will easily trigger an overspending warning!
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
    client.post(
        "/api/transactions",
        json={
            "description": "Weekend Luxury Club & Drinks",
            "amount": 4000.0,
            "transaction_type": "expense",
            "category": "Entertainment",
            "payment_method": "UPI",
            "is_essential": False,
            "date": f"{curr_month}-04",
        },
    )

    # 4. Fetch Prediction Forecast via API
    res = client.get(f"/api/analysis/forecast?month={curr_month}")
    assert res.status_code == 200
    data = res.json()

    assert data["month"] == curr_month
    assert data["current_income"] == 50000.0
    # Total expenses so far = 15000 + 6000 + 4000 = 25000
    assert data["current_expenses"] == 25000.0
    # Projected expenses must be at least current expenses
    assert data["projected_expenses"] >= 25000.0

    # Must detect overspending on unwanted things!
    assert data["is_overspending_on_unwanted"] is True
    assert len(data["unwanted_spending_alerts"]) >= 1

    # Check alert details for Shopping or Entertainment
    shop_alert = next((a for a in data["unwanted_spending_alerts"] if a["category"] == "Shopping"), None)
    assert shop_alert is not None
    assert shop_alert["current_spent"] == 6000.0
    assert shop_alert["excess_amount"] > 0
    assert shop_alert["severity"] in ["warning", "critical"]
    assert "cut down" in shop_alert["recommendation"].lower() or "save" in shop_alert["recommendation"].lower()

    # 5. Test AI Chatbot queries for prediction & unwanted warnings
    # Query A: "Predict my monthly expenses"
    chat_pred = client.post("/api/chat", json={"message": "Predict my monthly expenses and savings for this month"})
    assert chat_pred.status_code == 200
    pred_reply = chat_pred.json()["reply"]
    assert "₹" in pred_reply
    assert any(term in pred_reply.lower() for term in ["projected", "forecast", "savings", "pace", "expenses"])

    # Query B: "Am I spending too much on unwanted things than regular?"
    chat_warn = client.post("/api/chat", json={"message": "Am I spending too much on unwanted things than regular?"})
    assert chat_warn.status_code == 200
    warn_reply = chat_warn.json()["reply"]
    assert any(term in warn_reply.lower() for term in ["shopping", "unwanted", "alert", "warning", "caution", "discretionary", "excess"])
