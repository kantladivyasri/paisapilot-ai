import calendar
import json
import os
from collections import defaultdict
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from app.models import Category, BudgetSetting, SalaryRecord, Transaction
from app.schemas import ForecastResponse, UnwantedSpendingAlert


def get_server_timezone() -> ZoneInfo:
    """Returns the server configured timezone, defaulting to Asia/Kolkata."""
    tz_name = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Asia/Kolkata")


def get_current_date() -> date:
    """Returns current date in server timezone."""
    return datetime.now(get_server_timezone()).date()


def get_current_datetime() -> datetime:
    """Returns current datetime in server timezone."""
    return datetime.now(get_server_timezone())


def get_month_calendar_bounds(target_month_str: str) -> Tuple[int, int, int, str]:
    """
    Returns (days_passed, days_remaining, total_days_in_month, evaluation_date_str).
    Accurately accounts for timezone and calendar boundaries.
    """
    today = get_current_date()
    try:
        parts = target_month_str.split("-")
        year, month = int(parts[0]), int(parts[1])
    except Exception:
        year, month = today.year, today.month

    total_days = calendar.monthrange(year, month)[1]

    if today.year == year and today.month == month:
        days_passed = max(1, min(today.day, total_days))
        days_remaining = max(0, total_days - days_passed)
        evaluation_date_str = today.strftime("%d %b %Y")
    elif (year < today.year) or (year == today.year and month < today.month):
        days_passed = total_days
        days_remaining = 0
        evaluation_date_str = f"{total_days:02d} {calendar.month_abbr[month]} {year}"
    else:
        days_passed = 1
        days_remaining = total_days - 1
        evaluation_date_str = f"01 {calendar.month_abbr[month]} {year}"

    return days_passed, days_remaining, total_days, evaluation_date_str


def calculate_category_regular_baselines(
    db: Session, target_month: str, user_id: str = "default_user"
) -> Tuple[Dict[str, float], bool, int]:
    """
    Calculates historical 'regular' baseline spending for categories.
    Looks at actual prior recorded months.
    Returns (regular_baselines, has_sufficient_history, history_months_count).
    Does NOT fabricate baseline figures if insufficient historical data exists.
    """
    all_dates = (
        db.query(Transaction.date)
        .filter(Transaction.user_id == user_id, Transaction.transaction_type == "expense")
        .all()
    )
    distinct_months = sorted(
        list(set(d[0][:7] for d in all_dates if len(d[0]) >= 7 and d[0][:7] < target_month)),
        reverse=True,
    )
    prior_months = distinct_months[:3]
    has_sufficient_history = len(prior_months) >= 1

    # Fetch user configured category limits
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    category_limits = {
        c.name: float(c.budget_limit) for c in categories if c.budget_limit and c.budget_limit > 0
    }

    budget_setting = (
        db.query(BudgetSetting)
        .filter(BudgetSetting.user_id == user_id, BudgetSetting.month == target_month)
        .first()
    )
    if budget_setting and budget_setting.category_limits:
        try:
            extra_limits = json.loads(budget_setting.category_limits)
            category_limits.update({k: float(v) for k, v in extra_limits.items() if v > 0})
        except Exception:
            pass

    history_cat_totals = defaultdict(list)
    if prior_months:
        for pm in prior_months:
            txns = (
                db.query(Transaction)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.date.startswith(pm),
                    Transaction.transaction_type == "expense",
                )
                .all()
            )
            month_spend = defaultdict(float)
            for t in txns:
                month_spend[t.category] += t.amount
            for cat, amt in month_spend.items():
                history_cat_totals[cat].append(amt)

    regular_baselines: Dict[str, float] = {}

    for cat in categories:
        cat_name = cat.name
        if has_sufficient_history and cat_name in history_cat_totals and len(history_cat_totals[cat_name]) > 0:
            regular_baselines[cat_name] = round(
                sum(history_cat_totals[cat_name]) / len(history_cat_totals[cat_name]), 2
            )
        elif cat_name in category_limits:
            regular_baselines[cat_name] = category_limits[cat_name]
        else:
            # When insufficient history, assign 0.0 baseline (do not fabricate)
            regular_baselines[cat_name] = 0.0

    return regular_baselines, has_sufficient_history, len(prior_months)


