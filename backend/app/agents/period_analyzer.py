import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import Category, SalaryRecord, Transaction
from app.schemas import (
    CategorySpend,
    DailyTrendPoint,
    PeriodComparison,
    PeriodReportResponse,
    PeriodSummary,
)


def parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def format_date(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def compute_date_ranges(
    period_type: str,
    reference_date_str: Optional[str] = None,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
) -> Tuple[date, date, date, date, str, str]:
    """
    Computes exact current and previous date boundaries.
    Handles month/year boundaries and leap years accurately.
    Returns (curr_start, curr_end, prev_start, prev_end, curr_label, prev_label)
    """
    today = parse_date(reference_date_str) if reference_date_str else date.today()

    if period_type == "daily":
        curr_start = today
        curr_end = today
        prev_start = today - timedelta(days=1)
        prev_end = prev_start
        curr_label = curr_start.strftime("%d %b %Y")
        prev_label = prev_start.strftime("%d %b %Y (Yesterday)")

    elif period_type == "weekly":
        # Monday to Sunday of the week
        curr_start = today - timedelta(days=today.weekday())
        curr_end = curr_start + timedelta(days=6)
        prev_start = curr_start - timedelta(days=7)
        prev_end = curr_end - timedelta(days=7)
        curr_label = f"Week of {curr_start.strftime('%d %b')} - {curr_end.strftime('%d %b %Y')}"
        prev_label = f"Prev Week ({prev_start.strftime('%d %b')} - {prev_end.strftime('%d %b')})"

    elif period_type == "yearly":
        year = today.year
        curr_start = date(year, 1, 1)
        curr_end = date(year, 12, 31)
        prev_start = date(year - 1, 1, 1)
        prev_end = date(year - 1, 12, 31)
        curr_label = f"Year {year}"
        prev_label = f"Year {year - 1}"

    elif period_type == "custom" and start_date_str and end_date_str:
        curr_start = parse_date(start_date_str)
        curr_end = parse_date(end_date_str)
        if curr_end < curr_start:
            curr_start, curr_end = curr_end, curr_start
        duration = (curr_end - curr_start).days + 1
        prev_end = curr_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=duration - 1)
        curr_label = f"{curr_start.strftime('%d %b %Y')} to {curr_end.strftime('%d %b %Y')}"
        prev_label = f"Previous {duration} Days"

    else:
        # Default: Monthly
        year = today.year
        month = today.month
        _, last_day = calendar.monthrange(year, month)
        curr_start = date(year, month, 1)
        curr_end = date(year, month, last_day)

        # Previous month
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
        _, prev_last_day = calendar.monthrange(prev_year, prev_month)
        prev_start = date(prev_year, prev_month, 1)
        prev_end = date(prev_year, prev_month, prev_last_day)

        curr_label = curr_start.strftime("%B %Y")
        prev_label = prev_start.strftime("%B %Y")

    return curr_start, curr_end, prev_start, prev_end, curr_label, prev_label


