import pytest
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


def test_category_management(client):
    # 1. Fetch initial categories (defaults seeded)
    res = client.get("/api/categories")
    assert res.status_code == 200
    cats = res.json()
    assert len(cats) >= 5

    # 2. Create custom category
    create_res = client.post(
        "/api/categories",
        json={
            "name": "Pet Care",
            "color": "#fbbf24",
            "icon": "Heart",
            "is_essential": True,
            "budget_limit": 2500.0,
        },
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["name"] == "Pet Care"
    cat_id = created["id"]

    # 3. Create transaction under "Pet Care"
    txn_res = client.post(
        "/api/transactions",
        json={
            "description": "Veterinary Checkup",
            "amount": 1200.0,
            "transaction_type": "expense",
            "category": "Pet Care",
            "payment_method": "UPI",
            "is_essential": True,
            "date": "2026-10-04",
        },
    )
    assert txn_res.status_code == 201

    # 4. Check that category spending reflects the transaction
    get_res = client.get("/api/categories?month=2026-10")
    assert get_res.status_code == 200
    all_cats = get_res.json()
    pet_cat = next(c for c in all_cats if c["name"] == "Pet Care")
    assert pet_cat["current_month_spent"] == 1200.0
    assert pet_cat["transaction_count"] == 1

    # 5. Update category name
    update_res = client.put(
        f"/api/categories/{cat_id}",
        json={"name": "Pets & Vets", "budget_limit": 3000.0},
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["name"] == "Pets & Vets"
    assert updated["budget_limit"] == 3000.0

    # Verify transaction was reassigned to new name
    txns = client.get("/api/transactions?category=Pets%20%26%20Vets").json()
    assert len(txns) == 1

    # 6. Delete category
    del_res = client.delete(f"/api/categories/{cat_id}")
    assert del_res.status_code == 200

    # Verify transaction was safely reassigned to Miscellaneous
    misc_txns = client.get("/api/transactions?category=Miscellaneous").json()
    assert len(misc_txns) == 1
    assert misc_txns[0]["description"] == "Veterinary Checkup"