def compute_forecast(
    db: Session, target_month: Optional[str] = None, user_id: str = "default_user"
) -> ForecastResponse:
    """
    Core AI Prediction & Forecast Engine:
    1. Uses server configured timezone and exact calendar elapsed bounds.
    2. Projects total monthly expenses & end-of-month savings with mathematical consistency.
    3. Clearly distinguishes actual recorded expenses from estimated projections.
    4. Only checks baseline overspending if real historical data exists; never fabricates comparisons.
    5. Formats a clean, professional, concise forecast presentation according to requirements.
    """
    today = get_current_date()
    month_str = target_month or today.strftime("%Y-%m")
    days_passed, days_remaining, total_days, evaluation_date = get_month_calendar_bounds(month_str)

    # 1. Fetch current month salary / income
    salary_record = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.user_id == user_id, SalaryRecord.month == month_str)
        .first()
    )
    salary_amount = float(salary_record.amount) if salary_record else 0.0
    salary_recorded = salary_amount > 0

    current_txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.date.startswith(month_str))
        .all()
    )

    other_income = 0.0
    current_expenses = 0.0
    category_spends = defaultdict(float)

    for t in current_txns:
        if t.transaction_type == "income":
            if t.category != "Salary":
                other_income += t.amount
            elif not salary_recorded:
                salary_amount += t.amount
                salary_recorded = True
        else:
            current_expenses += t.amount
            category_spends[t.category] += t.amount

    current_income = round(salary_amount + other_income, 2)
    current_expenses = round(current_expenses, 2)
    current_savings = round(current_income - current_expenses, 2) if current_income > 0 else 0.0

    # 2. Daily spending pace
    daily_spending_pace = round(current_expenses / max(1, days_passed), 2)

    # 3. Category metadata & baselines
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    essential_map = {c.name: c.is_essential for c in categories}

    regular_baselines, has_sufficient_history, history_months_count = calculate_category_regular_baselines(
        db, month_str, user_id
    )

    # 4. Projections: segment fixed recurring vs variable pace
    projected_category_spends = {}
    unwanted_spending_alerts: List[UnwantedSpendingAlert] = []
    total_unwanted_spent = 0.0
    projected_unwanted_spent = 0.0
    regular_unwanted_baseline = 0.0

    all_cat_names = set(category_spends.keys()) | set(regular_baselines.keys())

    for cat in all_cat_names:
        spent = category_spends.get(cat, 0.0)
        is_ess = essential_map.get(cat, True)
        unwanted_keywords = [
            "shopping", "entertainment", "dining", "food", "party", "leisure",
            "subscription", "luxury", "gift"
        ]
        if any(kw in cat.lower() for kw in unwanted_keywords):
            is_ess = False

        baseline = regular_baselines.get(cat, 0.0)

        # Projection logic: recurring fixed items already paid are projected flat
        if days_remaining == 0:
            projected = spent
        elif cat.lower() in ["rent", "rent & housing", "tuition", "education", "insurance"] and spent > 0:
            projected = spent
        else:
            daily_rate = spent / max(1, days_passed)
            projected = spent + (daily_rate * days_remaining)

        projected = round(projected, 2)
        projected_category_spends[cat] = projected

        # Track discretionary outflow
        if not is_ess:
            total_unwanted_spent += spent
            projected_unwanted_spent += projected
            if baseline > 0:
                regular_unwanted_baseline += baseline

            # Flag only if we have sufficient history and baseline > 0
            if has_sufficient_history and baseline > 0:
                if projected > (baseline * 1.20) and (spent >= 400.0 or projected >= baseline + 500.0):
                    excess_amt = round(projected - baseline, 2)
                    excess_pct = round(((projected - baseline) / baseline) * 100.0, 1)
                    severity = "critical" if (projected > baseline * 1.50 or excess_amt >= 2000.0) else "warning"

                    alert_msg = (
                        f"Discretionary spending on {cat} is tracking above your regular baseline. "
                        f"Recorded ₹{spent:,.2f} in {days_passed} days; estimated month-end is ₹{projected:,.2f} "
                        f"(+{excess_pct}% over your ₹{baseline:,.2f} baseline)."
                    )
                    recommendation = (
                        f"Reduce {cat.lower()} purchases over the remaining {days_remaining} days to save "
                        f"₹{excess_amt:,.2f} and preserve your savings target."
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

    # Total Projected Savings & Estimated Remaining Balance
    if current_income > 0:
        estimated_remaining_balance = round(current_income - projected_expenses, 2)
        projected_savings = estimated_remaining_balance
        projected_savings_rate = round((projected_savings / current_income) * 100.0, 2)
    else:
        estimated_remaining_balance = 0.0
        projected_savings = 0.0
        projected_savings_rate = 0.0

    # Status classification
    if current_income > 0:
        if estimated_remaining_balance < 0:
            projected_status = "deficit_risk"
        elif projected_savings_rate < 15.0 or len(unwanted_spending_alerts) >= 2:
            projected_status = "caution"
        else:
            projected_status = "healthy"
    else:
        projected_status = "caution" if current_expenses > 0 else "healthy"

    # Regular daily baseline (only computed if sufficient history exists)
    if has_sufficient_history and regular_unwanted_baseline > 0:
        regular_daily_baseline = round(sum(regular_baselines.values()) / max(1, total_days), 2)
    else:
        regular_daily_baseline = 0.0

    # Summary of discretionary spending
    is_overspending_on_unwanted = len(unwanted_spending_alerts) > 0

    if not has_sufficient_history:
        overspending_summary = (
            "Historical spending data is insufficient to establish a regular spending baseline. "
            "Logging transactions across multiple months will establish your personal baseline."
        )
    elif is_overspending_on_unwanted:
        top_culprits = ", ".join(a.category for a in unwanted_spending_alerts[:2])
        total_excess = sum(a.excess_amount for a in unwanted_spending_alerts)
        overspending_summary = (
            f"Discretionary spending on {top_culprits} is tracking higher than your regular baseline. "
            f"Projected discretionary excess is ₹{total_excess:,.2f}. Curbing these purchases over the remaining "
            f"{days_remaining} days will preserve your projected savings."
        )
    else:
        overspending_summary = (
            f"Discretionary spending is well within your regular benchmarks. "
            f"Projected month-end savings: ₹{projected_savings:,.2f} ({projected_savings_rate}%)."
        )

    # 5. Requirement 4: Standardized Clean Forecast Presentation
    try:
        month_label = datetime.strptime(month_str, "%Y-%m").strftime("%B %Y")
    except Exception:
        month_label = month_str

    if not salary_recorded:
        rec_text = (
            "Set your monthly salary in the Salary section to verify your projected savings rate "
            "and track your estimated remaining balance."
        )
    elif estimated_remaining_balance >= 0:
        rec_text = (
            f"At your current daily pace, your spending remains well within your salary. Keep daily "
            f"variable expenses around ₹{daily_spending_pace:,.2f} to protect your projected ₹{estimated_remaining_balance:,.2f} surplus."
        )
    else:
        deficit_amt = abs(estimated_remaining_balance)
        daily_cut = round(deficit_amt / max(1, days_remaining), 2)
        rec_text = (
            f"Estimated expenses exceed your salary by ₹{deficit_amt:,.2f}. Trimming variable spending by "
            f"₹{daily_cut:,.2f}/day over the remaining {days_remaining} days will avoid a month-end deficit."
        )

    salary_display = f"₹{salary_amount:,.2f}" if salary_recorded else "Not recorded"
    balance_display = (
        f"₹{estimated_remaining_balance:,.2f}"
        if salary_recorded
        else "Unavailable (requires recorded salary)"
    )

    forecast_presentation = (
        f"### Expense Forecast for {month_label} (as of {evaluation_date})\n\n"
        f"- **Total expenses recorded so far:** ₹{current_expenses:,.2f}\n"
        f"- **Average daily spending ({days_passed} days elapsed):** ₹{daily_spending_pace:,.2f}/day\n"
        f"- **Estimated month-end expenses (projection):** ₹{projected_expenses:,.2f}\n"
        f"- **Monthly salary:** {salary_display}\n"
        f"- **Estimated remaining balance (projection):** {balance_display}\n\n"
        f"**Recommendation:** {rec_text}"
    )

    return ForecastResponse(
        month=month_str,
        evaluation_date=evaluation_date,
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
        has_sufficient_history=has_sufficient_history,
        history_months_count=history_months_count,
        salary_recorded=salary_recorded,
        monthly_salary=salary_amount,
        estimated_remaining_balance=estimated_remaining_balance,
        unwanted_spending_alerts=unwanted_spending_alerts,
        total_unwanted_spent=round(total_unwanted_spent, 2),
        projected_unwanted_spent=round(projected_unwanted_spent, 2),
        regular_unwanted_baseline=round(regular_unwanted_baseline, 2),
        is_overspending_on_unwanted=is_overspending_on_unwanted,
        overspending_summary=overspending_summary,
        forecast_presentation=forecast_presentation,
    )
