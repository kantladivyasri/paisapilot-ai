from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, UniqueConstraint
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, default="default_user")
    name = Column(String(100), default="Primary User", nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SalaryRecord(Base):
    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), default="default_user", nullable=False, index=True)
    month = Column(String(7), nullable=False, index=True)  # 'YYYY-MM'
    amount = Column(Float, nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "month", name="uq_user_salary_month"),
    )


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), default="default_user", nullable=False, index=True)
    name = Column(String(50), nullable=False)
    color = Column(String(20), default="#10b981", nullable=False)
    icon = Column(String(30), default="Tag", nullable=False)
    is_essential = Column(Boolean, default=False, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    budget_limit = Column(Float, default=0.0, nullable=False)  # Monthly category budget limit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_category_name"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), default="default_user", nullable=False, index=True)
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(20), nullable=False)  # 'income' or 'expense'
    category = Column(String(50), nullable=False, index=True)
    payment_method = Column(String(30), default="UPI", nullable=False)  # 'UPI', 'Cash', 'Credit Card', 'Debit Card', 'Net Banking', 'Other'
    is_essential = Column(Boolean, default=False, nullable=False)
    date = Column(String(10), nullable=False, index=True)  # 'YYYY-MM-DD'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class BudgetSetting(Base):
    __tablename__ = "budget_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), default="default_user", nullable=False, index=True)
    month = Column(String(7), nullable=False, index=True)  # 'YYYY-MM'
    monthly_income = Column(Float, nullable=False)
    essential_expenses = Column(Float, default=0.0, nullable=False)
    savings_target = Column(Float, default=0.0, nullable=False)
    emergency_fund_target = Column(Float, default=0.0, nullable=False)
    category_limits = Column(Text, nullable=True)  # JSON-encoded dict of category: limit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "month", name="uq_user_budget_month"),
    )


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), default="default_user", nullable=False, index=True)
    name = Column(String(100), nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0, nullable=False)
    target_date = Column(String(10), nullable=False)  # 'YYYY-MM-DD'
    monthly_contribution = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(50), default="default_user", nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    engine = Column(String(30), nullable=True)
    intent = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
