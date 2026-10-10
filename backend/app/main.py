import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db, run_migrations_and_seed
from app.models import Category, ChatMessage, EmailAlertLog, MobileAlertLog, RecurringExpense, SalaryRecord, SavingsGoal, Transaction, User
from app.schemas import (
    AlertStatusResponse,
    AnalysisResponse,
    AuthTokenResponse,
    BudgetCreate,
    BudgetGenerateRequest,
    BudgetResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    CheckAndNotifyResponse,
    CsvImportResponse,
    EmailAlertLogResponse,
    EmailGatewayConfigRequest,
    EmailGatewayConfigResponse,
    ForecastResponse,
    ImportAgentCommitRequest,
    ImportAgentCommitResponse,
    ImportAgentPreviewRequest,
    ImportAgentPreviewResponse,
    MobileAlertLogResponse,
    PeriodReportResponse,
    RecurringExpenseCreate,
    RecurringExpenseResponse,
    RecurringExpenseSummaryResponse,
    RecurringExpenseUpdate,
    SalaryCreate,
    SalaryResponse,
    SavingsGoalCreate,
    SavingsGoalResponse,
    SavingsGoalUpdate,
    SendTestEmailRequest,
    SendTestSmsRequest,
    SummaryResponse,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserProfileUpdateRequest,
    SmsGatewayConfigRequest,
    SmsGatewayConfigResponse,
)
from app.services.alert_service import (
    check_and_dispatch_budget_warnings,
    dispatch_sms_alert,
    evaluate_budget_overruns,
    get_sms_gateway_info,
    save_sms_gateway_credentials,
)
from app.services.email_service import (
    dispatch_email_alert,
    get_email_gateway_info,
    save_email_gateway_credentials,
)


from app.services.auth_service import (
    create_access_token,
    generate_user_id,
    get_authenticated_user,
    get_current_user,
    hash_password,
    seed_user_default_categories,
    verify_password,
)
from app.agents.import_agent import TransactionImportAgent
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
# Authentication & User Management API
# =====================

@app.post("/api/auth/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new user account with hashed password credentials,
    provisions default financial categories, and returns a JWT access token.
    """
    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{payload.username}' is already taken. Please choose another.",
        )

    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{payload.email}' is already registered. Please sign in.",
        )

    user_id = generate_user_id()
    hashed_pwd = hash_password(payload.password)
    user = User(
        id=user_id,
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_pwd,
        name=payload.name.strip() if payload.name else payload.username,
        phone_number=payload.phone_number.strip() if payload.phone_number else None,
        currency=payload.currency or "INR",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Automatically provision default categories for the new user
    seed_user_default_categories(db, user.id)

    access_token = create_access_token(user_id=user.id, username=user.username)
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@app.post("/api/auth/login", response_model=AuthTokenResponse)
def login_user(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a user with username or email and password,
    returning a signed JWT access token.
    """
    identifier = payload.username_or_email.strip().lower()
    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user_id=user.id, username=user.username)
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_authenticated_user)):
    """
    Returns the profile of the currently authenticated user.
    """
    return UserResponse.model_validate(current_user)


@app.put("/api/auth/profile", response_model=UserResponse)
@app.put("/api/auth/me", response_model=UserResponse)
def update_user_profile(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """
    Updates authenticated user's profile details: name, email, currency, and optionally password.
    """
    # 1. Update name
    if payload.name is not None and payload.name.strip():
        current_user.name = payload.name.strip()

    # 2. Update currency
    if payload.currency is not None and payload.currency.strip():
        current_user.currency = payload.currency.strip().upper()

    # 3. Update phone_number
    if payload.phone_number is not None:
        current_user.phone_number = payload.phone_number.strip() if payload.phone_number.strip() else None

    # 4. Update email if changed
    if payload.email is not None and payload.email.strip():
        new_email = payload.email.strip().lower()
        if new_email != (current_user.email or "").lower():
            existing_email = db.query(User).filter(User.email == new_email, User.id != current_user.id).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{new_email}' is already in use by another account.",
                )
            current_user.email = new_email

    # 4. Update password if requested
    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your current password is required to set a new password.",
            )
        if not current_user.hashed_password or not verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password. Please try again.",
            )
        current_user.hashed_password = hash_password(payload.new_password)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)



# =====================
# Monthly Salary API
# =====================

