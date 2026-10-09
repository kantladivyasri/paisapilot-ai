import json
from datetime import datetime
from typing import Any, Dict
from sqlalchemy.orm import Session

from app.models import BudgetSetting, ChatMessage, SalaryRecord, SavingsGoal, Transaction

FICTIONAL_PROFILE_30K = [
    # Income
    {"description": "Monthly Salary Credit", "amount": 30000.0, "type": "income", "category": "Salary", "essential": False, "day": "01", "payment_method": "Net Banking"},
    # Essential Expenses
    {"description": "Apartment Monthly Rent", "amount": 7000.0, "type": "expense", "category": "Rent & Housing", "essential": True, "day": "02", "payment_method": "UPI"},
    {"description": "Monthly Groceries & Ration", "amount": 2500.0, "type": "expense", "category": "Groceries", "essential": True, "day": "04", "payment_method": "UPI"},
    {"description": "Fuel & Metro Commute", "amount": 1000.0, "type": "expense", "category": "Transportation", "essential": True, "day": "06", "payment_method": "Debit Card"},
    {"description": "Electricity & Utility Bill", "amount": 1200.0, "type": "expense", "category": "Bills & Utilities", "essential": True, "day": "08", "payment_method": "UPI"},
    {"description": "Professional Course & Books", "amount": 3000.0, "type": "expense", "category": "Education", "essential": True, "day": "12", "payment_method": "Credit Card"},
    {"description": "Pharmacy & Health Checkup", "amount": 500.0, "type": "expense", "category": "Healthcare", "essential": True, "day": "16", "payment_method": "UPI"},
    # Discretionary Expenses
    {"description": "Weekend Dining & Swiggy Delivery", "amount": 1500.0, "type": "expense", "category": "Food & Dining", "essential": False, "day": "10", "payment_method": "UPI"},
    {"description": "Clothing & Essentials Shopping", "amount": 1800.0, "type": "expense", "category": "Shopping", "essential": False, "day": "14", "payment_method": "Credit Card"},
    {"description": "OTT Streaming & Movie Tickets", "amount": 500.0, "type": "expense", "category": "Entertainment", "essential": False, "day": "18", "payment_method": "Credit Card"},
]


def seed_demo_data(db: Session, force: bool = False, user_id: str = "default_user") -> Dict[str, Any]:
    """
    Seeds the canonical ₹30,000 fictional demo profile.
    Prevents repeated seeding if data already exists unless force=True.
    """
    count = db.query(Transaction).filter(Transaction.user_id == user_id).count()
    if count > 0 and not force:
        return {
            "status": "already_seeded",
            "message": f"Database already contains {count} transactions. Use reset or force to re-seed.",
            "transaction_count": count,
        }

    if force:
        reset_all_data(db, user_id=user_id)

    current_ym = datetime.now().strftime("%Y-%m")

    # 1. Seed monthly salary
    salary = SalaryRecord(
        user_id=user_id,
        month=current_ym,
        amount=30000.0,
        notes="Canonical hackathon demo profile salary",
    )
    db.add(salary)

    # 2. Insert transactions
    created_txns = []
    for item in FICTIONAL_PROFILE_30K:
        date_str = f"{current_ym}-{item['day']}"
        t = Transaction(
            user_id=user_id,
            description=item["description"],
            amount=item["amount"],
            transaction_type=item["type"],
            category=item["category"],
            payment_method=item.get("payment_method", "UPI"),
            is_essential=item["essential"],
            date=date_str,
            notes="Fictional hackathon demo dataset (₹30k Profile)",
        )
        created_txns.append(t)

    db.add_all(created_txns)

    # 3. Insert default balanced budget
    category_limits = {
        "Rent & Housing": 7000.0,
        "Groceries": 2500.0,
        "Transportation": 1200.0,
        "Bills & Utilities": 1200.0,
        "Education": 3000.0,
        "Healthcare": 1000.0,
        "Food & Dining": 2000.0,
        "Shopping": 2000.0,
        "Entertainment": 1000.0,
    }
    budget = BudgetSetting(
        user_id=user_id,
        month=current_ym,
        monthly_income=30000.0,
        essential_expenses=15200.0,
        savings_target=6000.0,
        emergency_fund_target=2000.0,
        category_limits=json.dumps(category_limits),
    )
    db.add(budget)

    # 4. Insert demo savings goals
    goals = [
        SavingsGoal(
            user_id=user_id,
            name="Emergency Fund (3 Months)",
            target_amount=60000.0,
            current_amount=22000.0,
            target_date=f"{int(current_ym[:4]) + 1}-03-31",
            monthly_contribution=5000.0,
        ),
        SavingsGoal(
            user_id=user_id,
            name="Upskilling & Tech Certification",
            target_amount=15000.0,
            current_amount=6000.0,
            target_date=f"{current_ym[:4]}-12-31",
            monthly_contribution=3000.0,
        ),
    ]
    db.add_all(goals)

    db.commit()

    return {
        "status": "success",
        "message": "Fictional ₹30,000 demo profile successfully seeded.",
        "transactions_seeded": len(created_txns),
        "income": 30000.0,
        "expenses": 19000.0,
        "balance": 11000.0,
        "savings_rate_pct": 36.67,
    }


def reset_all_data(db: Session, user_id: str = "default_user") -> Dict[str, Any]:
    """Wipes all transactions, salaries, budgets, chat history, and goals for a fresh test slate."""
    db.query(Transaction).filter(Transaction.user_id == user_id).delete()
    db.query(SalaryRecord).filter(SalaryRecord.user_id == user_id).delete()
    db.query(BudgetSetting).filter(BudgetSetting.user_id == user_id).delete()
    db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).delete()
    db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    db.commit()
    return {"status": "success", "message": "All database records have been reset."}
