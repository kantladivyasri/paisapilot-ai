import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db, run_migrations_and_seed
from app.models import Category, ChatMessage, SalaryRecord, SavingsGoal, Transaction
from app.schemas import (
    AnalysisResponse,
    BudgetCreate,
    BudgetGenerateRequest,
    BudgetResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    CsvImportResponse,
    ForecastResponse,
    PeriodReportResponse,
    SalaryCreate,
    SalaryResponse,
    SavingsGoalCreate,
    SavingsGoalResponse,
    SavingsGoalUpdate,
    SummaryResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.agents.analyzer import calculate_analysis, calculate_summary
from app.agents.prediction_agent import compute_forecast
from app.agents.budget_agent import generate_budget_plan, get_current_budget, save_or_update_budget
from app.agents.categorizer import categorize_transaction, is_category_essential
from app.agents.orchestrator import route_chat_query
from app.agents.period_analyzer import compute_period_report
from app.agents.salary_service import (
    calculate_salary_dashboard_metrics,
    get_all_salaries,
    get_salary_for_month,
    save_or_update_salary,
)
from app.agents.savings_agent import evaluate_goal
from app.services.csv_import import parse_and_import_csv
from app.services.llm_service import (
    get_gemini_api_key,
    get_gemini_model,
    get_groq_api_key,
    get_groq_model,
    save_env_setting,
)
from app.services.seed_data import reset_all_data, seed_demo_data

load_dotenv()

# Run database migrations and seed default categories/user
run_migrations_and_seed(engine)

app = FastAPI(
    title="Nidhi Pilot AI API",
    description="Intelligent Personal Finance & Expense Management System",
    version="2.0.0",
)

# CORS configuration
origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
origins = [o.strip() for o in origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    groq_key = get_groq_api_key()
    gemini_key = get_gemini_api_key()
    return {
        "status": "ok",
        "app": "Nidhi Pilot AI",
        "tagline": "Understand Your Money. Plan Your Future.",
        "currency": "INR (₹)",
        "llm_active": bool(groq_key or gemini_key),
        "langchain_agent_active": bool(groq_key or gemini_key),
        "framework": "LangChain Tool-Calling Agent",
        "groq_configured": bool(groq_key),
        "groq_model": get_groq_model() if groq_key else None,
        "gemini_configured": bool(gemini_key),
        "gemini_model": get_gemini_model() if gemini_key else None,
    }


# =====================
# Monthly Salary API
# =====================

@app.get("/api/salary", response_model=SalaryResponse)
def get_monthly_salary(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
):
    target_month = month or datetime.now().strftime("%Y-%m")
    record = get_salary_for_month(db, target_month)
    metrics = calculate_salary_dashboard_metrics(db, target_month)

    if not record:
        # Return transient zero salary with live expense metrics
        now = datetime.utcnow()
        return SalaryResponse(
            id=0,
            user_id="default_user",
            month=target_month,
            amount=0.0,
            notes=None,
            created_at=now,
            updated_at=now,
            current_month_salary=0.0,
            total_expenses=metrics["total_expenses"],
            remaining_balance=metrics["remaining_balance"],
            savings_rate=metrics["savings_rate"],
        )

    return SalaryResponse(
        id=record.id,
        user_id=record.user_id,
        month=record.month,
        amount=record.amount,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
        current_month_salary=metrics["current_month_salary"],
        total_expenses=metrics["total_expenses"],
        remaining_balance=metrics["remaining_balance"],
        savings_rate=metrics["savings_rate"],
    )


@app.post("/api/salary", response_model=SalaryResponse)
def set_monthly_salary(
    payload: SalaryCreate,
    db: Session = Depends(get_db),
):
    record = save_or_update_salary(
        db=db,
        month=payload.month,
        amount=payload.amount,
        notes=payload.notes,
    )
    metrics = calculate_salary_dashboard_metrics(db, payload.month)

    return SalaryResponse(
        id=record.id,
        user_id=record.user_id,
        month=record.month,
        amount=record.amount,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
        current_month_salary=metrics["current_month_salary"],
        total_expenses=metrics["total_expenses"],
        remaining_balance=metrics["remaining_balance"],
        savings_rate=metrics["savings_rate"],
    )


@app.get("/api/salaries", response_model=List[SalaryResponse])
def list_salaries(db: Session = Depends(get_db)):
    records = get_all_salaries(db)
    results = []
    for r in records:
        metrics = calculate_salary_dashboard_metrics(db, r.month)
        results.append(
            SalaryResponse(
                id=r.id,
                user_id=r.user_id,
                month=r.month,
                amount=r.amount,
                notes=r.notes,
                created_at=r.created_at,
                updated_at=r.updated_at,
                current_month_salary=r.amount,
                total_expenses=metrics["total_expenses"],
                remaining_balance=metrics["remaining_balance"],
                savings_rate=metrics["savings_rate"],
            )
        )
    return results


# =====================
# Dynamic Categories API
# =====================

@app.get("/api/categories", response_model=List[CategoryResponse])
def get_categories(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
):
    target_month = month or datetime.now().strftime("%Y-%m")
    cats = db.query(Category).filter(Category.user_id == "default_user").all()
    if not cats:
        from app.database import run_migrations_and_seed
        run_migrations_and_seed(db.get_bind())
        cats = db.query(Category).filter(Category.user_id == "default_user").all()

    # Query transaction counts and current month spending
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == "default_user",
            Transaction.date.startswith(target_month),
            Transaction.transaction_type == "expense",
        )
        .all()
    )
    spent_map = {}
    count_map = {}
    for t in txns:
        spent_map[t.category] = spent_map.get(t.category, 0.0) + t.amount
        count_map[t.category] = count_map.get(t.category, 0) + 1

    results = []
    for c in cats:
        results.append(
            CategoryResponse(
                id=c.id,
                user_id=c.user_id,
                name=c.name,
                color=c.color,
                icon=c.icon,
                is_essential=c.is_essential,
                is_default=c.is_default,
                budget_limit=c.budget_limit,
                current_month_spent=round(spent_map.get(c.name, 0.0), 2),
                transaction_count=count_map.get(c.name, 0),
                created_at=c.created_at,
            )
        )
    return results


