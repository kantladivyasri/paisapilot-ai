import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Transaction
from app.agents.analyzer import calculate_summary, calculate_analysis

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_zero_income_safety(db_session):
    """Ensure zero income does not cause ZeroDivisionError and yields 0% savings rate."""
    txn = Transaction(
        description="Electricity Bill",
        amount=1200.0,
        transaction_type="expense",
        category="Electricity",
        is_essential=True,
        date="2026-10-01",
    )
    db_session.add(txn)
    db_session.commit()

    summary = calculate_summary(db_session)
    assert summary.total_income == 0.0
    assert summary.total_expenses == 1200.0
    assert summary.available_balance == -1200.0
    assert summary.savings_rate == 0.0
    assert len(summary.alerts) > 0


def test_standard_balance_and_savings_rate(db_session):
    """
    Test standard ₹30,000 income, ₹19,000 expense scenario.
    Balance must be ₹11,000, savings rate = 36.67%.
    """
    db_session.add(
        Transaction(
            description="Salary Credit",
            amount=30000.0,
            transaction_type="income",
            category="Salary",
            is_essential=False,
            date="2026-10-01",
        )
    )
    db_session.add(
        Transaction(
            description="House Rent",
            amount=19000.0,
            transaction_type="expense",
            category="Rent",
            is_essential=True,
            date="2026-10-02",
        )
    )
    db_session.commit()

    summary = calculate_summary(db_session)
    assert summary.total_income == 30000.0
    assert summary.total_expenses == 19000.0
    assert summary.available_balance == 11000.0
    assert summary.savings_rate == 36.67
    assert len(summary.top_categories) == 1
    assert summary.top_categories[0].category == "Rent"
    assert summary.top_categories[0].percentage == 100.0


def test_essential_vs_discretionary_breakdown(db_session):
    """Verifies proper split between essential and discretionary expenses."""
    db_session.add_all([
        Transaction(
            description="Salary",
            amount=50000.0,
            transaction_type="income",
            category="Salary",
            is_essential=False,
            date="2026-10-01",
        ),
        Transaction(
            description="Groceries",
            amount=6000.0,
            transaction_type="expense",
            category="Groceries",
            is_essential=True,
            date="2026-10-03",
        ),
        Transaction(
            description="Fine Dining",
            amount=4000.0,
            transaction_type="expense",
            category="Food",
            is_essential=False,
            date="2026-10-05",
        ),
    ])
    db_session.commit()

    analysis = calculate_analysis(db_session)
    assert analysis.essential_spending == 6000.0
    assert analysis.discretionary_spending == 4000.0
    assert analysis.essential_percentage == 60.0
    assert analysis.discretionary_percentage == 40.0
