import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models import Category, BudgetSetting, SalaryRecord, Transaction
from app.schemas import BudgetCreate, BudgetResponse


def generate_budget_plan(
    monthly_income: float,
    essential_expenses: float,
    savings_target: float,
    emergency_fund_target: float = 0.0,
    category_limits: Optional[Dict[str, float]] = None,
    month: Optional[str] = None,
    db: Optional[Session] = None,
    user_id: str = "default_user",
) -> Dict[str, Any]:
    """
    Deterministically calculates a balanced monthly budget tailored to user circumstances.
    Suggests allocations for Needs, Wants, Savings, and Emergency Fund.
    Ensures mathematical feasibility and generates a shortfall recovery plan if essentials exceed income.
    """
    current_month = month or datetime.now().strftime("%Y-%m")

    # If monthly income is 0 or not provided, check recorded salary in database
    if monthly_income <= 0 and db is not None:
        sal = db.query(SalaryRecord).filter(
            SalaryRecord.user_id == user_id, SalaryRecord.month == current_month
        ).first()
        if sal and sal.amount > 0:
            monthly_income = sal.amount

    monthly_income = round(max(0.0, monthly_income), 2)
    essential_expenses = round(max(0.0, essential_expenses), 2)
    savings_target = round(max(0.0, savings_target), 2)
    emergency_fund_target = round(max(0.0, emergency_fund_target), 2)

    # Check for deficit
    if essential_expenses > monthly_income and monthly_income > 0:
        deficit = round(essential_expenses - monthly_income, 2)
        deficit_warning = (
            f"Essential expenses (₹{essential_expenses:,.2f}) exceed monthly income/salary (₹{monthly_income:,.2f}) "
            f"by ₹{deficit:,.2f}. A balanced surplus budget cannot be formed without restructuring."
        )
        recovery_plan = [
            "Phase 1: Freeze all non-essential and discretionary lifestyle spending immediately.",
            f"Phase 2: Review essential bills—negotiate rent/maintenance or trim utilities to bridge the ₹{deficit:,.2f} deficit.",
            "Phase 3: Prioritize mandatory obligations (housing, food, medicine) while seeking bridge income or freelance work.",
            "Phase 4: Temporarily pause long-term savings goals until essential obligations stay below 80% of net income.",
        ]
        return {
            "month": current_month,
            "monthly_income": monthly_income,
            "essential_expenses": essential_expenses,
            "savings_target": 0.0,
            "emergency_fund_target": 0.0,
            "discretionary_allowance": 0.0,
            "unallocated_balance": 0.0,
            "is_balanced": False,
            "deficit_amount": deficit,
            "deficit_warning": deficit_warning,
            "recovery_plan": recovery_plan,
            "category_limits": category_limits or {},
        }

    # Available surplus after covering essentials
    surplus = round(max(0.0, monthly_income - essential_expenses), 2)

    total_reserve_target = savings_target + emergency_fund_target

    if total_reserve_target > surplus:
        # Cap reserves proportionally to available surplus
        if emergency_fund_target > 0:
            proposed_savings = round(surplus * 0.50, 2)
            proposed_emergency = round(surplus * 0.20, 2)
            discretionary_allowance = round(surplus - (proposed_savings + proposed_emergency), 2)
        else:
            proposed_savings = round(surplus * 0.70, 2)
            proposed_emergency = 0.0
            discretionary_allowance = round(surplus - proposed_savings, 2)
        unallocated_balance = 0.0
    else:
        proposed_savings = savings_target
        proposed_emergency = emergency_fund_target
        discretionary_allowance = round(surplus - total_reserve_target, 2)
        unallocated_balance = round(
            monthly_income - (essential_expenses + proposed_savings + proposed_emergency + discretionary_allowance), 2
        )

    # Generate or pull category limits
    if not category_limits and db is not None:
        db_cats = db.query(Category).filter(Category.user_id == user_id).all()
        category_limits = {c.name: c.budget_limit for c in db_cats if c.budget_limit > 0}

    if not category_limits:
        category_limits = {}
        if essential_expenses > 0:
            category_limits["Rent & Housing"] = round(essential_expenses * 0.50, 2)
            category_limits["Groceries"] = round(essential_expenses * 0.25, 2)
            category_limits["Bills & Utilities"] = round(essential_expenses * 0.12, 2)
            category_limits["Transportation"] = round(essential_expenses * 0.13, 2)
        if discretionary_allowance > 0:
            category_limits["Food & Dining"] = round(discretionary_allowance * 0.40, 2)
            category_limits["Shopping"] = round(discretionary_allowance * 0.35, 2)
            category_limits["Entertainment"] = round(discretionary_allowance * 0.25, 2)

    return {
        "month": current_month,
        "monthly_income": monthly_income,
        "essential_expenses": essential_expenses,
        "savings_target": proposed_savings,
        "emergency_fund_target": proposed_emergency,
        "discretionary_allowance": discretionary_allowance,
        "unallocated_balance": unallocated_balance,
        "is_balanced": True,
        "deficit_amount": 0.0,
        "deficit_warning": None,
        "recovery_plan": None,
        "category_limits": category_limits,
    }


