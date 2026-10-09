import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
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


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["currency"] == "INR (₹)"


def test_create_and_get_transaction(client):
    # Test creation
    payload = {
        "description": "Zomato Order",
        "amount": 450.50,
        "transaction_type": "expense",
        "category": "Food",
        "is_essential": False,
        "date": "2026-10-05",
        "notes": "Dinner with friends",
    }
    create_res = client.post("/api/transactions", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["id"] is not None
    assert created_data["amount"] == 450.50
    assert created_data["category"] == "Food"

    # Test listing
    list_res = client.get("/api/transactions")
    assert list_res.status_code == 200
    txns = list_res.json()
    assert len(txns) == 1
    assert txns[0]["description"] == "Zomato Order"


def test_auto_categorization_and_essential_flag(client):
    """If user leaves category blank or default, auto-categorizer must set it correctly."""
    payload = {
        "description": "Bescom Monthly Electricity",
        "amount": 1200.0,
        "transaction_type": "expense",
        "category": "Uncategorized",
        "is_essential": False,
        "date": "2026-10-06",
    }
    res = client.post("/api/transactions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["category"] == "Electricity"
    assert data["is_essential"] is True


def test_update_and_delete_transaction(client):
    create_res = client.post(
        "/api/transactions",
        json={
            "description": "Test Item",
            "amount": 100.0,
            "transaction_type": "expense",
            "category": "Shopping",
            "date": "2026-10-07",
        },
    )
    txn_id = create_res.json()["id"]

    # Update
    update_res = client.put(f"/api/transactions/{txn_id}", json={"amount": 150.0})
    assert update_res.status_code == 200
    assert update_res.json()["amount"] == 150.0

    # Delete
    del_res = client.delete(f"/api/transactions/{txn_id}")
    assert del_res.status_code == 200

    # Check gone
    list_res = client.get("/api/transactions")
    assert len(list_res.json()) == 0
