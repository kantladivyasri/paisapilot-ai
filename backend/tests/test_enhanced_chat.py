import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from unittest.mock import patch

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


def test_enhanced_chat_queries_and_history(client):
    today = date.today()
    curr_month = today.strftime("%Y-%m")
    
    # 1. Setup financial context: Salary 50,000
    client.post(
        "/api/salary",
        json={"month": curr_month, "amount": 50000.0, "notes": "Monthly Salary"},
    )

    # Add expenses
    client.post(
        "/api/transactions",
        json={
            "description": "Supermarket Grocery",
            "amount": 6500.0,
            "transaction_type": "expense",
            "category": "Food & Dining",
            "payment_method": "UPI",
            "is_essential": True,
            "date": today.isoformat(),
        },
    )
    client.post(
        "/api/transactions",
        json={
            "description": "Zomato Delivery",
            "amount": 850.0,
            "transaction_type": "expense",
            "category": "Food & Dining",
            "payment_method": "UPI",
            "is_essential": False,
            "date": today.isoformat(),
        },
    )
    client.post(
        "/api/transactions",
        json={
            "description": "Zara Clothing",
            "amount": 4200.0,
            "transaction_type": "expense",
            "category": "Shopping",
            "payment_method": "Credit Card",
            "is_essential": False,
            "date": today.isoformat(),
        },
    )
    # September transaction
    client.post(
        "/api/transactions",
        json={
            "description": "September Dinner",
            "amount": 3200.0,
            "transaction_type": "expense",
            "category": "Food & Dining",
            "payment_method": "Credit Card",
            "is_essential": False,
            "date": f"{today.year}-09-15",
        },
    )

    # 2. Query: "How much money did I spend this week?"
    res = client.post("/api/chat", json={"message": "How much money did I spend this week?"})
    assert res.status_code == 200
    answer = res.json()["reply"]
    assert "week" in answer.lower() or "₹" in answer
    # Total today alone is 6500 + 850 + 4200 = 11550
    assert "11,550" in answer or "11550" in answer

    # 3. Query: "What is my biggest expense category this month?"
    res = client.post("/api/chat", json={"message": "What is my biggest expense category this month?"})
    assert res.status_code == 200
    answer = res.json()["reply"]
    assert "Food & Dining" in answer or "food" in answer.lower()

    # 4. Query: "How much money do I have left from my salary?"
    res = client.post("/api/chat", json={"message": "How much money do I have left from my salary?"})
    assert res.status_code == 200
    answer = res.json()["reply"]
    # 50,000 - 11,550 = 38,450
    assert "38,450" in answer or "38450" in answer

    # 5. Query: "How much did I spend on food in September?"
    res = client.post("/api/chat", json={"message": "How much did I spend on food in September?"})
    assert res.status_code == 200
    answer = res.json()["reply"]
    assert "3,200" in answer or "3200" in answer

    # 6. Query: "Show my total expenses for this year."
    res = client.post("/api/chat", json={"message": "Show my total expenses for this year."})
    assert res.status_code == 200
    answer = res.json()["reply"]
    # 11,550 + 3,200 = 14,750
    assert "14,750" in answer or "14750" in answer

    # 7. Query: "Predict my monthly expenses and savings"
    res = client.post("/api/chat", json={"message": "Predict my monthly expenses and savings"})
    assert res.status_code == 200
    answer = res.json()["reply"]
    assert "Projected" in answer or "Run-Rate" in answer or "₹" in answer
    assert "Trajectory" in answer or "Forecast" in answer

    # 8. Query: "Am I spending too much on unwanted things than regular?"
    res = client.post("/api/chat", json={"message": "Am I spending too much on unwanted things than regular?"})
    assert res.status_code == 200
    answer = res.json()["reply"]
    assert "Unwanted" in answer or "Discretionary" in answer or "Spending" in answer

    # 9. Check Chat History persistence
    hist_res = client.get("/api/chat/history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 14

    # 8. Clear Chat History
    del_res = client.delete("/api/chat/history")
    assert del_res.status_code == 200
    assert "cleared" in del_res.json()["message"].lower()

    hist_after = client.get("/api/chat/history").json()
    assert len(hist_after) == 0
