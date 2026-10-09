import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models import Category, BudgetSetting, SalaryRecord, Transaction
from app.schemas import (
    AnalysisResponse,
    AnomalyItem,
    CategorySpend,
    MonthComparison,
    RecommendationItem,
    SummaryResponse,
)


def get_month_transactions(db: Session, month: Optional[str] = None, user_id: str = "default_user") -> List[Transaction]:
    """Retrieve transactions for a specific month (YYYY-MM) or all if not specified."""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if month:
        query = query.filter(Transaction.date.startswith(month))
    return query.order_by(Transaction.date.desc()).all()


def calculate_summary(db: Session, month: Optional[str] = None, user_id: str = "default_user") -> SummaryResponse:
    """
    Computes deterministic summary metrics: monthly salary, total income, total expenses,
    available balance, savings rate, and category breakdowns with budget limits.
    """
    transactions = get_month_transactions(db, month, user_id)
    target_month = month if month else datetime.now().strftime("%Y-%m")

    # Fetch recorded salary for month
    salary_record = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.user_id == user_id, SalaryRecord.month == target_month)
        .first()
    )
    if not salary_record and not month:
        # Fallback to most recent salary record
        salary_record = (
            db.query(SalaryRecord)
            .filter(SalaryRecord.user_id == user_id)
            .order_by(SalaryRecord.month.desc())
            .first()
        )
    current_month_salary = salary_record.amount if salary_record else 0.0

    # Fetch categories metadata
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    cat_meta_map = {
        c.name: {
            "color": c.color,
            "is_essential": c.is_essential,
            "budget_limit": c.budget_limit,
        }
        for c in categories
    }

    # Fetch budget limits from budget_settings if configured
    budget_setting = db.query(BudgetSetting).filter(
        BudgetSetting.user_id == user_id,
        BudgetSetting.month == target_month
    ).first()
    budget_limits_dict = {}
    if budget_setting and budget_setting.category_limits:
        try:
            budget_limits_dict = json.loads(budget_setting.category_limits)
        except Exception:
            pass

    total_expenses = 0.0
    other_income = 0.0
    salary_from_txns = 0.0
    category_expenses = defaultdict(float)
    category_counts = defaultdict(int)

    for t in transactions:
        if t.transaction_type == "income":
            if t.category == "Salary":
                salary_from_txns += t.amount
            else:
                other_income += t.amount
        else:
            total_expenses += t.amount
            category_expenses[t.category] += t.amount
            category_counts[t.category] += 1

    # Base salary is maximum of recorded SalaryRecord and explicit Salary transactions
    effective_salary = max(current_month_salary, salary_from_txns)
    total_income = round(effective_salary + other_income, 2)
    total_expenses = round(total_expenses, 2)
    available_balance = round(total_income - total_expenses, 2)

    # Safe savings rate calculation (0 if income is 0)
    if total_income > 0:
        raw_savings_rate = ((total_income - total_expenses) / total_income) * 100.0
        savings_rate = round(raw_savings_rate, 2)
    else:
        savings_rate = 0.0

    # Sort categories by spending descending
    top_categories = []
    for cat, amt in sorted(category_expenses.items(), key=lambda x: x[1], reverse=True):
        pct = round((amt / total_expenses * 100.0), 2) if total_expenses > 0 else 0.0
        meta = cat_meta_map.get(cat, {})
        limit = budget_limits_dict.get(cat, meta.get("budget_limit", 0.0))
        remaining = max(0.0, limit - amt) if limit > 0 else None

        status = "normal"
        if limit > 0:
            if amt > limit:
                status = "exceeded"
            elif amt >= limit * 0.8:
                status = "warning"

        top_categories.append(
            CategorySpend(
                category=cat,
                amount=round(amt, 2),
                percentage=pct,
                is_essential=meta.get("is_essential", False),
                transaction_count=category_counts[cat],
                color=meta.get("color", "#10b981"),
                budget_limit=limit,
                budget_remaining=remaining,
                budget_status=status,
            )
        )

    # Budget utilization check
    budget_utilization_percent = None
    if budget_setting and budget_setting.monthly_income > 0:
        max_spendable = max(budget_setting.monthly_income - budget_setting.savings_target, 1.0)
        budget_utilization_percent = round((total_expenses / max_spendable) * 100.0, 2)

    alerts = []
    if total_expenses > total_income and total_income > 0:
        deficit = round(total_expenses - total_income, 2)
        alerts.append(f"Spending alert: Expenses exceed income by ₹{deficit:,.2f} this period.")
    elif total_income == 0 and total_expenses > 0:
        alerts.append("No salary or income recorded yet for this period while expenses have occurred.")

    if budget_utilization_percent and budget_utilization_percent > 100:
        alerts.append(f"Budget exceeded: Spending is at {budget_utilization_percent}% of allowable spend.")
    elif budget_utilization_percent and budget_utilization_percent > 85:
        alerts.append(f"Budget caution: Spending is at {budget_utilization_percent}% of allowable spend.")

    # Category specific overrun alerts
    for cs in top_categories:
        if cs.budget_status == "exceeded":
            alerts.append(f"{cs.category} budget exceeded: Spent ₹{cs.amount:,.2f} of ₹{cs.budget_limit:,.2f} limit.")

    period_label = month if month else "All Time"

    return SummaryResponse(
        total_income=total_income,
        total_expenses=total_expenses,
        available_balance=available_balance,
        savings_rate=savings_rate,
        current_month_salary=current_month_salary,
        currency="INR",
        currency_symbol="₹",
        transaction_count=len(transactions),
        period=period_label,
        top_categories=top_categories,
        budget_utilization_percent=budget_utilization_percent,
        alerts=alerts,
    )