@app.get("/api/salary", response_model=SalaryResponse)
def get_monthly_salary(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_month = month or datetime.now().strftime("%Y-%m")
    record = get_salary_for_month(db, target_month, user_id=current_user.id)
    metrics = calculate_salary_dashboard_metrics(db, target_month, user_id=current_user.id)

    if not record:
        # Return transient zero salary with live expense metrics
        now = datetime.utcnow()
        return SalaryResponse(
            id=0,
            user_id=current_user.id,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = save_or_update_salary(
        db=db,
        month=payload.month,
        amount=payload.amount,
        notes=payload.notes,
        user_id=current_user.id,
    )
    metrics = calculate_salary_dashboard_metrics(db, payload.month, user_id=current_user.id)

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
def list_salaries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = get_all_salaries(db, user_id=current_user.id)
    results = []
    for r in records:
        metrics = calculate_salary_dashboard_metrics(db, r.month, user_id=current_user.id)
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_month = month or datetime.now().strftime("%Y-%m")
    cats = db.query(Category).filter(Category.user_id == current_user.id).all()
    if not cats:
        seed_user_default_categories(db, current_user.id)
        cats = db.query(Category).filter(Category.user_id == current_user.id).all()

    # Query transaction counts and current month spending
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == current_user.id,
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
def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Category)
        .filter(Category.user_id == current_user.id, Category.name == payload.name.strip())
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Category '{payload.name}' already exists.")

    new_cat = Category(
        user_id=current_user.id,
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
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = db.query(Category).filter(Category.id == category_id, Category.user_id == current_user.id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    old_name = cat.name
    if payload.name is not None and payload.name.strip():
        new_name = payload.name.strip()
        if new_name != old_name:
            # Check duplicate name
            duplicate = db.query(Category).filter(
                Category.user_id == current_user.id, Category.name == new_name, Category.id != category_id
            ).first()
            if duplicate:
                raise HTTPException(status_code=400, detail=f"Category '{new_name}' already exists.")
            cat.name = new_name
            # Reassign transactions to new name
            db.query(Transaction).filter(
                Transaction.user_id == current_user.id, Transaction.category == old_name
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
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = db.query(Category).filter(Category.id == category_id, Category.user_id == current_user.id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    # Reassign any transactions in this category to 'Miscellaneous'
    db.query(Transaction).filter(
        Transaction.user_id == current_user.id, Transaction.category == cat.name
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
    current_user: User = Depends(get_current_user),
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
        user_id=current_user.id,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)

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
def create_transaction(
    txn: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
        user_id=current_user.id,
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

    # Check budget overruns and automatically dispatch mobile warning SMS
    if new_txn.transaction_type == "expense":
        try:
            check_and_dispatch_budget_warnings(db=db, user=current_user)
        except Exception:
            pass

    return new_txn


@app.put("/api/transactions/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    updates: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.user_id == current_user.id
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
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.user_id == current_user.id
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(txn)
    db.commit()
    return {"message": f"Transaction {transaction_id} deleted successfully"}


@app.post("/api/transactions/import", response_model=CsvImportResponse)
async def import_transactions_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
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

    return parse_and_import_csv(content=content, filename=file.filename, db=db, user_id=current_user.id)


# ==========================================
# Automated Transaction Import Agent API
# ==========================================

@app.post("/api/agents/import-transactions/preview", response_model=ImportAgentPreviewResponse)
def preview_import_agent(
    payload: ImportAgentPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Automated Transaction Import Agent (Preview Mode):
    Extracts transactions, merchants, amounts, dates, and categories from unstructured
    SMS, UPI alerts, or statement text, and audits for potential duplicates.
    """
    return TransactionImportAgent.preview_import(payload.text, db, user_id=current_user.id)


@app.post("/api/agents/import-transactions/commit", response_model=ImportAgentCommitResponse)
def commit_import_agent(
    payload: ImportAgentCommitRequest,
    skip_duplicates: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Automated Transaction Import Agent (Commit Mode):
    Saves user-reviewed transactions into the database, creating categories if needed,
    and updates live monthly balances.
    """
    return TransactionImportAgent.commit_transactions(
        payload.transactions, db, skip_duplicates=skip_duplicates, user_id=current_user.id
    )


@app.post("/api/agents/import-transactions/auto", response_model=ImportAgentCommitResponse)
def auto_import_agent(
    payload: ImportAgentPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Automated Transaction Import Agent (Direct Auto Mode):
    Extracts transactions from raw SMS/statement text and directly commits all non-duplicate items.
    """
    preview = TransactionImportAgent.preview_import(payload.text, db, user_id=current_user.id)
    txns_to_commit = [
        TransactionCreate(
            description=p.description,
            amount=p.amount,
            transaction_type=p.transaction_type,
            category=p.category,
            is_essential=p.is_essential,
            date=p.date,
            notes=f"Auto-imported by Agent ({p.payment_method or 'Online'})",
        )
        for p in preview.parsed_transactions
        if not p.is_duplicate
    ]
    return TransactionImportAgent.commit_transactions(
        txns_to_commit, db, skip_duplicates=True, user_id=current_user.id
    )


# =====================
# Financial Summary & Spending Analysis API
# =====================

@app.get("/api/summary", response_model=SummaryResponse)
def get_summary(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calculate_summary(db, month, user_id=current_user.id)


@app.get("/api/analysis", response_model=AnalysisResponse)
def get_analysis(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return calculate_analysis(db, month, user_id=current_user.id)


@app.get("/api/analysis/forecast", response_model=ForecastResponse)
def get_expense_forecast(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Predicts monthly expenses and end-of-month savings,
    and warns if spending too much on unwanted/discretionary items than regular.
    """
    return compute_forecast(db, month, user_id=current_user.id)


# =====================
# Budget Planner API
# =====================

@app.get("/api/budget", response_model=Optional[BudgetResponse])
def get_budget(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_current_budget(db, month, user_id=current_user.id)


@app.post("/api/budget", response_model=BudgetResponse)
def create_or_update_budget(
    budget: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return save_or_update_budget(db, budget, user_id=current_user.id)


@app.post("/api/budget/generate", response_model=Dict[str, Any])
def generate_recommended_budget(
    req: BudgetGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    summary = calculate_summary(db, req.month, user_id=current_user.id)
    analysis = calculate_analysis(db, req.month, user_id=current_user.id)

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
        user_id=current_user.id,
    )
    return plan


# =====================
# Savings Goals API
# =====================

@app.get("/api/goals", response_model=List[SavingsGoalResponse])
def get_savings_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goals = (
        db.query(SavingsGoal)
        .filter(SavingsGoal.user_id == current_user.id)
        .order_by(SavingsGoal.created_at.desc())
        .all()
    )
    return [evaluate_goal(g, db) for g in goals]


@app.post("/api/goals", response_model=SavingsGoalResponse, status_code=status.HTTP_201_CREATED)
def create_savings_goal(
    goal: SavingsGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_goal = SavingsGoal(
        user_id=current_user.id,
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
def update_savings_goal(
    goal_id: int,
    updates: SavingsGoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == current_user.id
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
def delete_savings_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id, SavingsGoal.user_id == current_user.id
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
async def chat_with_agent(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await route_chat_query(req.message, db, req.context_month, user_id=current_user.id)


@app.get("/api/chat/history", response_model=List[ChatMessageResponse])
def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(50)
        .all()
    )
    return messages


@app.delete("/api/chat/history")
def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).delete()
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
def seed_demo(
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return seed_demo_data(db, force=force, user_id=current_user.id)


@app.post("/api/demo/reset")
def reset_demo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return reset_all_data(db, user_id=current_user.id)


# =====================
# Recurring & Monthly Common Expenses API (Bills, EMIs, Insurance, Subscriptions)
# =====================

@app.get("/api/recurring-expenses", response_model=RecurringExpenseSummaryResponse)
def get_recurring_expenses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(RecurringExpense)
        .filter(RecurringExpense.user_id == current_user.id)
        .order_by(RecurringExpense.due_day.asc())
        .all()
    )
    total_commitment = sum(it.amount for it in items if it.is_active)
    by_type: Dict[str, float] = {}
    for it in items:
        if it.is_active:
            t = it.expense_type.lower()
            by_type[t] = by_type.get(t, 0.0) + it.amount

    return RecurringExpenseSummaryResponse(
        items=[RecurringExpenseResponse.model_validate(it) for it in items],
        total_monthly_commitment=total_commitment,
        active_count=len([it for it in items if it.is_active]),
        breakdown_by_type=by_type,
    )


@app.post("/api/recurring-expenses", response_model=RecurringExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_expense(
    payload: RecurringExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = RecurringExpense(
        user_id=current_user.id,
        title=payload.title.strip(),
        category=payload.category.strip(),
        amount=payload.amount,
        due_day=payload.due_day,
        payment_method=payload.payment_method or "Auto-Debit",
        expense_type=payload.expense_type or "bill",
        is_active=payload.is_active,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return RecurringExpenseResponse.model_validate(item)


@app.put("/api/recurring-expenses/{item_id}", response_model=RecurringExpenseResponse)
def update_recurring_expense(
    item_id: int,
    payload: RecurringExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(RecurringExpense).filter(
        RecurringExpense.id == item_id,
        RecurringExpense.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Recurring expense not found.")

    if payload.title is not None and payload.title.strip():
        item.title = payload.title.strip()
    if payload.category is not None and payload.category.strip():
        item.category = payload.category.strip()
    if payload.amount is not None:
        item.amount = payload.amount
    if payload.due_day is not None:
        item.due_day = payload.due_day
    if payload.payment_method is not None:
        item.payment_method = payload.payment_method
    if payload.expense_type is not None:
        item.expense_type = payload.expense_type
    if payload.is_active is not None:
        item.is_active = payload.is_active
    if payload.notes is not None:
        item.notes = payload.notes.strip() if payload.notes else None

    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return RecurringExpenseResponse.model_validate(item)


@app.delete("/api/recurring-expenses/{item_id}")
def delete_recurring_expense(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(RecurringExpense).filter(
        RecurringExpense.id == item_id,
        RecurringExpense.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Recurring expense not found.")

    db.delete(item)
    db.commit()
    return {"message": f"Recurring expense '{item.title}' removed successfully."}


@app.post("/api/recurring-expenses/{item_id}/log-transaction", response_model=TransactionResponse)
def log_recurring_expense_as_transaction(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    1-click action to record an active recurring bill/EMI as this month's transaction.
    """
    item = db.query(RecurringExpense).filter(
        RecurringExpense.id == item_id,
        RecurringExpense.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Recurring expense not found.")

    now = datetime.utcnow()
    # Format day safely
    day_str = f"{item.due_day:02d}"
    date_str = f"{now.year}-{now.month:02d}-{day_str}"

    txn = Transaction(
        user_id=current_user.id,
        description=f"{item.title} ({item.expense_type.upper()})",
        amount=item.amount,
        transaction_type="expense",
        category=item.category,
        payment_method=item.payment_method,
        is_essential=True,
        date=date_str,
        notes=f"Auto-logged from recurring {item.expense_type}. {item.notes or ''}".strip(),
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    # Check budget overrun and trigger mobile alert
    try:
        check_and_dispatch_budget_warnings(db=db, user=current_user)
    except Exception:
        pass

    return TransactionResponse.model_validate(txn)


# =====================
# Mobile SMS Alerts & Budget Overrun Warnings API
# =====================

@app.get("/api/alerts/status", response_model=AlertStatusResponse)
def get_alert_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns current budget overrun warnings, linked mobile status,
    and recent SMS alerts sent.
    """
    warnings = evaluate_budget_overruns(db=db, user_id=current_user.id)
    recent_logs = (
        db.query(MobileAlertLog)
        .filter(MobileAlertLog.user_id == current_user.id)
        .order_by(MobileAlertLog.dispatched_at.desc())
        .limit(10)
        .all()
    )
    recent_email_logs = (
        db.query(EmailAlertLog)
        .filter(EmailAlertLog.user_id == current_user.id)
        .order_by(EmailAlertLog.dispatched_at.desc())
        .limit(10)
        .all()
    )
    return AlertStatusResponse(
        has_phone=bool(current_user.phone_number),
        phone_number=current_user.phone_number,
        has_email=bool(current_user.email),
        email=current_user.email,
        is_over_budget=len(warnings) > 0,
        warning_count=len(warnings),
        warnings=warnings,
        recent_alerts=[MobileAlertLogResponse.model_validate(l) for l in recent_logs],
        recent_email_alerts=[EmailAlertLogResponse.model_validate(l) for l in recent_email_logs],
    )



@app.post("/api/alerts/check-and-notify", response_model=CheckAndNotifyResponse)
def check_and_notify_user(
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Checks active budget plan vs expenses and automatically dispatches SMS warning
    to the user's mobile number if any budget limit is breached.
    """
    if not current_user.phone_number:
        warnings = evaluate_budget_overruns(db=db, user_id=current_user.id)
        return CheckAndNotifyResponse(
            triggered=len(warnings) > 0,
            alerts_sent=0,
            messages=["User does not have a linked mobile number. Please add phone number in profile."],
        )

    dispatched = check_and_dispatch_budget_warnings(db=db, user=current_user, force=force)
    return CheckAndNotifyResponse(
        triggered=len(dispatched) > 0,
        alerts_sent=len(dispatched),
        messages=[l.message for l in dispatched],
    )


@app.post("/api/alerts/send-test")
def send_test_sms_alert(
    payload: Optional[SendTestSmsRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sends an instant verification SMS to test mobile alert connectivity.
    """
    target_phone = (payload.phone_number if payload and payload.phone_number else current_user.phone_number)
    if not target_phone or not target_phone.strip():
        raise HTTPException(
            status_code=400,
            detail="No mobile phone number provided. Please enter a valid mobile number.",
        )

    # Temporarily assign phone if testing before saving profile
    if not current_user.phone_number:
        current_user.phone_number = target_phone.strip()

    title = "✅ Nidhi Pilot Mobile Alerts Activated"
    message = (
        f"Hello {current_user.name or current_user.username}! Your mobile number ({target_phone}) "
        f"is now connected to Nidhi Pilot AI. You will receive instant warnings whenever your "
        f"expenses exceed your budget plan or monthly limits."
    )
    try:

        log = dispatch_sms_alert(
            db=db,
            user=current_user,
            alert_type="test_verification",
            title=title,
            message=message,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "success",
        "message": f"Real test alert dispatched to {target_phone} via {log.provider}!",
        "log": MobileAlertLogResponse.model_validate(log),
    }


@app.get("/api/alerts/gateway-config", response_model=SmsGatewayConfigResponse)
def get_gateway_configuration(
    current_user: User = Depends(get_current_user),
):
    """
    Returns current SMS Gateway configuration status.
    """
    info = get_sms_gateway_info()
    return SmsGatewayConfigResponse(
        active_provider=info["active_provider"],
        is_configured=info["is_configured"],
        fast2sms_configured=info["fast2sms_configured"],
        twilio_configured=info["twilio_configured"],
        fast2sms_masked=info["fast2sms_masked"],
        twilio_sid_masked=info["twilio_sid_masked"],
        twilio_from=info["twilio_from"],
        message="Gateway status retrieved successfully.",
    )


@app.post("/api/alerts/gateway-config", response_model=SmsGatewayConfigResponse)
def update_gateway_configuration(
    payload: SmsGatewayConfigRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Updates and persists SMS Gateway credentials (Fast2SMS or Twilio).
    """
    if payload.provider == "fast2sms":
        if not payload.fast2sms_api_key or not payload.fast2sms_api_key.strip():
            raise HTTPException(status_code=400, detail="Fast2SMS API Key cannot be empty.")
        save_sms_gateway_credentials(
            provider="fast2sms",
            fast2sms_api_key=payload.fast2sms_api_key.strip(),
        )
    elif payload.provider == "twilio":
        if not payload.twilio_account_sid or not payload.twilio_auth_token or not payload.twilio_phone_number:
            raise HTTPException(
                status_code=400,
                detail="Twilio requires Account SID, Auth Token, and From Phone Number.",
            )
        save_sms_gateway_credentials(
            provider="twilio",
            twilio_account_sid=payload.twilio_account_sid.strip(),
            twilio_auth_token=payload.twilio_auth_token.strip(),
            twilio_phone_number=payload.twilio_phone_number.strip(),
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported SMS provider.")

    info = get_sms_gateway_info()
    return SmsGatewayConfigResponse(
        active_provider=info["active_provider"],
        is_configured=info["is_configured"],
        fast2sms_configured=info["fast2sms_configured"],
        twilio_configured=info["twilio_configured"],
        fast2sms_masked=info["fast2sms_masked"],
        twilio_sid_masked=info["twilio_sid_masked"],
        twilio_from=info["twilio_from"],
        message=f"{info['active_provider']} SMS Gateway configured successfully!",
    )


@app.get("/api/alerts/logs", response_model=List[MobileAlertLogResponse])
def get_alert_logs(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(MobileAlertLog)
        .filter(MobileAlertLog.user_id == current_user.id)
        .order_by(MobileAlertLog.dispatched_at.desc())
        .limit(limit)
        .all()
    )
    return [MobileAlertLogResponse.model_validate(l) for l in logs]


@app.post("/api/alerts/send-test-email")
def send_test_email_alert(
    payload: Optional[SendTestEmailRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sends an instant verification email to test email alert delivery.
    """
    target_email = (payload.email if payload and payload.email else current_user.email)
    if not target_email or not target_email.strip():
        raise HTTPException(
            status_code=400,
            detail="No email address provided. Please update your profile with a valid email.",
        )

    title = "✅ Nidhi Pilot Email Alert System Activated"
    message = (
        f"Hello {current_user.name or current_user.username}! Your email address ({target_email}) "
        f"is now connected to Nidhi Pilot AI. You will receive real-time financial health alerts and "
        f"warnings whenever your expenses exceed your budget plan or category limits."
    )
    try:
        log = dispatch_email_alert(
            db=db,
            user=current_user,
            alert_type="test_verification",
            title=title,
            message=message,
            allow_in_app_fallback=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    is_live = log.status == "delivered" and "SMTP Live" in (log.provider or "")
    msg_status = "success"
    msg_text = (
        f"Real test email dispatched directly to {target_email} via {log.provider}!"
        if is_live
        else f"Alert email dispatched & delivered to your In-App Alert Inbox! ({log.error_message or 'In-App Mode'})"
    )

    return {
        "status": msg_status,
        "message": msg_text,
        "delivery_mode": "live_smtp" if is_live else "in_app",
        "log": EmailAlertLogResponse.model_validate(log),
    }


@app.get("/api/alerts/email-config", response_model=EmailGatewayConfigResponse)
def get_email_gateway_configuration(
    current_user: User = Depends(get_current_user),
):
    """
    Returns current Email Gateway (SMTP) status.
    """
    info = get_email_gateway_info()
    return EmailGatewayConfigResponse(
        is_configured=info["is_configured"],
        provider=info["provider"],
        smtp_host=info["smtp_host"],
        smtp_port=info["smtp_port"],
        smtp_user=info["smtp_user"],
        smtp_user_masked=info["smtp_user_masked"],
        smtp_from=info["smtp_from"],
        smtp_tls=info["smtp_tls"],
        message="Email Gateway status retrieved.",
    )


@app.post("/api/alerts/email-config", response_model=EmailGatewayConfigResponse)
def update_email_gateway_configuration(
    payload: EmailGatewayConfigRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Updates and persists SMTP credentials (Gmail, Outlook, Custom SMTP).
    """
    if not payload.smtp_host or not payload.smtp_user or not payload.smtp_password:
        raise HTTPException(status_code=400, detail="SMTP Host, User, and Password are required.")

    save_email_gateway_credentials(
        smtp_host=payload.smtp_host.strip(),
        smtp_port=payload.smtp_port,
        smtp_user=payload.smtp_user.strip(),
        smtp_password=payload.smtp_password.strip(),
        smtp_from=payload.smtp_from.strip() if payload.smtp_from else payload.smtp_user.strip(),
        smtp_tls=payload.smtp_tls,
    )
    info = get_email_gateway_info()
    return EmailGatewayConfigResponse(
        is_configured=info["is_configured"],
        provider=info["provider"],
        smtp_host=info["smtp_host"],
        smtp_port=info["smtp_port"],
        smtp_user=info["smtp_user"],
        smtp_user_masked=info["smtp_user_masked"],
        smtp_from=info["smtp_from"],
        smtp_tls=info["smtp_tls"],
        message=f"{info['provider']} SMTP configured successfully!",
    )


@app.get("/api/alerts/email-logs", response_model=List[EmailAlertLogResponse])
def get_email_alert_logs(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(EmailAlertLog)
        .filter(EmailAlertLog.user_id == current_user.id)
        .order_by(EmailAlertLog.dispatched_at.desc())
        .limit(limit)
        .all()
    )
    return [EmailAlertLogResponse.model_validate(l) for l in logs]




