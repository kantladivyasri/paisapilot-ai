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


def test_salary_crud_and_live_balance(client):
    # 1. Initially no salary recorded
    res = client.get("/api/salary?month=2026-10")
    assert res.status_code == 200
    data = res.json()
    assert data["amount"] == 0.0
    assert data["total_expenses"] == 0.0

    # 2. Set salary for 2026-10
    create_res = client.post(
        "/api/salary",
        json={"month": "2026-10", "amount": 45000.0, "notes": "Base Software Engineer Salary"},
    )
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["amount"] == 45000.0
    assert created["month"] == "2026-10"
    assert created["remaining_balance"] == 45000.0
    assert created["savings_rate"] == 100.0

    # 3. Add an expense of ₹15,000 in 2026-10
    txn_res = client.post(
        "/api/transactions",
        json={
            "description": "Apartment Rent",
            "amount": 15000.0,
            "transaction_type": "expense",
            "category": "Rent & Housing",
            "payment_method": "UPI",
            "is_essential": True,
            "date": "2026-10-02",
        },
    )
    assert txn_res.status_code == 201

    # 4. Fetch salary again - remaining balance should be 45,000 - 15,000 = 30,000
    check_res = client.get("/api/salary?month=2026-10")
    assert check_res.status_code == 200
    checked = check_res.json()
    assert checked["current_month_salary"] == 45000.0
    assert checked["total_expenses"] == 15000.0
    assert checked["remaining_balance"] == 30000.0
    assert checked["savings_rate"] == 66.67

    # 5. Update salary to 50,000
    update_res = client.post(
        "/api/salary",
        json={"month": "2026-10", "amount": 50000.0, "notes": "Updated with bonus"},
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["amount"] == 50000.0
    assert updated["remaining_balance"] == 35000.0  # 50,000 - 15,000