def save_or_update_budget(db: Session, budget_data: BudgetCreate, user_id: str = "default_user") -> BudgetResponse:
    """Saves or updates budget settings in the database."""
    category_limits_json = json.dumps(budget_data.category_limits or {})

    existing = (
        db.query(BudgetSetting)
        .filter(BudgetSetting.user_id == user_id, BudgetSetting.month == budget_data.month)
        .first()
    )
    if existing:
        existing.monthly_income = budget_data.monthly_income
        existing.essential_expenses = budget_data.essential_expenses
        existing.savings_target = budget_data.savings_target
        existing.emergency_fund_target = budget_data.emergency_fund_target
        existing.category_limits = category_limits_json
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        setting = existing
    else:
        setting = BudgetSetting(
            user_id=user_id,
            month=budget_data.month,
            monthly_income=budget_data.monthly_income,
            essential_expenses=budget_data.essential_expenses,
            savings_target=budget_data.savings_target,
            emergency_fund_target=budget_data.emergency_fund_target,
            category_limits=category_limits_json,
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)

    # Sync category limits to the Category table
    if budget_data.category_limits:
        for cat_name, limit in budget_data.category_limits.items():
            cat = db.query(Category).filter(
                Category.user_id == user_id, Category.name == cat_name
            ).first()
            if cat:
                cat.budget_limit = limit
        db.commit()

    # Compute live progress
    plan = generate_budget_plan(
        monthly_income=setting.monthly_income,
        essential_expenses=setting.essential_expenses,
        savings_target=setting.savings_target,
        emergency_fund_target=setting.emergency_fund_target,
        category_limits=budget_data.category_limits,
        month=setting.month,
        db=db,
        user_id=user_id,
    )

    category_progress = get_category_budget_progress(db, setting.month, budget_data.category_limits or {}, user_id)

    return BudgetResponse(
        id=setting.id,
        month=setting.month,
        monthly_income=setting.monthly_income,
        essential_expenses=setting.essential_expenses,
        savings_target=plan["savings_target"],
        emergency_fund_target=plan.get("emergency_fund_target", 0.0),
        category_limits=budget_data.category_limits,
        discretionary_allowance=plan["discretionary_allowance"],
        unallocated_balance=plan["unallocated_balance"],
        is_balanced=plan["is_balanced"],
        deficit_amount=plan["deficit_amount"],
        deficit_warning=plan["deficit_warning"],
        recovery_plan=plan["recovery_plan"],
        category_progress=category_progress,
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )


def get_category_budget_progress(
    db: Session, month: str, category_limits: Dict[str, float], user_id: str = "default_user"
) -> List[Dict[str, Any]]:
    """Compares actual expenses per category against configured budget limits."""
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.date.startswith(month),
            Transaction.transaction_type == "expense",
        )
        .all()
    )

    actuals: Dict[str, float] = {}
    for t in transactions:
        actuals[t.category] = actuals.get(t.category, 0.0) + t.amount

    progress_list = []
    for cat, limit in category_limits.items():
        actual = round(actuals.get(cat, 0.0), 2)
        pct = round((actual / limit * 100.0), 1) if limit > 0 else 0.0
        remaining = round(limit - actual, 2)
        progress_list.append({
            "category": cat,
            "budgeted": limit,
            "spent": actual,
            "remaining": remaining,
            "percentage": pct,
            "is_over_budget": actual > limit,
        })

    return progress_list


def get_current_budget(
    db: Session, month: Optional[str] = None, user_id: str = "default_user"
) -> Optional[BudgetResponse]:
    """Retrieves current or latest budget with calculation results."""
    query = db.query(BudgetSetting).filter(BudgetSetting.user_id == user_id)
    if month:
        setting = query.filter(BudgetSetting.month == month).first()
    else:
        setting = query.order_by(BudgetSetting.month.desc()).first()

    if not setting:
        return None

    limits = {}
    if setting.category_limits:
        try:
            limits = json.loads(setting.category_limits)
        except Exception:
            limits = {}

    plan = generate_budget_plan(
        monthly_income=setting.monthly_income,
        essential_expenses=setting.essential_expenses,
        savings_target=setting.savings_target,
        emergency_fund_target=setting.emergency_fund_target,
        category_limits=limits,
        month=setting.month,
        db=db,
        user_id=user_id,
    )

    category_progress = get_category_budget_progress(db, setting.month, limits, user_id)

    return BudgetResponse(
        id=setting.id,
        month=setting.month,
        monthly_income=setting.monthly_income,
        essential_expenses=setting.essential_expenses,
        savings_target=plan["savings_target"],
        emergency_fund_target=plan.get("emergency_fund_target", 0.0),
        category_limits=limits,
        discretionary_allowance=plan["discretionary_allowance"],
        unallocated_balance=plan["unallocated_balance"],
        is_balanced=plan["is_balanced"],
        deficit_amount=plan["deficit_amount"],
        deficit_warning=plan["deficit_warning"],
        recovery_plan=plan["recovery_plan"],
        category_progress=category_progress,
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )
