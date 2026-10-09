import pytest
from datetime import datetime, date
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


def test_period_reports_monthly_and_comparison(client):
    today = date.today()
    curr_month_str = today.strftime("%Y-%m")
    
    # Set salary for this month
    client.post(
        "/api/salary",
        json={"month": curr_month_str, "amount": 60000.0, "notes": "Monthly Salary"},
    )

    # Add transactions for current month
    client.post(
        "/api/transactions",
        json={
            "description": "Groceries",
            "amount": 4000.0,
            "transaction_type": "expense",
            "category": "Food & Dining",
            "payment_method": "UPI",
            "is_essential": True,
            "date": f"{curr_month_str}-05",
        },
    )
    client.post(
        "/api/transactions",
        json={
            "description": "Internet Bill",
            "amount": 1000.0,
            "transaction_type": "expense",
            "category": "Bills & Utilities",
            "payment_method": "Net Banking",
            "is_essential": True,
            "date": f"{curr_month_str}-10",
        },
    )
    client.post(
        "/api/transactions",
        json={
            "description": "Freelance Gig",
            "amount": 5000.0,
            "transaction_type": "income",
            "category": "Salary / Income",
            "payment_method": "Bank Transfer",
            "is_essential": False,
            "date": f"{curr_month_str}-12",
        },
    )

    # 1. Fetch Monthly Report
    res = client.get(f"/api/reports/period?period_type=monthly&target_date={curr_month_str}-01")
    assert res.status_code == 200
    data = res.json()
    assert data["period_type"] == "monthly"
    
    current_p = data["current_period"]
    # Total expenses = 4000 + 1000 = 5000
    assert current_p["total_expenses"] == 5000.0
    # Income = 60000 (salary) + 5000 (extra) = 65000
    assert current_p["total_income"] == 65000.0
    assert current_p["remaining_balance"] == 60000.0
    assert current_p["savings_rate"] == 92.31
    assert current_p["transaction_count"] == 3
    
    # Check category breakdowns
    cat_breakdown = current_p["category_breakdown"]
    food_cat = next((c for c in cat_breakdown if c["category"] == "Food & Dining"), None)
    assert food_cat is not None
    assert food_cat["amount"] == 4000.0

    # 2. Daily Report
    daily_res = client.get(f"/api/reports/period?period_type=daily&target_date={curr_month_str}-05")
    assert daily_res.status_code == 200
    daily_data = daily_res.json()
    assert daily_data["period_type"] == "daily"
    assert daily_data["current_period"]["total_expenses"] == 4000.0

    # 3. Weekly Report
    weekly_res = client.get(f"/api/reports/period?period_type=weekly&target_date={curr_month_str}-05")
    assert weekly_res.status_code == 200
    weekly_data = weekly_res.json()
    assert weekly_data["period_type"] == "weekly"
    assert weekly_data["current_period"]["total_expenses"] >= 4000.0

    # 4. Yearly Report
    year_str = str(today.year)
    yearly_res = client.get(f"/api/reports/period?period_type=yearly&target_date={year_str}-01-01")
    assert yearly_res.status_code == 200
    yearly_data = yearly_res.json()
    assert yearly_data["period_type"] == "yearly"
    assert yearly_data["current_period"]["total_expenses"] >= 5000.0

    # 5. Custom Date Range Report
    custom_res = client.get(f"/api/reports/period?period_type=custom&start_date={curr_month_str}-01&end_date={curr_month_str}-08")
    assert custom_res.status_code == 200
    custom_data = custom_res.json()
    assert custom_data["period_type"] == "custom"
    # only 4000 was on 05, 1000 was on 10
    assert custom_data["current_period"]["total_expenses"] == 4000.0
