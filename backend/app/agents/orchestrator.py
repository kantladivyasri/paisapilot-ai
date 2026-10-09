import calendar
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.agents.analyzer import calculate_analysis, calculate_summary
from app.agents.budget_agent import get_current_budget
from app.agents.period_analyzer import compute_period_report
from app.agents.prediction_agent import compute_forecast
from app.agents.salary_service import calculate_salary_dashboard_metrics, get_salary_for_month
from app.agents.savings_agent import evaluate_goal
from app.models import Category, ChatMessage, SalaryRecord, SavingsGoal, Transaction
from app.schemas import ChatResponse
from app.services.llm_service import (
    generate_gemini_response,
    generate_groq_response,
    generate_ollama_response,
    get_gemini_api_key,
    get_gemini_model,
    get_groq_api_key,
    get_groq_model,
)

MONTH_MAP = {
    "january": "01", "jan": "01",
    "february": "02", "feb": "02",
    "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "may": "05",
    "june": "06", "jun": "06",
    "july": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sep": "09", "sept": "09",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12",
}


def extract_amount_from_query(query: str) -> Optional[float]:
    """Extracts monetary amount mentioned in user query (e.g. ₹2000, 15,000, 2000 rs, 2k, 5,000)."""
    clean_query = query.replace(",", "")
    match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(k|rupees|rs\.?|bucks)?\b", clean_query, re.IGNORECASE)
    if match:
        try:
            val = float(match.group(1))
            suffix = (match.group(2) or "").lower()
            if suffix == "k":
                val *= 1000
            if val > 0:
                return val
        except (ValueError, IndexError):
            pass

    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", clean_query)
    for n in numbers:
        try:
            val = float(n)
            if val > 0 and val != 2024 and val != 2025 and val != 2026:
                return val
        except ValueError:
            continue
    return None


def extract_month_from_query(query: str) -> Optional[str]:
    """Extracts YYYY-MM if a specific month name is mentioned in the query."""
    q = query.lower()
    current_year = datetime.now().year
    for name, month_num in MONTH_MAP.items():
        if re.search(rf"\b{name}\b", q):
            # Check if a 4-digit year is also in query
            year_match = re.search(r"\b(20\d\d)\b", q)
            year = year_match.group(1) if year_match else str(current_year)
            return f"{year}-{month_num}"
    return None


def extract_category_from_query(query: str, available_categories: List[str]) -> Optional[str]:
    """Matches any existing category name from the query."""
    q = query.lower()
    for cat in available_categories:
        if cat.lower() in q:
            return cat
    # Common aliases
    if "food" in q or "dining" in q or "eating" in q or "swiggy" in q or "zomato" in q:
        for cat in available_categories:
            if "food" in cat.lower():
                return cat
    if "rent" in q or "housing" in q or "flat" in q:
        for cat in available_categories:
            if "rent" in cat.lower():
                return cat
    if "groceries" in q or "grocery" in q or "ration" in q or "d-mart" in q:
        for cat in available_categories:
            if "grocer" in cat.lower():
                return cat
    if "shop" in q or "clothes" in q or "amazon" in q or "myntra" in q:
        for cat in available_categories:
            if "shop" in cat.lower():
                return cat
    return None


def classify_intent(query: str) -> str:
    """Classifies user question into structured financial intent."""
    q = query.lower()
    if any(k in q for k in ["predict", "forecast", "projected", "how much will i spend", "end of the month", "by month-end", "how much will i save"]):
        return "predict_forecast"
    elif any(k in q for k in ["unwanted", "too much on unwanted", "unwanted things", "more than regular", "spending more than regular", "wasteful"]):
        return "unwanted_spending"
    elif any(k in q for k in ["this week", "weekly", "spend this week", "past 7 days"]):
        return "week_spending"
    elif any(k in q for k in ["this year", "yearly", "total expenses for this year", "spent this year"]):
        return "yearly_expenses"
    elif any(k in q for k in ["compare", "vs last month", "compared to last month", "month over month"]):
        return "compare_months"
    elif any(k in q for k in ["left from my salary", "salary left", "remaining from salary"]):
        return "salary_balance"
    elif any(k in q for k in ["left", "balance", "how much money do i have left", "remaining"]):
        return "balance_query"
    elif any(k in q for k in ["reduce", "cut down", "which expenses can i reduce", "cut expenses"]):
        return "reduce_expenses"
    elif any(k in q for k in ["too much on", "overspending on", "spending too much"]):
        return "category_audit"
    elif any(k in q for k in ["how can i save", "save ₹", "save 5", "save 1", "saving plan"]):
        return "save_money"
    elif any(k in q for k in ["where am i spending", "biggest expense", "top expense", "spending the most", "largest category"]):
        return "top_spending"
    elif any(k in q for k in ["afford", "can i buy", "can i spend", "purchase", "additional"]):
        return "simulate_purchase"
    elif any(k in q for k in ["budget", "exceeding", "over budget", "limits", "overrun"]):
        return "budget_status"
    elif any(k in q for k in ["goal", "goals", "milestone", "reach my goal"]):
        return "goals_inquiry"
    elif any(m in q for m in MONTH_MAP.keys()):
        return "category_month_query"
    return "general"