@app.post("/api/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Category)
        .filter(Category.user_id == "default_user", Category.name == payload.name.strip())
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{payload.name}' already exists.")

    new_cat = Category(
        user_id="default_user",
        name=payload.name.strip(),
        color=payload.color or "#10b981",
        icon=payload.icon or "Tag",
        is_essential=payload.is_essential,
        is_default=False,
        budget_limit=payload.budget_limit or 0.0,
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)
    return CategoryResponse(
        id=new_cat.id,
        user_id=new_cat.user_id,
        name=new_cat.name,
        color=new_cat.color,
        icon=new_cat.icon,
        is_essential=new_cat.is_essential,
        is_default=new_cat.is_default,
        budget_limit=new_cat.budget_limit,
        current_month_spent=0.0,
        transaction_count=0,
        created_at=new_cat.created_at,
    )


@app.put("/api/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id, Category.user_id == "default_user").first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    old_name = cat.name
    if payload.name is not None and payload.name.strip():
        new_name = payload.name.strip()
        if new_name != old_name:
            # Check duplicate name
            duplicate = db.query(Category).filter(
                Category.user_id == "default_user", Category.name == new_name, Category.id != category_id
            ).first()
            if duplicate:
                raise HTTPException(status_code=400, detail=f"Category '{new_name}' already exists.")
            cat.name = new_name
            # Reassign transactions to new name
            db.query(Transaction).filter(
                Transaction.user_id == "default_user", Transaction.category == old_name
            ).update({"category": new_name})

    if payload.color is not None:
        cat.color = payload.color
    if payload.icon is not None:
        cat.icon = payload.icon
    if payload.is_essential is not None:
        cat.is_essential = payload.is_essential
    if payload.budget_limit is not None:
        cat.budget_limit = payload.budget_limit

    db.commit()
    db.refresh(cat)
    return CategoryResponse(
        id=cat.id,
        user_id=cat.user_id,
        name=cat.name,
        color=cat.color,
        icon=cat.icon,
        is_essential=cat.is_essential,
        is_default=cat.is_default,
        budget_limit=cat.budget_limit,
        current_month_spent=0.0,
        transaction_count=0,
        created_at=cat.created_at,
    )


@app.delete("/api/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id, Category.user_id == "default_user").first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    # Reassign any transactions in this category to 'Miscellaneous'
    db.query(Transaction).filter(
        Transaction.user_id == "default_user", Transaction.category == cat.name
    ).update({"category": "Miscellaneous"})

    db.delete(cat)
    db.commit()
    return {"message": f"Category '{cat.name}' deleted successfully."}


# =====================
# Period-Based Tracking Reports API (Daily, Weekly, Monthly, Yearly, Custom)
# =====================

@app.get("/api/reports/period", response_model=PeriodReportResponse)
def get_period_report(
    period_type: str = Query("monthly", description="daily, weekly, monthly, yearly, custom"),
    reference_date: Optional[str] = Query(None, description="Reference date YYYY-MM-DD"),
    target_date: Optional[str] = Query(None, description="Alias for reference date YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date for custom range YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date for custom range YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    valid_types = ["daily", "weekly", "monthly", "yearly", "custom"]
    if period_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"period_type must be one of {valid_types}")

    ref_date = reference_date or target_date
    return compute_period_report(
        db=db,
        period_type=period_type,
        reference_date_str=ref_date,
        start_date_str=start_date,
        end_date_str=end_date,
        user_id="default_user",
    )


# =====================
# Transactions API (with Pagination, Sorting, Search, and Payment Methods)
# =====================

@app.get("/api/transactions")
def get_transactions(
    category: Optional[str] = None,
    transaction_type: Optional[str] = None,
    payment_method: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("date", description="date or amount"),
    sort_order: Optional[str] = Query("desc", description="desc or asc"),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Transaction).filter(Transaction.user_id == "default_user")

    if category and category != "All":
        query = query.filter(Transaction.category == category)
    if transaction_type and transaction_type != "all":
        query = query.filter(Transaction.transaction_type == transaction_type)
    if payment_method and payment_method != "all":
        query = query.filter(Transaction.payment_method == payment_method)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Transaction.description.ilike(search_filter))
            | (Transaction.category.ilike(search_filter))
            | (Transaction.payment_method.ilike(search_filter))
        )

    # Sorting
    if sort_by == "amount":
        order_col = Transaction.amount.desc() if sort_order == "desc" else Transaction.amount.asc()
    else:
        order_col = Transaction.date.desc() if sort_order == "desc" else Transaction.date.asc()

    query = query.order_by(order_col, Transaction.id.desc())

    # If pagination requested
    if page is not None and page_size is not None:
        total_count = query.count()
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [TransactionResponse.model_validate(it) for it in items],
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    # If unpaginated (classic full list)
    items = query.all()
    return [TransactionResponse.model_validate(it) for it in items]


@app.post("/api/transactions", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(txn: TransactionCreate, db: Session = Depends(get_db)):
    category = txn.category
    is_essential = txn.is_essential
    if not category or category == "Uncategorized":
        auto_cat, auto_essential = categorize_transaction(txn.description, txn.transaction_type)
        category = auto_cat
        if not is_essential:
            is_essential = auto_essential
    elif is_category_essential(category):
        is_essential = True

    new_txn = Transaction(
        user_id="default_user",
        description=txn.description.strip(),
        amount=txn.amount,
        transaction_type=txn.transaction_type,
        category=category.strip(),
        payment_method=txn.payment_method or "UPI",
        is_essential=is_essential,
        date=txn.date,
        notes=txn.notes.strip() if txn.notes else None,
    )
    db.add(new_txn)
    db.commit()
    db.refresh(new_txn)
    return new_txn


@app.put("/api/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    updates: TransactionUpdate,
    db: Session = Depends(get_db),
):
    txn = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.user_id == "default_user"
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if updates.description is not None:
        txn.description = updates.description.strip()
    if updates.amount is not None:
        txn.amount = updates.amount
    if updates.transaction_type is not None:
        txn.transaction_type = updates.transaction_type
    if updates.category is not None:
        txn.category = updates.category.strip()
    if updates.payment_method is not None:
        txn.payment_method = updates.payment_method
    if updates.is_essential is not None:
        txn.is_essential = updates.is_essential
    if updates.date is not None:
        txn.date = updates.date
    if updates.notes is not None:
        txn.notes = updates.notes.strip() if updates.notes else None

    txn.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(txn)
    return txn


@app.delete("/api/transactions/{transaction_id}", status_code=status.HTTP_200_OK)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.user_id == "default_user"
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()
    return {"message": f"Transaction {transaction_id} deleted successfully"}


@app.post("/api/transactions/import", response_model=CsvImportResponse)
async def import_transactions_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    content = await file.read()
    try:
        csv_text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            csv_text = content.decode("latin1")
        except Exception:
            raise HTTPException(status_code=400, detail="Unable to decode CSV file")

    return parse_and_import_csv(content=content, filename=file.filename, db=db)


# =====================
# Financial Summary & Spending Analysis API
# =====================

@app.get("/api/summary", response_model=SummaryResponse)
def get_summary(month: Optional[str] = None, db: Session = Depends(get_db)):
    return calculate_summary(db, month)


@app.get("/api/analysis", response_model=AnalysisResponse)
def get_analysis(month: Optional[str] = None, db: Session = Depends(get_db)):
    return calculate_analysis(db, month)


@app.get("/api/analysis/forecast", response_model=ForecastResponse)
def get_expense_forecast(month: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Predicts monthly expenses and end-of-month savings,
    and warns if spending too much on unwanted/discretionary items than regular.
    """
    return compute_forecast(db, month)


# =====================
# Budget Planner API
# =====================

@app.get("/api/budget", response_model=Optional[BudgetResponse])
def get_budget(month: Optional[str] = None, db: Session = Depends(get_db)):
    return get_current_budget(db, month)


@app.post("/api/budget", response_model=BudgetResponse)
def create_or_update_budget(budget: BudgetCreate, db: Session = Depends(get_db)):
    return save_or_update_budget(db, budget)


@app.post("/api/budget/generate", response_model=Dict[str, Any])
def generate_recommended_budget(
    req: BudgetGenerateRequest, db: Session = Depends(get_db)
):
    summary = calculate_summary(db, req.month)
    analysis = calculate_analysis(db, req.month)

    income = req.custom_income if req.custom_income is not None else summary.total_income
    if income <= 0:
        income = summary.current_month_salary if summary.current_month_salary > 0 else 30000.0

    essentials = analysis.essential_spending
    if essentials <= 0:
        essentials = round(income * 0.50, 2)

    savings_target = round(income * ((req.desired_savings_rate or 20.0) / 100.0), 2)
    emergency_target = round(income * ((req.desired_emergency_rate or 10.0) / 100.0), 2)

    plan = generate_budget_plan(
        monthly_income=income,
        essential_expenses=essentials,
        savings_target=savings_target,
        emergency_fund_target=emergency_target,
        month=req.month,
        db=db,
    )
    return plan


# =====================
# Savings Goals API
# =====================

@app.get("/api/goals", response_model=List[SavingsGoalResponse])
def get_savings_goals(db: Session = Depends(get_db)):
    goals = (
        db.query(SavingsGoal)
        .filter(SavingsGoal.user_id == "default_user")
        .order_by(SavingsGoal.created_at.desc())
        .all()
    )
    return [evaluate_goal(g, db) for g in goals]


@app.post("/api/goals", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
def create_savings_goal(goal: SavingsGoalCreate, db: Session = Depends(get_db)):
    new_goal = SavingsGoal(
        user_id="default_user",
        name=goal.name.strip(),
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        monthly_contribution=goal.monthly_contribution,
    )
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)
    return evaluate_goal(new_goal, db)


@app.put("/api/goals/{goal_id}", response_model=SavingsGoalResponse)
def update_savings_goal(goal_id: int, updates: SavingsGoalUpdate, db: Session = Depends(get_db)):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == "default_user"
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if updates.name is not None:
        goal.name = updates.name.strip()
    if updates.target_amount is not None:
        goal.target_amount = updates.target_amount
    if updates.current_amount is not None:
        goal.current_amount = updates.current_amount
    if updates.target_date is not None:
        goal.target_date = updates.target_date
    if updates.monthly_contribution is not None:
        goal.monthly_contribution = updates.monthly_contribution

    goal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(goal)
    return evaluate_goal(goal, db)


@app.delete("/api/goals/{goal_id}", status_code=status.HTTP_200_OK)
def delete_savings_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == "default_user"
    ).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(goal)
    db.commit()
    return {"message": f"Savings goal '{goal.name}' deleted"}


# =====================
# AI Finance Chatbot API
# =====================

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_agent(req: ChatRequest, db: Session = Depends(get_db)):
    return await route_chat_query(req.message, db, req.context_month)


@app.get("/api/chat/history", response_model=List[ChatMessageResponse])
def get_chat_history(db: Session = Depends(get_db)):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == "default_user")
        .order_by(ChatMessage.created_at.asc())
        .limit(50)
        .all()
    )
    return messages


@app.delete("/api/chat/history")
def clear_chat_history(db: Session = Depends(get_db)):
    db.query(ChatMessage).filter(ChatMessage.user_id == "default_user").delete()
    db.commit()
    return {"message": "Chat history cleared"}


# =====================
# Settings & Key Config
# =====================

@app.get("/api/settings")
def get_settings():
    groq_key = get_groq_api_key()
    gemini_key = get_gemini_api_key()
    masked_groq = f"{groq_key[:4]}...{groq_key[-4:]}" if groq_key and len(groq_key) > 8 else ("Configured" if groq_key else None)
    masked_gemini = f"{gemini_key[:4]}...{gemini_key[-4:]}" if gemini_key and len(gemini_key) > 8 else ("Configured" if gemini_key else None)
    return {
        "groq_api_key_configured": bool(groq_key),
        "groq_masked_key": masked_groq,
        "groq_model": get_groq_model(),
        "gemini_api_key_configured": bool(gemini_key),
        "gemini_masked_key": masked_gemini,
        "gemini_model": get_gemini_model(),
    }


@app.post("/api/settings")
def update_settings(payload: Dict[str, str]):
    if "groq_api_key" in payload:
        new_key = payload["groq_api_key"].strip()
        save_env_setting("GROQ_API_KEY", new_key)
    if "groq_model" in payload and payload["groq_model"].strip():
        save_env_setting("GROQ_MODEL", payload["groq_model"].strip())
    if "gemini_api_key" in payload:
        new_gem_key = payload["gemini_api_key"].strip()
        save_env_setting("GEMINI_API_KEY", new_gem_key)
    if "gemini_model" in payload and payload["gemini_model"].strip():
        save_env_setting("GEMINI_MODEL", payload["gemini_model"].strip())

    groq_k = get_groq_api_key()
    gemini_k = get_gemini_api_key()
    return {
        "status": "success",
        "groq_api_key_configured": bool(groq_k),
        "groq_model": get_groq_model(),
        "gemini_api_key_configured": bool(gemini_k),
        "gemini_model": get_gemini_model(),
    }


# =====================
# Demo Data Management
# =====================

@app.post("/api/demo/seed")
def seed_demo(force: bool = False, db: Session = Depends(get_db)):
    return seed_demo_data(db, force=force)


@app.post("/api/demo/reset")
def reset_demo(db: Session = Depends(get_db)):
    return reset_all_data(db)
