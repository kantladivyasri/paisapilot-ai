from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models import BudgetSetting, SalaryRecord, Transaction


def get_salary_for_month(
    db: Session, month: Optional[str] = None, user_id: str = "default_user"
) -> Optional[SalaryRecord]:
    """Retrieves salary for a specified month (YYYY-MM) or the latest recorded salary."""
    if month:
        record = (
            db.query(SalaryRecord)
            .filter(SalaryRecord.user_id == user_id, SalaryRecord.month == month)
            .first()
        )
        if record:
            return record

    # Fallback to most recent salary
    return (
        db.query(SalaryRecord)
        .filter(SalaryRecord.user_id == user_id)
        .order_by(SalaryRecord.month.desc())
        .first()
    )


def save_or_update_salary(
    db: Session,
    month: str,
    amount: float,
    notes: Optional[str] = None,
    user_id: str = "default_user",
) -> SalaryRecord:
    """Creates or updates a monthly salary record."""
    amount = round(amount, 2)
    record = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.user_id == user_id, SalaryRecord.month == month)
        .first()
    )

    if record:
        record.amount = amount
        if notes is not None:
            record.notes = notes
        record.updated_at = datetime.utcnow()
    else:
        record = SalaryRecord(
            user_id=user_id,
            month=month,
            amount=amount,
            notes=notes,
        )
        db.add(record)

    # Also keep budget setting monthly income in sync if budget exists
    budget = (
        db.query(BudgetSetting)
        .filter(BudgetSetting.user_id == user_id, BudgetSetting.month == month)
        .first()
    )
    if budget:
        budget.monthly_income = amount
        budget.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(record)
    return record


def get_all_salaries(db: Session, user_id: str = "default_user") -> List[SalaryRecord]:
    """Returns all recorded salaries sorted chronologically descending."""
    return (
        db.query(SalaryRecord)
        .filter(SalaryRecord.user_id == user_id)
        .order_by(SalaryRecord.month.desc())
        .all()
    )


def calculate_salary_dashboard_metrics(
    db: Session, month: str, user_id: str = "default_user"
) -> Dict[str, float]:
    """Calculates month's salary, total expenses, remaining balance, and savings rate."""
    salary_record = (
        db.query(SalaryRecord)
        .filter(SalaryRecord.user_id == user_id, SalaryRecord.month == month)
        .first()
    )
    salary_amount = salary_record.amount if salary_record else 0.0

    # Query all expenses for the month
    expenses = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date.startswith(month),
        )
        .all()
    )
    total_expenses = round(sum(t.amount for t in expenses), 2)

    # Query any extra income transactions
    extra_incomes = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "income",
            Transaction.category != "Salary",
            Transaction.date.startswith(month),
        )
        .all()
    )
    extra_income_total = round(sum(t.amount for t in extra_incomes), 2)

    effective_income = round(salary_amount + extra_income_total, 2)
    remaining_balance = round(effective_income - total_expenses, 2)
    savings_rate = (
        round(((effective_income - total_expenses) / effective_income * 100.0), 2)
        if effective_income > 0
        else 0.0
    )

    return {
        "current_month_salary": salary_amount,
        "total_expenses": total_expenses,
        "remaining_balance": remaining_balance,
        "savings_rate": savings_rate,
        "effective_income": effective_income,
    }