def execute_deterministic_tool(
    intent: str,
    query: str,
    db: Session,
    user_id: str = "default_user",
    context_month: Optional[str] = None,
) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Executes real database queries and calculations for the requested financial intent.
    Returns (reply_text, suggested_prompts, structured_data)
    """
    current_m = context_month or datetime.now().strftime("%Y-%m")
    categories = [c.name for c in db.query(Category).filter(Category.user_id == user_id).all()]
    if not categories:
        categories = ["Food & Dining", "Rent & Housing", "Groceries", "Transportation", "Shopping", "Entertainment"]

    suggested_prompts = [
        "How much money did I spend this week?",
        "What is my biggest expense category this month?",
        "How much money do I have left from my salary?",
        "Compare my spending this month with last month.",
    ]

    # 1. Week Spending
    if intent == "week_spending":
        week_report = compute_period_report(db, period_type="weekly", user_id=user_id)
        cur = week_report.current_period
        comp = week_report.comparison
        
        reply = f"You have spent **₹{cur.total_expenses:,.2f}** this week across {cur.transaction_count} transaction(s)."
        if comp.previous_expenses > 0:
            if comp.expense_change_amount > 0:
                reply += f" That is an increase of **₹{comp.expense_change_amount:,.2f}** (+{comp.expense_change_percent}%) compared to last week (₹{comp.previous_expenses:,.2f})."
            else:
                reply += f" That is a decrease of **₹{abs(comp.expense_change_amount):,.2f}** ({comp.expense_change_percent}%) compared to last week (₹{comp.previous_expenses:,.2f})."
        if cur.category_breakdown:
            top = cur.category_breakdown[0]
            reply += f" Your highest spending category this week was **{top.category}** at **₹{top.amount:,.2f}** ({top.percentage}%)."
        return reply, suggested_prompts, {"weekly": cur.model_dump()}

    # 2. Yearly Expenses
    elif intent == "yearly_expenses":
        year_report = compute_period_report(db, period_type="yearly", user_id=user_id)
        cur = year_report.current_period
        reply = (
            f"Total recorded expenses for **{cur.period_label}** are **₹{cur.total_expenses:,.2f}** across {cur.transaction_count} transactions. "
            f"Total recorded income is **₹{cur.total_income:,.2f}**, leaving a cumulative balance of **₹{cur.remaining_balance:,.2f}** "
            f"(Annual savings rate: {cur.savings_rate}%)."
        )
        return reply, suggested_prompts, {"yearly": cur.model_dump()}

    # 3. Remaining Salary / Balance
    elif intent in ("salary_balance", "balance_query"):
        metrics = calculate_salary_dashboard_metrics(db, current_m, user_id=user_id)
        sal = metrics["current_month_salary"]
        exp = metrics["total_expenses"]
        rem = metrics["remaining_balance"]
        rate = metrics["savings_rate"]

        if sal == 0:
            reply = (
                f"You haven't recorded a salary for **{current_m}** yet. "
                f"You have logged **₹{exp:,.2f}** in expenses so far. "
                f"Please set your monthly salary in the Salary section to track your live remaining balance."
            )
        else:
            reply = (
                f"You have **₹{rem:,.2f}** remaining from your monthly salary of **₹{sal:,.2f}**, "
                f"after **₹{exp:,.2f}** in recorded expenses. This represents a current savings rate of **{rate}%**."
            )
        return reply, suggested_prompts, metrics

    # 4. Compare This Month With Last Month
    elif intent == "compare_months":
        month_report = compute_period_report(db, period_type="monthly", user_id=user_id)
        cur = month_report.current_period
        prev = month_report.previous_period
        comp = month_report.comparison

        if prev.total_expenses == 0:
            reply = (
                f"In **{cur.period_label}**, your recorded expenses are **₹{cur.total_expenses:,.2f}**. "
                f"There are no expense records for {prev.period_label} to establish a reliable month-over-month comparison."
            )
        else:
            change_txt = "increased" if comp.expense_change_amount > 0 else "decreased"
            reply = (
                f"### Spending Comparison ({cur.period_label} vs {prev.period_label})\n\n"
                f"- **{cur.period_label}:** ₹{cur.total_expenses:,.2f}\n"
                f"- **{prev.period_label}:** ₹{prev.total_expenses:,.2f}\n\n"
                f"Spending **{change_txt} by ₹{abs(comp.expense_change_amount):,.2f}** ({comp.expense_change_percent}%) compared to last month."
            )
            if comp.increased_categories:
                top_inc = comp.increased_categories[0]
                reply += f" Main driver: **{top_inc['category']}** (+₹{top_inc['increase_amount']:,.2f})."
        return reply, suggested_prompts, month_report.model_dump()

    # 5. Category Month Query (e.g. "How much did I spend on food in September?")
    elif intent == "category_month_query":
        target_m = extract_month_from_query(query) or current_m
        matched_cat = extract_category_from_query(query, categories)

        query_txns = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "expense",
            Transaction.date.startswith(target_m),
        )
        if matched_cat:
            query_txns = query_txns.filter(Transaction.category == matched_cat)

        txns = query_txns.all()
        spent = sum(t.amount for t in txns)

        try:
            month_label = datetime.strptime(target_m, "%Y-%m").strftime("%B %Y")
        except Exception:
            month_label = target_m

        if matched_cat:
            reply = f"In **{month_label}**, you spent **₹{spent:,.2f}** on **{matched_cat}** across {len(txns)} transaction(s)."
        else:
            reply = f"In **{month_label}**, your total recorded expenses were **₹{spent:,.2f}** across {len(txns)} transaction(s)."
        return reply, suggested_prompts, {"month": target_m, "category": matched_cat, "amount": spent}

    # 6. Category Audit (e.g. "Am I spending too much on shopping?")
    elif intent == "category_audit":
        matched_cat = extract_category_from_query(query, categories) or "Shopping"
        summary = calculate_summary(db, current_m, user_id=user_id)
        cat_item = next((c for c in summary.top_categories if c.category.lower() == matched_cat.lower()), None)
        
        if not cat_item:
            reply = f"You haven't recorded any expenses under **{matched_cat}** for {summary.period}."
            return reply, suggested_prompts, {}

        reply = f"You have spent **₹{cat_item.amount:,.2f}** on **{cat_item.category}** ({cat_item.percentage}% of your expenses) in {summary.period}."
        if cat_item.budget_limit > 0:
            if cat_item.amount > cat_item.budget_limit:
                over = cat_item.amount - cat_item.budget_limit
                reply += f" This exceeds your configured limit of ₹{cat_item.budget_limit:,.2f} by ₹{over:,.2f}."
            else:
                rem = cat_item.budget_limit - cat_item.amount
                reply += f" This is within your monthly limit of ₹{cat_item.budget_limit:,.2f} (₹{rem:,.2f} remaining)."
        return reply, suggested_prompts, cat_item.model_dump()

    # 7. How Can I Save Money
    elif intent in ("save_money", "reduce_expenses"):
        target_save = extract_amount_from_query(query) or 2000.0
        analysis = calculate_analysis(db, current_m, user_id=user_id)
        summary = calculate_summary(db, current_m, user_id=user_id)

        discretionary_cats = [c for c in summary.top_categories if not c.is_essential]

        if not discretionary_cats:
            reply = (
                f"You have minimal discretionary lifestyle expenses logged for {summary.period}. "
                f"To save ₹{target_save:,.2f}, consider auditing fixed commitments or exploring income avenues."
            )
        else:
            reply = (
                f"To save **₹{target_save:,.2f}** this month:\n\n"
                f"Your current discretionary spend is **₹{analysis.discretionary_spending:,.2f}** ({analysis.discretionary_percentage}% of expenses).\n"
            )
            remaining_to_trim = target_save
            for idx, c in enumerate(discretionary_cats[:3], 1):
                trim_target = min(round(c.amount * 0.40, 2), remaining_to_trim)
                reply += f"- **Reduce {c.category}:** Trim ~₹{trim_target:,.2f} (current spend: ₹{c.amount:,.2f}).\n"
                remaining_to_trim -= trim_target
                if remaining_to_trim <= 0:
                    break
        return reply, suggested_prompts, {"target_save": target_save, "discretionary_spending": analysis.discretionary_spending}

    # 8. Simulate Purchase
    elif intent == "simulate_purchase":
        cost = extract_amount_from_query(query) or 2000.0
        summary = calculate_summary(db, current_m, user_id=user_id)
        balance = summary.available_balance

        new_balance = round(balance - cost, 2)
        new_expenses = round(summary.total_expenses + cost, 2)
        new_rate = (
            round(((summary.total_income - new_expenses) / summary.total_income * 100.0), 2)
            if summary.total_income > 0
            else 0.0
        )

        if new_balance >= 0:
            reply = (
                f"Yes, you can afford this **₹{cost:,.2f}** expense. "
                f"Your current surplus is **₹{balance:,.2f}**; after this purchase, your remaining balance will be "
                f"**₹{new_balance:,.2f}** (Projected savings rate: {new_rate}%)."
            )
        else:
            shortfall = abs(new_balance)
            reply = (
                f"Caution: A purchase of **₹{cost:,.2f}** exceeds your available funds by **₹{shortfall:,.2f}**. "
                f"Your current balance is ₹{balance:,.2f}. Postponing this expense is recommended to avoid a deficit."
            )
        return reply, suggested_prompts, {"cost": cost, "projected_balance": new_balance}

    # 9. Top Spending
    elif intent == "top_spending":
        summary = calculate_summary(db, current_m, user_id=user_id)
        if not summary.top_categories:
            return "You haven't recorded any expenses yet for this period.", suggested_prompts, {}

        top_cat = summary.top_categories[0]
        reply = f"Your biggest expense category this month is **{top_cat.category}**, with a total of **₹{top_cat.amount:,.2f}** ({top_cat.percentage}% of total expenses)."
        if len(summary.top_categories) > 1:
            second = summary.top_categories[1]
            reply += f" Followed by **{second.category}** at **₹{second.amount:,.2f}** ({second.percentage}%)."
        return reply, suggested_prompts, summary.model_dump()

    # 10. Prediction & Monthly Forecast Tool (Requirement 4)
    elif intent == "predict_forecast":
        fc = compute_forecast(db, current_m, user_id=user_id)
        return fc.forecast_presentation, suggested_prompts, fc.model_dump()

    # 11. Unwanted / Discretionary Overspending Warning Tool
    elif intent == "unwanted_spending":
        fc = compute_forecast(db, current_m, user_id=user_id)
        if not fc.has_sufficient_history:
            reply = (
                f"You have spent **₹{fc.total_unwanted_spent:,.2f}** on discretionary items so far in {fc.month}. "
                f"Historical data is currently insufficient to establish a regular spending baseline. "
                f"Logging transactions across multiple months will allow Nidhi Pilot to calculate your personal baseline."
            )
        elif fc.is_overspending_on_unwanted:
            reply = f"### Discretionary Spending Alert ({fc.month})\n\n{fc.overspending_summary}\n\n"
            for a in fc.unwanted_spending_alerts:
                reply += (
                    f"- **{a.category}:** Spent ₹{a.current_spent:,.2f} so far; estimated month-end is ₹{a.projected_spent:,.2f} "
                    f"(+{a.excess_percentage}% over baseline ₹{a.regular_baseline:,.2f}).\n"
                    f"  *{a.recommendation}*\n"
                )
        else:
            reply = (
                f"Your discretionary spending is well controlled and tracking within your regular benchmarks. "
                f"Total spent on discretionary items so far: **₹{fc.total_unwanted_spent:,.2f}**. "
                f"Projected month-end savings: **₹{fc.projected_savings:,.2f}** ({fc.projected_savings_rate}%)."
            )
        return reply, suggested_prompts, fc.model_dump()

    # Default: General cash flow overview
    summary = calculate_summary(db, current_m, user_id=user_id)
    reply = (
        f"### Financial Overview for {summary.period}\n\n"
        f"- **Monthly Salary:** ₹{summary.current_month_salary:,.2f}\n"
        f"- **Total Expenses:** ₹{summary.total_expenses:,.2f}\n"
        f"- **Remaining Balance:** ₹{summary.available_balance:,.2f}\n"
        f"- **Current Savings Rate:** {summary.savings_rate}%\n"
        f"- **Logged Transactions:** {summary.transaction_count}"
    )
    return reply, suggested_prompts, summary.model_dump()


async def route_chat_query(
    query: str, db: Session, context_month: Optional[str] = None, user_id: str = "default_user"
) -> ChatResponse:
    """
    Central Orchestrator:
    1. Extracts intent and executes database queries/calculations.
    2. Builds verified facts and loads recent conversation context from chat_messages table.
    3. If Groq/Gemini key is present, synthesizes natural language response.
    4. If no LLM key or call fails, returns mathematically grounded deterministic response.
    5. Persists conversation in chat_messages table.
    """
    current_m = context_month or datetime.now().strftime("%Y-%m")
    summary = calculate_summary(db, current_m, user_id)
    analysis = calculate_analysis(db, current_m, user_id)
    budget = get_current_budget(db, current_m, user_id)
    salary_record = get_salary_for_month(db, current_m, user_id)
    forecast = compute_forecast(db, current_m, user_id)
    goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).all()
    evaluated_goals = [evaluate_goal(g, db).model_dump() for g in goals]

    intent = classify_intent(query)
    det_reply, suggested_prompts, query_data = execute_deterministic_tool(
        intent, query, db, user_id, current_m
    )

    financial_facts = {
        "summary": summary.model_dump(),
        "top_categories": [c.model_dump() for c in summary.top_categories],
        "essential_spending": analysis.essential_spending,
        "discretionary_spending": analysis.discretionary_spending,
        "budget": budget.model_dump() if budget else {"is_set": False},
        "salary_info": {"amount": salary_record.amount if salary_record else 0.0},
        "forecast": forecast.model_dump(),
        "goals": evaluated_goals,
        "period_query": query_data,
        "tool_calculation_result": det_reply,
    }

    # Load recent conversation history (last 5 messages)
    history_records = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(6)
        .all()
    )
    history_records.reverse()
    conversation_history = [{"role": m.role, "content": m.content} for m in history_records]

    # Save user message
    user_msg_record = ChatMessage(
        user_id=user_id,
        role="user",
        content=query,
        intent=intent,
    )
    db.add(user_msg_record)
    db.commit()

    # Attempt Groq LLM
    groq_key = get_groq_api_key()
    if groq_key:
        groq_reply = await generate_groq_response(
            query, financial_facts, api_key=groq_key, conversation_history=conversation_history
        )
        if groq_reply:
            bot_msg = ChatMessage(
                user_id=user_id,
                role="assistant",
                content=groq_reply,
                engine="groq",
                intent=intent,
            )
            db.add(bot_msg)
            db.commit()
            return ChatResponse(
                reply=groq_reply,
                engine="groq",
                engine_name=f"Groq LLM ({get_groq_model()})",
                intent=intent,
                structured_data=query_data or financial_facts["summary"],
                suggested_prompts=suggested_prompts,
            )

    # Attempt Gemini LLM
    gemini_key = get_gemini_api_key()
    if gemini_key:
        gemini_reply = await generate_gemini_response(
            query, financial_facts, api_key=gemini_key, conversation_history=conversation_history
        )
        if gemini_reply:
            bot_msg = ChatMessage(
                user_id=user_id,
                role="assistant",
                content=gemini_reply,
                engine="gemini",
                intent=intent,
            )
            db.add(bot_msg)
            db.commit()
            return ChatResponse(
                reply=gemini_reply,
                engine="gemini",
                engine_name=f"Google Gemini ({get_gemini_model()})",
                intent=intent,
                structured_data=query_data or financial_facts["summary"],
                suggested_prompts=suggested_prompts,
            )

    # Attempt Ollama local
    ollama_reply = await generate_ollama_response(query, financial_facts)
    if ollama_reply:
        bot_msg = ChatMessage(
            user_id=user_id,
            role="assistant",
            content=ollama_reply,
            engine="ollama",
            intent=intent,
        )
        db.add(bot_msg)
        db.commit()
        return ChatResponse(
            reply=ollama_reply,
            engine="ollama",
            engine_name="Ollama Local LLM",
            intent=intent,
            structured_data=query_data or financial_facts["summary"],
            suggested_prompts=suggested_prompts,
        )

    # Deterministic Fallback with honest transparency
    bot_msg = ChatMessage(
        user_id=user_id,
        role="assistant",
        content=det_reply,
        engine="deterministic",
        intent=intent,
    )
    db.add(bot_msg)
    db.commit()

    return ChatResponse(
        reply=det_reply,
        engine="deterministic",
        engine_name="⚡ Nidhi Pilot Financial Rule Engine (Deterministic)",
        intent=intent,
        structured_data=query_data or financial_facts["summary"],
        suggested_prompts=suggested_prompts,
    )