def get_period_summary_data(
    db: Session,
    start_d: date,
    end_d: date,
    label: str,
    categories_meta: Dict[str, Dict[str, Any]],
    user_id: str = "default_user",
) -> PeriodSummary:
    """Computes exact verified totals and category breakdown for a date interval."""
    start_str = format_date(start_d)
    end_str = format_date(end_d)

    # Query transactions in date range
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_str,
            Transaction.date <= end_str,
        )
        .all()
    )

    total_expense = 0.0
    direct_income = 0.0
    category_amounts = defaultdict(float)
    category_counts = defaultdict(int)

    for t in txns:
        if t.transaction_type == "expense":
            total_expense += t.amount
            category_amounts[t.category] += t.amount
            category_counts[t.category] += 1
        elif t.transaction_type == "income":
            direct_income += t.amount

    # Check for recorded salaries spanning this period
    # Extract distinct YYYY-MM months within the range
    months_in_range = set()
    cur = start_d
    while cur <= end_d:
        months_in_range.add(cur.strftime("%Y-%m"))
        # Move forward by roughly 25 days to avoid missing short months
        cur += timedelta(days=25)
    months_in_range.add(end_d.strftime("%Y-%m"))

    salaries = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.user_id == user_id, SalaryRecord.month.in_(list(months_in_range)))
        .all()
    )
    salary_amount = sum(s.amount for s in salaries)

    # Total income is salary + other non-salary income
    # (If a transaction is already categorized as Salary, we ensure no double counting)
    salary_txns = sum(t.amount for t in txns if t.transaction_type == "income" and t.category == "Salary")
    effective_salary = max(salary_amount, salary_txns)
    other_income = sum(t.amount for t in txns if t.transaction_type == "income" and t.category != "Salary")
    total_income = round(effective_salary + other_income, 2)
    total_expense = round(total_expense, 2)

    remaining_balance = round(total_income - total_expense, 2)
    savings_rate = (
        round(((total_income - total_expense) / total_income * 100.0), 2)
        if total_income > 0
        else 0.0
    )

    # Build category breakdown
    category_breakdown = []
    for cat, amt in sorted(category_amounts.items(), key=lambda x: x[1], reverse=True):
        pct = round((amt / total_expense * 100.0), 2) if total_expense > 0 else 0.0
        meta = categories_meta.get(cat, {})
        limit = meta.get("budget_limit", 0.0)
        remaining = max(0.0, limit - amt) if limit > 0 else None
        
        status = "normal"
        if limit > 0:
            if amt > limit:
                status = "exceeded"
            elif amt >= limit * 0.8:
                status = "warning"

        category_breakdown.append(
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

    return PeriodSummary(
        start_date=start_str,
        end_date=end_str,
        period_label=label,
        total_income=total_income,
        total_expenses=total_expense,
        remaining_balance=remaining_balance,
        savings_rate=savings_rate,
        transaction_count=len(txns),
        category_breakdown=category_breakdown,
    )


def compute_period_report(
    db: Session,
    period_type: str = "monthly",
    reference_date_str: Optional[str] = None,
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    user_id: str = "default_user",
) -> PeriodReportResponse:
    """
    Main entry point for Daily, Weekly, Monthly, Yearly, and Custom tracking.
    Computes current period, previous period, comparison deltas, and trend points.
    """
    curr_start, curr_end, prev_start, prev_end, curr_label, prev_label = compute_date_ranges(
        period_type, reference_date_str, start_date_str, end_date_str
    )

    # Fetch categories metadata
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    categories_meta = {
        c.name: {
            "color": c.color,
            "icon": c.icon,
            "is_essential": c.is_essential,
            "budget_limit": c.budget_limit,
        }
        for c in categories
    }

    current_summary = get_period_summary_data(
        db, curr_start, curr_end, curr_label, categories_meta, user_id
    )
    previous_summary = get_period_summary_data(
        db, prev_start, prev_end, prev_label, categories_meta, user_id
    )

    # Compute comparison
    prev_exp = previous_summary.total_expenses
    curr_exp = current_summary.total_expenses
    exp_delta = round(curr_exp - prev_exp, 2)
    exp_pct_change = round((exp_delta / prev_exp * 100.0), 2) if prev_exp > 0 else (100.0 if curr_exp > 0 else 0.0)

    income_delta = round(current_summary.total_income - previous_summary.total_income, 2)

    # Map category spend changes
    curr_cat_map = {c.category: c.amount for c in current_summary.category_breakdown}
    prev_cat_map = {c.category: c.amount for c in previous_summary.category_breakdown}
    all_cats = set(curr_cat_map.keys()) | set(prev_cat_map.keys())

    increased_cats = []
    decreased_cats = []

    for cat in all_cats:
        c_amt = curr_cat_map.get(cat, 0.0)
        p_amt = prev_cat_map.get(cat, 0.0)
        diff = round(c_amt - p_amt, 2)
        if diff > 0 and c_amt > 0:
            increased_cats.append({
                "category": cat,
                "current_amount": c_amt,
                "previous_amount": p_amt,
                "increase_amount": diff,
                "percentage_increase": round((diff / p_amt * 100.0), 1) if p_amt > 0 else 100.0,
            })
        elif diff < 0 and p_amt > 0:
            decreased_cats.append({
                "category": cat,
                "current_amount": c_amt,
                "previous_amount": p_amt,
                "decrease_amount": abs(diff),
                "percentage_decrease": round((abs(diff) / p_amt * 100.0), 1),
            })

    increased_cats.sort(key=lambda x: x["increase_amount"], reverse=True)
    decreased_cats.sort(key=lambda x: x["decrease_amount"], reverse=True)

    comparison = PeriodComparison(
        previous_expenses=prev_exp,
        expense_change_amount=exp_delta,
        expense_change_percent=exp_pct_change,
        previous_income=previous_summary.total_income,
        income_change_amount=income_delta,
        increased_categories=increased_cats,
        decreased_categories=decreased_cats,
    )

    # Compute daily/monthly trends based on period type
    trends: List[DailyTrendPoint] = []
    
    if period_type == "yearly":
        # Month-by-month trends for the year (12 months)
        year = curr_start.year
        for m in range(1, 13):
            _, last_d = calendar.monthrange(year, m)
            m_start = format_date(date(year, m, 1))
            m_end = format_date(date(year, m, last_d))
            month_label = calendar.month_abbr[m]

            m_txns = (
                db.query(Transaction)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.date >= m_start,
                    Transaction.date <= m_end,
                )
                .all()
            )
            m_exp = sum(t.amount for t in m_txns if t.transaction_type == "expense")
            m_inc = sum(t.amount for t in m_txns if t.transaction_type == "income")
            
            # Check salary for this month
            sal = db.query(SalaryRecord).filter(
                SalaryRecord.user_id == user_id,
                SalaryRecord.month == f"{year}-{m:02d}",
            ).first()
            if sal:
                m_inc = max(m_inc, sal.amount)

            trends.append(
                DailyTrendPoint(
                    date=f"{year}-{m:02d}",
                    label=month_label,
                    expenses=round(m_exp, 2),
                    income=round(m_inc, 2),
                )
            )

    else:
        # Day-by-day trends across curr_start to curr_end
        # Fetch all transactions in current period grouped by date
        txns = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.date >= format_date(curr_start),
                Transaction.date <= format_date(curr_end),
            )
            .all()
        )
        day_exp = defaultdict(float)
        day_inc = defaultdict(float)
        for t in txns:
            if t.transaction_type == "expense":
                day_exp[t.date] += t.amount
            elif t.transaction_type == "income":
                day_inc[t.date] += t.amount

        cur = curr_start
        while cur <= curr_end:
            d_str = format_date(cur)
            label = cur.strftime("%d %b") if (curr_end - curr_start).days > 7 else cur.strftime("%a %d")
            trends.append(
                DailyTrendPoint(
                    date=d_str,
                    label=label,
                    expenses=round(day_exp[d_str], 2),
                    income=round(day_inc[d_str], 2),
                )
            )
            cur += timedelta(days=1)

    return PeriodReportResponse(
        period_type=period_type,
        current_period=current_summary,
        previous_period=previous_summary,
        comparison=comparison,
        trends=trends,
    )
