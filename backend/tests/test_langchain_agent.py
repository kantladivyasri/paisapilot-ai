import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Category, SalaryRecord, SavingsGoal, Transaction
from app.agents.langchain_tools import get_nidhi_langchain_tools
from app.agents.langchain_agent import run_nidhi_langchain_agent
from app.agents.orchestrator import route_chat_query


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    current_month = datetime.now().strftime("%Y-%m")

    # Seed test salary
    salary = SalaryRecord(user_id="default_user", month=current_month, amount=30000.0)
    db.add(salary)

    # Seed test categories
    c1 = Category(user_id="default_user", name="Food", budget_limit=6000.0)
    c2 = Category(user_id="default_user", name="Shopping", budget_limit=3000.0)
    c3 = Category(user_id="default_user", name="Rent", budget_limit=8000.0)
    db.add_all([c1, c2, c3])

    # Seed test transactions
    t1 = Transaction(
        user_id="default_user",
        date=f"{current_month}-02",
        description="House Rent",
        amount=7000.0,
        transaction_type="expense",
        category="Rent",
        is_essential=True,
    )
    t2 = Transaction(
        user_id="default_user",
        date=f"{current_month}-05",
        description="Grocery Store",
        amount=2500.0,
        transaction_type="expense",
        category="Food",
        is_essential=True,
    )
    t3 = Transaction(
        user_id="default_user",
        date=f"{current_month}-08",
        description="Zara Shopping",
        amount=3500.0,
        transaction_type="expense",
        category="Shopping",
        is_essential=False,
    )
    db.add_all([t1, t2, t3])

    # Seed goal
    g = SavingsGoal(
        user_id="default_user",
        name="Emergency Fund",
        target_amount=50000.0,
        current_amount=15000.0,
        target_date="2026-12-31",
    )
    db.add(g)

    db.commit()
    yield db
    db.close()


def test_langchain_tools_suite(test_db):
    """Verifies that all 8 LangChain tools execute with accurate database data."""
    tools = get_nidhi_langchain_tools(test_db, user_id="default_user")
    assert len(tools) == 8

    tool_map = {t.name: t for t in tools}
    expected_names = [
        "get_salary_and_balance_tool",
        "query_category_spending_tool",
        "get_period_spending_report_tool",
        "predict_month_end_forecast_tool",
        "check_affordability_simulation_tool",
        "get_budget_and_savings_goals_tool",
        "list_recent_transactions_tool",
        "import_transactions_agent_tool",
    ]
    for name in expected_names:
        assert name in tool_map

    # 1. Salary and balance
    sal_res = tool_map["get_salary_and_balance_tool"].invoke({})
    assert "₹30,000.00" in sal_res
    assert "₹13,000.00" in sal_res  # total expenses 7000+2500+3500
    assert "₹17,000.00" in sal_res  # remaining balance

    # 2. Category spending
    food_res = tool_map["query_category_spending_tool"].invoke({"category_name": "Food"})
    assert "₹2,500.00" in food_res
    assert "Within Limit" in food_res

    shop_res = tool_map["query_category_spending_tool"].invoke({"category_name": "Shopping"})
    assert "₹3,500.00" in shop_res
    assert "Over Budget" in shop_res  # limit is 3000

    # 3. Period spending report
    rep_res = tool_map["get_period_spending_report_tool"].invoke({"period_type": "monthly"})
    assert "₹13,000.00" in rep_res

    # 4. Forecast projection
    fc_res = tool_map["predict_month_end_forecast_tool"].invoke({})
    assert "Month-End Projection" in fc_res
    assert "Estimated Month-End Outflow" in fc_res

    # 5. Affordability simulation
    aff_res = tool_map["check_affordability_simulation_tool"].invoke({"item_name": "Phone", "item_cost": 5000})
    assert "Affordability Simulation" in aff_res
    assert "YES ✅" in aff_res  # remaining balance 17000 covers 5000

    aff_expensive = tool_map["check_affordability_simulation_tool"].invoke({"item_name": "Car Downpayment", "item_cost": 25000})
    assert "NO ❌" in aff_expensive  # 25000 > 17000

    # 6. Budget & goals
    bg_res = tool_map["get_budget_and_savings_goals_tool"].invoke({})
    assert "Emergency Fund" in bg_res
    assert "₹15,000.00" in bg_res

    # 7. Recent transactions
    tx_res = tool_map["list_recent_transactions_tool"].invoke({"limit": 5})
    assert "House Rent" in tx_res
    assert "Zara Shopping" in tx_res


@pytest.mark.asyncio
async def test_langchain_agent_fallback_and_orchestration(test_db):
    """Verifies that orchestrator handles user queries and falls back safely if no external LLM key is set."""
    # When no API key is provided, orchestrator should return deterministic response with structured data
    response = await route_chat_query(
        query="How much money do I have left from my salary?",
        db=test_db,
        user_id="default_user",
    )
    assert response.reply is not None
    assert "₹17,000.00" in response.reply
    assert response.intent in ["remaining_salary", "salary_balance"]
    assert response.engine in ["langchain", "groq", "gemini", "deterministic"]