def calculate_analysis(db: Session, month: Optional[str] = None, user_id: str = "default_user") -> AnalysisResponse:
    """
    Performs deterministic spending analysis: essential vs discretionary proportions,
    largest expense drivers, month-over-month trajectory, anomalies, and recommendations.
    """
    summary = calculate_summary(db, month, user_id)
    transactions = get_month_transactions(db, month, user_id)

    essential_spending = 0.0
    discretionary_spending = 0.0

    for t in transactions:
        if t.transaction_type == "expense":
            if t.is_essential:
                essential_spending += t.amount
            else:
                discretionary_spending += t.amount

    essential_spending = round(essential_spending, 2)
    discretionary_spending = round(discretionary_spending, 2)
    total_exp = summary.total_expenses

    if total_exp > 0:
        essential_pct = round((essential_spending / total_exp) * 100.0, 2)
        discretionary_pct = round((discretionary_spending / total_exp) * 100.0, 2)
    else:
        essential_pct = 0.0
        discretionary_pct = 0.0

    # Month over month comparisons
    all_dates = db.query(Transaction.date).filter(Transaction.user_id == user_id).all()
    distinct_months = sorted(list(set(d[0][:7] for d in all_dates if len(d[0]) >= 7)), reverse=True)

    curr_m = month if month else (distinct_months[0] if distinct_months else datetime.now().strftime("%Y-%m"))
    prev_m = None
    if len(distinct_months) >= 2:
        try:
            curr_idx = distinct_months.index(curr_m)
            if curr_idx + 1 < len(distinct_months):
                prev_m = distinct_months[curr_idx + 1]
        except ValueError:
            prev_m = distinct_months[1] if len(distinct_months) > 1 else None

    has_sufficient_data = False
    income_change = None
    expense_change = None
    savings_change = None

    if prev_m:
        prev_summary = calculate_summary(db, prev_m, user_id)
        has_sufficient_data = True
        income_change = round(summary.total_income - prev_summary.total_income, 2)
        expense_change = round(summary.total_expenses - prev_summary.total_expenses, 2)
        savings_change = round(summary.savings_rate - prev_summary.savings_rate, 2)

    mom = MonthComparison(
        current_month=curr_m,
        previous_month=prev_m,
        income_change=income_change,
        expense_change=expense_change,
        savings_change=savings_change,
        has_sufficient_data=has_sufficient_data,
    )

    # Budget overruns
    budget_setting = db.query(BudgetSetting).filter(
        BudgetSetting.user_id == user_id,
        BudgetSetting.month == curr_m
    ).first()
    budget_overruns = []
    if budget_setting and budget_setting.category_limits:
        try:
            limits = json.loads(budget_setting.category_limits)
            category_totals = {c.category: c.amount for c in summary.top_categories}
            for cat, limit in limits.items():
                actual = category_totals.get(cat, 0.0)
                if actual > limit:
                    budget_overruns.append({
                        "category": cat,
                        "limit": limit,
                        "actual": actual,
                        "overrun": round(actual - limit, 2),
                        "overrun_percentage": round(((actual - limit) / limit) * 100.0, 1),
                    })
        except Exception:
            pass

    # Anomaly detection: flag transactions exceeding 35% of total expenses or 2.5x category average
    anomalies = []
    if total_exp > 0:
        for t in transactions:
            if t.transaction_type == "expense":
                if t.amount >= (total_exp * 0.35) and t.amount >= 2000.0:
                    anomalies.append(
                        AnomalyItem(
                            category=t.category,
                            description=t.description,
                            amount=t.amount,
                            reason=f"Single expense represents {round((t.amount / total_exp) * 100, 1)}% of total monthly expenses.",
                        )
                    )

    # Actionable savings recommendations
    recommendations = []
    discretionary_cats = [c for c in summary.top_categories if not c.is_essential]

    if discretionary_cats:
        top_disc = discretionary_cats[0]
        potential_save = round(top_disc.amount * 0.25, 2)
        recommendations.append(
            RecommendationItem(
                title=f"Trim {top_disc.category} Outflow",
                category=top_disc.category,
                impact=f"Potential monthly saving: ₹{potential_save:,.2f}",
                action=f"Reducing discretionary {top_disc.category.lower()} by 25% frees up ₹{potential_save:,.2f} for your savings buffer.",
                potential_savings=potential_save,
            )
        )

    if discretionary_spending > (summary.total_income * 0.35) and summary.total_income > 0:
        save_target = round(discretionary_spending - (summary.total_income * 0.30), 2)
        recommendations.append(
            RecommendationItem(
                title="Lifestyle Spending Optimization",
                category="Discretionary",
                impact="Realign to prudent wants ratio (<30%)",
                action=f"Discretionary spending is at {discretionary_pct}%. Trimming non-essentials by ₹{save_target:,.2f} restores financial breathing room.",
                potential_savings=save_target,
            )
        )

    if not recommendations:
        recommendations.append(
            RecommendationItem(
                title="Sustain Healthy Cash Flow",
                category="Savings",
                impact="Build 3-6 month emergency fund",
                action="Your essentials and discretionary expenses are well-balanced. Direct current surplus toward your savings milestones.",
                potential_savings=0.0,
            )
        )

    return AnalysisResponse(
        category_breakdown=summary.top_categories,
        largest_categories=summary.top_categories[:4],
        essential_spending=essential_spending,
        discretionary_spending=discretionary_spending,
        essential_percentage=essential_pct,
        discretionary_percentage=discretionary_pct,
        month_over_month=mom,
        budget_overruns=budget_overruns,
        anomalies=anomalies[:3],
        recommendations=recommendations,
    )
