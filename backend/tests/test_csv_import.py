import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Transaction
from app.services.csv_import import parse_and_import_csv

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_standard_csv_import(db):
    csv_data = b"""Date,Description,Amount,Type
2026-10-01,Tech Salary,30000,income
2026-10-02,House Rent,7000,expense
2026-10-03,Blinkit Groceries,1200,expense
"""
    res = parse_and_import_csv(csv_data, "test.csv", db)
    assert res.imported_count == 3
    assert res.error_count == 0
    assert db.query(Transaction).count() == 3

    rent_txn = db.query(Transaction).filter(Transaction.description == "House Rent").first()
    assert rent_txn is not None
    assert rent_txn.category == "Rent"
    assert rent_txn.is_essential is True


def test_csv_with_debit_credit_columns(db):
    csv_data = b"""date,narration,debit,credit
01/10/2026,Salary Employer,,45000
02/10/2026,Swiggy Lunch,350,
"""
    res = parse_and_import_csv(csv_data, "bank_stmt.csv", db)
    assert res.imported_count == 2
    assert res.error_count == 0

    salary = db.query(Transaction).filter(Transaction.description.contains("Salary")).first()
    assert salary.transaction_type == "income"
    assert salary.amount == 45000.0

    swiggy = db.query(Transaction).filter(Transaction.description.contains("Swiggy")).first()
    assert swiggy.transaction_type == "expense"
    assert swiggy.amount == 350.0


def test_csv_duplicate_warning(db):
    # Pre-seed one transaction
    db.add(
        Transaction(
            description="Apollo Pharmacy",
            amount=500.0,
            transaction_type="expense",
            category="Healthcare",
            is_essential=True,
            date="2026-10-05",
        )
    )
    db.commit()

    csv_data = b"""date,description,amount,kind
2026-10-05,Apollo Pharmacy,500,expense
2026-10-06,BookMyShow Tickets,400,expense
"""
    res = parse_and_import_csv(csv_data, "medical.csv", db)
    # The duplicate is imported but with a warning!
    assert res.imported_count == 2
    assert res.duplicate_warning_count == 1
    assert "duplicate" in res.warnings[0].warning.lower()
