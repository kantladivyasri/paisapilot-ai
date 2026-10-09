import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.import_agent import TransactionImportAgent
from app.agents.langchain_tools import get_nidhi_langchain_tools
from app.database import Base
from app.models import Category, Transaction
from app.schemas import TransactionCreate

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def db():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        # Seed basic categories
        session.add(Category(name="Food", color="#f59e0b", icon="Utensils", is_essential=False, user_id="default_user"))
        session.add(Category(name="Electricity", color="#3b82f6", icon="Zap", is_essential=True, user_id="default_user"))
        session.add(Category(name="Salary", color="#10b981", icon="Briefcase", is_essential=False, user_id="default_user"))
        session.commit()
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_sms_parsing_and_categorization(db):
    sample_sms = (
        "Dear SBI User, your A/C 1234 is debited by Rs 450.00 on 08-Oct-26 by UPI to SWIGGY ref 23498234.\n"
        "HDFC Bank: Rs. 1,850.00 spent on Credit Card ending 4321 at RELIANCE FRESH on 07-10-2026.\n"
        "ICICI Bank Alert: INR 65,000.00 credited to Account XX5432 on 01-10-2026. Info: SALARY OCT 2026."
    )

    preview = TransactionImportAgent.preview_import(sample_sms, db, user_id="default_user")
    assert preview.total_detected == 3
    assert preview.duplicate_count == 0

    items = preview.parsed_transactions
    # Swiggy expense
    assert items[0].amount == 450.0
    assert items[0].transaction_type == "expense"
    assert "Food" in items[0].category or "Swiggy" in items[0].description
    assert items[0].date == "2026-10-08"

    # Reliance Fresh expense
    assert items[1].amount == 1850.0
    assert items[1].transaction_type == "expense"
    assert items[1].date == "2026-10-07"

    # Salary income
    assert items[2].amount == 65000.0
    assert items[2].transaction_type == "income"
    assert items[2].category == "Salary"
    assert items[2].date == "2026-10-01"


def test_natural_language_and_relative_dates(db):
    text = (
        "Paid Rs 1,200 to Bescom for electricity bill yesterday\n"
        "Sent ₹350 to Uber for cab ride today"
    )

    preview = TransactionImportAgent.preview_import(text, db, user_id="default_user")
    assert preview.total_detected == 2

    # Bescom should be categorized as Electricity / essential
    bescom = next(i for i in preview.parsed_transactions if i.amount == 1200.0)
    assert bescom.is_essential is True
    assert bescom.transaction_type == "expense"


def test_duplicate_detection(db):
    # Pre-populate an existing transaction in the database
    db.add(
        Transaction(
            user_id="default_user",
            description="Swiggy",
            amount=450.0,
            transaction_type="expense",
            category="Food",
            date="2026-10-08",
        )
    )
    db.commit()

    # Now parse an SMS with the exact same transaction
    sms = "Dear SBI User, your A/C 1234 is debited by Rs 450.00 on 08-Oct-26 by UPI to SWIGGY ref 23498234."
    preview = TransactionImportAgent.preview_import(sms, db, user_id="default_user")
    assert preview.total_detected == 1
    assert preview.duplicate_count == 1
    assert preview.parsed_transactions[0].is_duplicate is True


def test_commit_transactions(db):
    txns = [
        TransactionCreate(
            description="Zomato Order",
            amount=320.0,
            transaction_type="expense",
            category="Food",
            is_essential=False,
            date="2026-10-05",
        ),
        TransactionCreate(
            description="Client Consulting",
            amount=15000.0,
            transaction_type="income",
            category="Freelance",
            is_essential=False,
            date="2026-10-06",
        ),
    ]

    res = TransactionImportAgent.commit_transactions(txns, db, user_id="default_user")
    assert res.imported_count == 2
    assert res.skipped_duplicates == 0
    assert res.total_expenses == 320.0
    assert res.total_income == 15000.0

    # Verify stored in SQLite
    count = db.query(Transaction).filter(Transaction.user_id == "default_user").count()
    assert count == 2


def test_langchain_import_tool(db):
    tools = get_nidhi_langchain_tools(db, user_id="default_user")
    import_tool = next((t for t in tools if t.name == "import_transactions_agent_tool"), None)
    assert import_tool is not None

    sms = "Paid Rs 550 to Swiggy on 09-10-2026 via UPI"
    result_preview = import_tool.invoke({"raw_text_or_sms_batch": sms, "commit_immediately": False})
    assert "Import Agent Extracted 1 Transaction(s)" in result_preview
    assert "₹550.00" in result_preview
    assert "Preview mode" in result_preview

    # Test commit immediately
    result_commit = import_tool.invoke({"raw_text_or_sms_batch": sms, "commit_immediately": True})
    assert "Successfully saved 1 new transaction(s)" in result_commit

    # Transaction is in DB
    saved = db.query(Transaction).filter(Transaction.amount == 550.0).first()
    assert saved is not None
