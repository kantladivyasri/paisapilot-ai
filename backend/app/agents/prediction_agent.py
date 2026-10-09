import calendar
import json
from collections import defaultdict
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import Category, BudgetSetting, SalaryRecord, Transaction
from app.schemas import ForecastResponse, UnwantedSpendingAlert


def get_month_calendar_bounds(target_month_str: str) -> Tuple[int, int, int]:
    """
    Returns (days_passed, days_remaining, total_days_in_month)
    """
    try:
        parts = target_month_str.split("-")
        year, month = int(parts[0]), int(parts[1])
    except Exception:
        today = date.today()
        year, month = today.year, today.month

    total_days = calendar.monthrange(year, month)[1]
    today = date.today()

    if today.year == year and today.month == month:
        days_passed = max(1, min(today.day, total_days))
        days_remaining = max(0, total_days - days_passed)
    elif (year < today.year) or (year == today.year and month < today.month):
        days_passed = total_days
        days_remaining = 0
    else:
        days_passed = 1
        days_remaining = total_days - 1

    return days_passed, days_remaining, total_days


def calculate_category_regular_baselines(
    db: Session, target_month: str, user_id: str = "default_user"
) -> Dict[str, float]:
    """
    Calculates historical 'regular' baseline spending for categories.
    Looks at the last 3 prior months. If insufficient historical data,
    falls back to category budget limits or standard benchmarks.
    """
    all_dates = db.query(Transaction.date).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "expense"
    ).all()
    distinct_months = sorted(list(set(d[0][:7] for d in all_dates if len(d[0]) >= 7 and d[0][:7] < target_month)), reverse=True)
    prior_months = distinct_months[:3]

    history_cat_totals = defaultdict(list)
    if prior_months:
        for pm in prior_months:
            txns = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.date.startswith(pm),
                Transaction.transaction_type == "expense",
            ).all()
            month_spend = defaultdict(float)
            for t in txns:
                month_spend[t.category] += t.amount
            for cat, amt in month_spend.items():
                history_cat_totals[cat].append(amt)

    # Fetch Category definitions for limits
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    category_limits = {c.name: c.budget_limit for c in categories if c.budget_limit and c.budget_limit > 0}

    # Fetch budget setting limits
    budget_setting = db.query(BudgetSetting).filter(
        BudgetSetting.user_id == user_id,
        BudgetSetting.month == target_month
    ).first()
    if budget_setting and budget_setting.category_limits:
        try:
            extra_limits = json.loads(budget_setting.category_limits)
            category_limits.update({k: float(v) for k, v in extra_limits.items() if v > 0})
        except Exception:
            pass

    # Standard fallback baselines if completely fresh database
    default_fallbacks = {
        "Food & Dining": 3000.0,
        "Shopping": 2500.0,
        "Entertainment": 1500.0,
        "Groceries": 3500.0,
        "Transportation": 1800.0,
        "Bills & Utilities": 2000.0,
        "Rent & Housing": 8000.0,
        "Healthcare": 1000.0,
        "Education": 2500.0,
        "Miscellaneous": 1000.0,
    }

    regular_baselines = {}
    for cat in categories:
        cat_name = cat.name
        if cat_name in history_cat_totals and len(history_cat_totals[cat_name]) > 0:
            regular_baselines[cat_name] = round(sum(history_cat_totals[cat_name]) / len(history_cat_totals[cat_name]), 2)
        elif cat_name in category_limits:
            regular_baselines[cat_name] = float(category_limits[cat_name])
        else:
            regular_baselines[cat_name] = default_fallbacks.get(cat_name, 1500.0)

    for def_cat, val in default_fallbacks.items():
        if def_cat not in regular_baselines:
            regular_baselines[def_cat] = val

    return regular_baselines


