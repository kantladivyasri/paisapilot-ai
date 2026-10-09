import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.orchestrator import classify_intent, route_chat_query
from app.database import Base
from app.models import Transaction

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


def test_intent_classification():
    assert classify_intent("Where am I spending the most?") == "top_spending"
    assert classify_intent("Can I afford an additional ₹2,000 expense?") == "simulate_purchase"
    assert classify_intent("How can I save ₹1,000 next month?") == "save_money"
    assert classify_intent("How much money do I have left?") == "balance_query"
    assert classify_intent("Why am I exceeding my budget?") == "budget_status"


from unittest.mock import patch

@pytest.mark.asyncio
async def test_affordability_simulation(db):
    # Setup income ₹30,000 and expenses ₹19,000 -> balance ₹11,000
    db.add(
        Transaction(
            description="Salary",
            amount=30000.0,
            transaction_type="income",
            category="Salary",
            date="2026-10-01",
        )
    )
    db.add(
        Transaction(
            description="Rent",
            amount=19000.0,
            transaction_type="expense",
            category="Rent",
            date="2026-10-02",
        )
    )
    db.commit()

    with patch("app.agents.orchestrator.get_groq_api_key", return_value=None), \
         patch("app.agents.orchestrator.get_gemini_api_key", return_value=None):
        # Query 1: affordable ₹2,000
        res1 = await route_chat_query("Can I afford an additional ₹2,000 expense?", db)
        assert "Yes, you can afford" in res1.reply
        assert "₹2,000.00" in res1.reply
        assert "₹11,000.00" in res1.reply  # refers to exact current balance!

        # Query 2: unaffordable ₹15,000
        res2 = await route_chat_query("Can I afford an additional ₹15,000 expense?", db)
        assert any(term in res2.reply.lower() for term in ["cannot afford", "caution", "exceeds", "deficit", "shortfall"])
        assert "4,000" in res2.reply or "15,000" in res2.reply
