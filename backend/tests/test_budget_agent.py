from app.agents.budget_agent import generate_budget_plan


def test_balanced_budget_allocation():
    plan = generate_budget_plan(
        monthly_income=30000.0,
        essential_expenses=15000.0,
        savings_target=6000.0,
    )
    assert plan["is_balanced"] is True
    assert plan["essential_expenses"] == 15000.0
    assert plan["savings_target"] == 6000.0
    assert plan["discretionary_allowance"] == 9000.0  # 30,000 - 15,000 - 6,000
    assert plan["deficit_amount"] == 0.0
    assert plan["deficit_warning"] is None
    assert plan["recovery_plan"] is None


def test_budget_shortfall_recovery_plan():
    """
    If essential expenses exceed monthly income,
    the planner must NOT allocate impossible budgets and must return a shortfall recovery plan.
    """
    plan = generate_budget_plan(
        monthly_income=25000.0,
        essential_expenses=28000.0,  # ₹3,000 deficit!
        savings_target=5000.0,
    )
    assert plan["is_balanced"] is False
    assert plan["deficit_amount"] == 3000.0
    assert plan["discretionary_allowance"] == 0.0
    assert plan["savings_target"] == 0.0
    assert plan["deficit_warning"] is not None
    assert "exceed monthly income" in plan["deficit_warning"]
    assert plan["recovery_plan"] is not None
    assert len(plan["recovery_plan"]) >= 3


def test_savings_target_exceeding_surplus():
    """
    When user requests savings target larger than surplus,
    planner realistically caps savings to preserve cash flow.
    """
    plan = generate_budget_plan(
        monthly_income=30000.0,
        essential_expenses=20000.0,  # Surplus = 10,000
        savings_target=15000.0,      # Unrealistic!
    )
    assert plan["is_balanced"] is True
    assert plan["savings_target"] <= 10000.0
    assert plan["savings_target"] + plan["discretionary_allowance"] == 10000.0
