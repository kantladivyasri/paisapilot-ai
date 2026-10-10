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


def test_user_registration_and_login_flow(client):
    # 1. Register a new user
    reg_payload = {
        "username": "arjun_sharma",
        "email": "arjun@example.com",
        "password": "Password123!",
        "name": "Arjun Sharma",
        "currency": "INR",
    }
    reg_resp = client.post("/api/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text
    data = reg_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "arjun_sharma"
    assert data["user"]["email"] == "arjun@example.com"
    assert data["user"]["name"] == "Arjun Sharma"
    token = data["access_token"]

    # 2. Verify duplicate username rejection
    dup_user_resp = client.post("/api/auth/register", json={
        "username": "arjun_sharma",
        "email": "different@example.com",
        "password": "Password123!",
    })
    assert dup_user_resp.status_code == 400
    assert "already taken" in dup_user_resp.json()["detail"]

    # 3. Verify duplicate email rejection
    dup_email_resp = client.post("/api/auth/register", json={
        "username": "another_user",
        "email": "arjun@example.com",
        "password": "Password123!",
    })
    assert dup_email_resp.status_code == 400
    assert "already registered" in dup_email_resp.json()["detail"]

    # 4. Login with username
    login_resp = client.post("/api/auth/login", json={
        "username_or_email": "arjun_sharma",
        "password": "Password123!",
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == "arjun@example.com"

    # 5. Login with email
    login_email_resp = client.post("/api/auth/login", json={
        "username_or_email": "arjun@example.com",
        "password": "Password123!",
    })
    assert login_email_resp.status_code == 200

    # 6. Login with incorrect password
    bad_login_resp = client.post("/api/auth/login", json={
        "username_or_email": "arjun_sharma",
        "password": "WrongPassword!",
    })
    assert bad_login_resp.status_code == 401

    # 7. Check /api/auth/me with valid Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "arjun_sharma"

    # 8. Check /api/auth/me without token -> 401
    me_no_token = client.get("/api/auth/me")
    assert me_no_token.status_code == 401

    # 9. Check /api/auth/me with tampered token -> 401
    me_bad_token = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token_xyz"})
    assert me_bad_token.status_code == 401


def test_multi_tenant_data_isolation(client):
    # User 1
    u1_resp = client.post("/api/auth/register", json={
        "username": "user_one",
        "email": "one@example.com",
        "password": "PasswordOne123!",
        "name": "User One",
    })
    assert u1_resp.status_code == 201
    u1_token = u1_resp.json()["access_token"]
    u1_headers = {"Authorization": f"Bearer {u1_token}"}

    # User 2
    u2_resp = client.post("/api/auth/register", json={
        "username": "user_two",
        "email": "two@example.com",
        "password": "PasswordTwo123!",
        "name": "User Two",
    })
    assert u2_resp.status_code == 201
    u2_token = u2_resp.json()["access_token"]
    u2_headers = {"Authorization": f"Bearer {u2_token}"}

    # Check default categories were provisioned for both users
    u1_cats = client.get("/api/categories", headers=u1_headers).json()
    u2_cats = client.get("/api/categories", headers=u2_headers).json()
    assert len(u1_cats) >= 10
    assert len(u2_cats) >= 10

    # User 1 sets salary 50,000
    client.post("/api/salary", json={"month": "2026-10", "amount": 50000.0, "notes": "User 1 Job"}, headers=u1_headers)

    # User 2 sets salary 80,000
    client.post("/api/salary", json={"month": "2026-10", "amount": 80000.0, "notes": "User 2 Tech"}, headers=u2_headers)

    # User 1 creates an expense
    client.post("/api/transactions", json={
        "description": "User 1 Rent",
        "amount": 15000.0,
        "transaction_type": "expense",
        "category": "Rent & Housing",
        "payment_method": "UPI",
        "is_essential": True,
        "date": "2026-10-02",
    }, headers=u1_headers)

    # User 2 creates an expense
    client.post("/api/transactions", json={
        "description": "User 2 Laptop",
        "amount": 45000.0,
        "transaction_type": "expense",
        "category": "Shopping",
        "payment_method": "Credit Card",
        "is_essential": False,
        "date": "2026-10-05",
    }, headers=u2_headers)

    # Verify User 1 sees ONLY their salary and transactions
    u1_salary = client.get("/api/salary?month=2026-10", headers=u1_headers).json()
    assert u1_salary["amount"] == 50000.0
    assert u1_salary["total_expenses"] == 15000.0
    assert u1_salary["remaining_balance"] == 35000.0

    u1_txns = client.get("/api/transactions", headers=u1_headers).json()
    assert len(u1_txns) == 1
    assert u1_txns[0]["description"] == "User 1 Rent"

    # Verify User 2 sees ONLY their salary and transactions
    u2_salary = client.get("/api/salary?month=2026-10", headers=u2_headers).json()
    assert u2_salary["amount"] == 80000.0
    assert u2_salary["total_expenses"] == 45000.0
    assert u2_salary["remaining_balance"] == 35000.0

    u2_txns = client.get("/api/transactions", headers=u2_headers).json()
    assert len(u2_txns) == 1
    assert u2_txns[0]["description"] == "User 2 Laptop"


def test_user_profile_update(client):
    # Register user
    reg = client.post("/api/auth/register", json={
        "username": "profile_user",
        "email": "orig@example.com",
        "password": "InitialPassword123",
        "name": "Original Name",
        "currency": "INR",
    }).json()
    token = reg["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update Name and Currency
    upd_resp = client.put("/api/auth/profile", json={
        "name": "Updated Name",
        "currency": "USD",
    }, headers=headers)
    assert upd_resp.status_code == 200
    data = upd_resp.json()
    assert data["name"] == "Updated Name"
    assert data["currency"] == "USD"
    assert data["email"] == "orig@example.com"

    # 2. Update Email
    email_resp = client.put("/api/auth/profile", json={
        "email": "newemail@example.com",
    }, headers=headers)
    assert email_resp.status_code == 200
    assert email_resp.json()["email"] == "newemail@example.com"

    # 3. Change password with wrong current password -> 400
    bad_pwd = client.put("/api/auth/profile", json={
        "current_password": "WrongPassword",
        "new_password": "NewSecretPassword123",
    }, headers=headers)
    assert bad_pwd.status_code == 400

    # 4. Change password with correct current password -> 200
    ok_pwd = client.put("/api/auth/profile", json={
        "current_password": "InitialPassword123",
        "new_password": "NewSecretPassword123",
    }, headers=headers)
    assert ok_pwd.status_code == 200

    # 5. Verify can now login with new password
    login_new = client.post("/api/auth/login", json={
        "username_or_email": "profile_user",
        "password": "NewSecretPassword123",
    })
    assert login_new.status_code == 200

