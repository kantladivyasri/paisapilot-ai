from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# =====================
# Salary Schemas
# =====================

class SalaryCreate(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format")
    amount: float = Field(..., gt=0, description="Monthly salary must be strictly positive")
    notes: Optional[str] = Field(None, max_length=255)

    @field_validator("amount")
    @classmethod
    def validate_positive_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Salary amount must be greater than zero")
        return round(v, 2)


class SalaryUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    notes: Optional[str] = Field(None, max_length=255)

    @field_validator("amount")
    @classmethod
    def validate_positive_amount(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Salary amount must be greater than zero")
        return round(v, 2) if v is not None else None


class SalaryResponse(BaseModel):
    id: int
    user_id: str
    month: str
    amount: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    # Dynamically calculated fields for the month
    current_month_salary: float = 0.0
    total_expenses: float = 0.0
    remaining_balance: float = 0.0
    savings_rate: float = 0.0
    model_config = ConfigDict(from_attributes=True)


# =====================
# Category Schemas
# =====================

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field("#10b981", max_length=20)
    icon: str = Field("Tag", max_length=30)
    is_essential: bool = False
    budget_limit: float = Field(0.0, ge=0)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    icon: Optional[str] = Field(None, max_length=30)
    is_essential: Optional[bool] = None
    budget_limit: Optional[float] = Field(None, ge=0)


class CategoryResponse(CategoryBase):
    id: int
    user_id: str
    is_default: bool
    current_month_spent: float = 0.0
    transaction_count: int = 0
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# =====================
# Transaction Schemas
# =====================

class TransactionBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0, description="Amount must be strictly positive")
    transaction_type: Literal["income", "expense"]
    category: str = Field(..., min_length=1, max_length=50)
    payment_method: str = Field("UPI", max_length=30)
    is_essential: bool = False
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date in YYYY-MM-DD format")
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_positive_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[float] = Field(None, gt=0)
    transaction_type: Optional[Literal["income", "expense"]] = None
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    payment_method: Optional[str] = Field(None, max_length=30)
    is_essential: Optional[bool] = None
    date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_positive_amount(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2) if v is not None else None


class TransactionResponse(TransactionBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class PaginatedTransactionsResponse(BaseModel):
    items: List[TransactionResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


# =====================
# Analytics & Reports
# =====================

class CategorySpend(BaseModel):
    category: str
    amount: float
    percentage: float
    is_essential: bool
    transaction_count: int
    color: Optional[str] = None
    budget_limit: Optional[float] = 0.0
    budget_remaining: Optional[float] = None
    budget_status: Optional[str] = "normal"  # "normal" | "warning" | "exceeded"


class SummaryResponse(BaseModel):
    total_income: float
    total_expenses: float
    available_balance: float
    savings_rate: float
    current_month_salary: float = 0.0
    currency: str = "INR"
    currency_symbol: str = "₹"
    transaction_count: int
    period: str
    top_categories: List[CategorySpend]
    budget_utilization_percent: Optional[float] = None
    alerts: List[str] = []


class MonthComparison(BaseModel):
    current_month: str
    previous_month: Optional[str] = None
    income_change: Optional[float] = None
    expense_change: Optional[float] = None
    savings_change: Optional[float] = None
    has_sufficient_data: bool


class AnomalyItem(BaseModel):
    category: str
    description: str
    amount: float
    reason: str


class RecommendationItem(BaseModel):
    title: str
    category: str
    impact: str
    action: str
    potential_savings: float


class AnalysisResponse(BaseModel):
    category_breakdown: List[CategorySpend]
    largest_categories: List[CategorySpend]
    essential_spending: float
    discretionary_spending: float
    essential_percentage: float
    discretionary_percentage: float
    month_over_month: MonthComparison
    budget_overruns: List[Dict[str, Any]]
    anomalies: List[AnomalyItem]
    recommendations: List[RecommendationItem]


# =====================
# Prediction & Forecasting Schemas (Monthly Expenses & Savings, Unwanted Spending)
# =====================

class UnwantedSpendingAlert(BaseModel):
    category: str
    is_essential: bool
    current_spent: float
    regular_baseline: float
    projected_spent: float
    excess_amount: float
    excess_percentage: float
    severity: Literal["warning", "critical"]
    message: str
    recommendation: str


class ForecastResponse(BaseModel):
    month: str
    days_passed: int
    days_remaining: int
    total_days: int
    current_expenses: float
    current_income: float
    current_savings: float
    projected_expenses: float
    projected_savings: float
    projected_savings_rate: float
    projected_status: Literal["healthy", "caution", "deficit_risk"]
    daily_spending_pace: float
    regular_daily_baseline: float
    unwanted_spending_alerts: List[UnwantedSpendingAlert]
    total_unwanted_spent: float
    projected_unwanted_spent: float
    regular_unwanted_baseline: float
    is_overspending_on_unwanted: bool
    overspending_summary: str


# =====================
# Period-Based Reports (Daily, Weekly, Monthly, Yearly, Custom)
# =====================

class PeriodSummary(BaseModel):
    start_date: str
    end_date: str
    period_label: str
    total_income: float
    total_expenses: float
    remaining_balance: float
    savings_rate: float
    transaction_count: int
    category_breakdown: List[CategorySpend]


class PeriodComparison(BaseModel):
    previous_expenses: float
    expense_change_amount: float
    expense_change_percent: float
    previous_income: float
    income_change_amount: float
    increased_categories: List[Dict[str, Any]]
    decreased_categories: List[Dict[str, Any]]


class DailyTrendPoint(BaseModel):
    date: str
    label: str
    expenses: float
    income: float


class PeriodReportResponse(BaseModel):
    period_type: str  # 'daily' | 'weekly' | 'monthly' | 'yearly' | 'custom'
    current_period: PeriodSummary
    previous_period: PeriodSummary
    comparison: PeriodComparison
    trends: List[DailyTrendPoint]


# =====================
# Budget Planner Schemas
# =====================

class BudgetBase(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Month in YYYY-MM format")
    monthly_income: float = Field(..., ge=0)
    essential_expenses: float = Field(0.0, ge=0)
    savings_target: float = Field(0.0, ge=0)
    emergency_fund_target: float = Field(0.0, ge=0)
    category_limits: Optional[Dict[str, float]] = None


class BudgetCreate(BudgetBase):
    pass


class BudgetResponse(BudgetBase):
    id: int
    discretionary_allowance: float
    unallocated_balance: float
    is_balanced: bool
    deficit_amount: float
    deficit_warning: Optional[str] = None
    recovery_plan: Optional[List[str]] = None
    category_progress: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class BudgetGenerateRequest(BaseModel):
    month: Optional[str] = None
    custom_income: Optional[float] = None
    desired_savings_rate: Optional[float] = Field(20.0, ge=0, le=100)
    desired_emergency_rate: Optional[float] = Field(10.0, ge=0, le=100)


# =====================
# Savings Goals Schemas
# =====================

class SavingsGoalBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    target_amount: float = Field(..., gt=0)
    current_amount: float = Field(0.0, ge=0)
    target_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    monthly_contribution: float = Field(0.0, ge=0)


class SavingsGoalCreate(SavingsGoalBase):
    pass


class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    target_amount: Optional[float] = Field(None, gt=0)
    current_amount: Optional[float] = Field(None, ge=0)
    target_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    monthly_contribution: Optional[float] = Field(None, ge=0)


class SavingsGoalResponse(SavingsGoalBase):
    id: int
    progress_percentage: float
    remaining_amount: float
    estimated_months_to_complete: Optional[float] = None
    is_realistic: bool
    feasibility_notes: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# =====================
# Chat & Message Schemas
# =====================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    context_month: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    engine: Literal["groq", "gemini", "ollama", "deterministic"]
    engine_name: str
    intent: str
    structured_data: Optional[Dict[str, Any]] = None
    suggested_prompts: List[str] = []


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    engine: Optional[str] = None
    intent: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# =====================
# CSV Import Schemas
# =====================

class CsvImportRowError(BaseModel):
    row_number: int
    raw_data: Dict[str, Any]
    error: str


class CsvImportDuplicateWarning(BaseModel):
    row_number: int
    description: str
    amount: float
    date: str
    warning: str


class CsvImportResponse(BaseModel):
    total_rows_processed: int
    imported_count: int
    duplicate_warning_count: int
    error_count: int
    warnings: List[CsvImportDuplicateWarning]
    errors: List[CsvImportRowError]
    message: str