def compute_forecast(
    db: Session, target_month: Optional[str] = None, user_id: str = "default_user"
) -> ForecastResponse:
    """
    Core AI Prediction & Forecast Engine:
    1. Analyzes current spending trajectory & daily pace.
    2. Projects total monthly expenses & end-of-month savings.
    3. Detects if user is spending too much on unwanted / discretionary items compared to regular baseline.
    4. Issues actionable warnings with exact excess amounts.
    """
    month_str = target_month or datetime.now().strftime("%Y-%m")
    days_passed, days_remaining, total_days = get_month_calendar_bounds(month_str)

    # 1. Fetch current month salary / income
    salary_record = db.query(SalaryRecord).filter(
        SalaryRecord.user_id == user_id, SalaryRecord.month == month_str
    ).first()
    salary_amount = salary_record.amount if salary_record else 0.0

    current_txns = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date.startswith(month_str),
    ).all()

    other_income = 0.0
    current_expenses = 0.0
    category_spends = defaultdict(float)

    for t in current_txns:
        if t.transaction_type == "income":
            if t.category != "Salary":
                other_income += t.amount
            elif salary_amount == 0:
                salary_amount = t.amount
        else:
            current_expenses += t.amount
            category_spends[t.category] += t.amount

    current_income = round(salary_amount + other_income, 2)
    current_expenses = round(current_expenses, 2)
    current_savings = round(current_income - current_expenses, 2)

    # 2. Category metadata (essential vs unwanted/discretionary)
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    essential_map = {c.name: c.is_essential for c in categories}

    # Baselines
    regular_baselines = calculate_category_regular_baselines(db, month_str, user_id)

    # 3. Forecast calculation
    projected_category_spends = {}
    unwanted_spending_alerts: List[UnwantedSpendingAlert] = []

    total_unwanted_spent = 0.0
    projected_unwanted_spent = 0.0
    regular_unwanted_baseline = 0.0

    all_cat_names = set(category_spends.keys()) | set(regular_baselines.keys())

    for cat in all_cat_names:
        spent = category_spends.get(cat, 0.0)
        is_ess = essential_map.get(cat, True)
        unwanted_keywords = ["shopping", "entertainment", "dining", "food", "party", "leisure", "subscription", "luxury", "gift"]
        if any(kw in cat.lower() for kw in unwanted_keywords):
            is_ess = False

        baseline = regular_baselines.get(cat, 2000.0)

        # Projection logic
        if days_remaining == 0:
            projected = spent
        elif cat.lower() in ["rent", "rent & housing", "tuition", "education", "insurance"] and spent > 0:
            projected = spent
        else:
            daily_rate = spent / max(1, days_passed)
            projected = spent + (daily_rate * days_remaining)

        projected = round(projected, 2)
        projected_category_spends[cat] = projected

        # Check Unwanted / Discretionary Overspending
        if not is_ess:
            total_unwanted_spent += spent
            projected_unwanted_spent += projected
            regular_unwanted_baseline += baseline

            # Flag if projected is >20% above regular baseline and spend is meaningful (>= 400)
            if projected > (baseline * 1.20) and (spent >= 400.0 or projected >= baseline + 500.0):
                excess_amt = round(projected - baseline, 2)
                excess_pct = round(((projected - baseline) / max(1.0, baseline)) * 100.0, 1)
                severity = "critical" if (projected > baseline * 1.50 or excess_amt >= 2000.0) else "warning"

                alert_msg = (
                    f"⚠️ High Discretionary Alert: You have spent ₹{spent:,.2f} on {cat} in {days_passed} days. "
                    f"At your current daily pace, {cat} is projected to reach ₹{projected:,.2f} by month-end, "
                    f"which is {excess_pct}% higher than your regular benchmark of ₹{baseline:,.2f}."
                )
                recommendation = (
                    f"Cut down {cat.lower()} purchases over the remaining {days_remaining} days to save ₹{excess_amt:,.2f} "
                    f"and protect your monthly savings target."
                )

                unwanted_spending_alerts.append(
                    UnwantedSpendingAlert(
                        category=cat,
                        is_essential=False,
                        current_spent=spent,
                        regular_baseline=baseline,
                        projected_spent=projected,
                        excess_amount=excess_amt,
                        excess_percentage=excess_pct,
                        severity=severity,
                        message=alert_msg,
                        recommendation=recommendation,
                    )
                )

    # Total Projected Expenses
    projected_expenses = round(sum(projected_category_spends.values()), 2)
    projected_expenses = max(current_expenses, projected_expenses)

    # Total Projected Savings
    projected_savings = round(current_income - projected_expenses, 2) if current_income > 0 else 0.0
    projected_savings_rate = (
        round((projected_savings / current_income) * 100.0, 2) if current_income > 0 else 0.0
    )

    # Status classification
    if projected_savings < 0:
        projected_status = "deficit_risk"
    elif projected_savings_rate < 15.0 or len(unwanted_spending_alerts) >= 2:
        projected_status = "caution"
    else:
        projected_status = "healthy"

    daily_spending_pace = round(current_expenses / max(1, days_passed), 2)
    regular_daily_baseline = round(sum(regular_baselines.values()) / max(1, total_days), 2)

    is_overspending_on_unwanted = len(unwanted_spending_alerts) > 0 or (
        projected_unwanted_spent > regular_unwanted_baseline * 1.25 and regular_unwanted_baseline > 0
    )

    if is_overspending_on_unwanted:
        top_culprits = ", ".join(a.category for a in unwanted_spending_alerts[:2])
        total_excess = sum(a.excess_amount for a in unwanted_spending_alerts)
        overspending_summary = (
            f"Caution: You are spending more than regular on unwanted discretionary items ({top_culprits}). "
            f"Projected discretionary excess is ₹{total_excess:,.2f}. Curbing these purchases over the remaining {days_remaining} days "
            f"will preserve your projected ₹{projected_savings:,.2f} savings!"
        )
    else:
        overspending_summary = (
            f"Your spending pace is controlled! Discretionary outflows are tracking safely within regular benchmarks. "
            f"Projected month-end savings: ₹{projected_savings:,.2f} ({projected_savings_rate}%)."
        )

    return ForecastResponse(
        month=month_str,
        days_passed=days_passed,
        days_remaining=days_remaining,
        total_days=total_days,
        current_expenses=current_expenses,
        current_income=current_income,
        current_savings=current_savings,
        projected_expenses=projected_expenses,
        projected_savings=projected_savings,
        projected_savings_rate=projected_savings_rate,
        projected_status=projected_status,
        daily_spending_pace=daily_spending_pace,
        regular_daily_baseline=regular_daily_baseline,
        unwanted_spending_alerts=unwanted_spending_alerts,
        total_unwanted_spent=round(total_unwanted_spent, 2),
        projected_unwanted_spent=round(projected_unwanted_spent, 2),
        regular_unwanted_baseline=round(regular_unwanted_baseline, 2),
        is_overspending_on_unwanted=is_overspending_on_unwanted,
        overspending_summary=overspending_summary,
    )
