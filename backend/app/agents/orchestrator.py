import calendar
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.agents.analyzer import calculate_analysis, calculate_summary
from app.agents.budget_agent import get_current_budget
from app.agents.period_analyzer import compute_period_report
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
    if any(k in q for k in ["this week", "weekly", "spend this week", "past 7 days"]):
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
        
        reply = (
            f"📅 **Weekly Spending Summary ({cur.period_label}):**\n"
            f"• **Total Expenses This Week:** ₹{cur.total_expenses:,.2f} across {cur.transaction_count} transaction(s)\n"
            f"• **Previous Week Expenses:** ₹{comp.previous_expenses:,.2f}\n"
        )
        if comp.previous_expenses > 0:
            if comp.expense_change_amount > 0:
                reply += f"• **Trend:** Increased by ₹{comp.expense_change_amount:,.2f} (+{comp.expense_change_percent}% vs last week) 📈\n"
            else:
                reply += f"• **Trend:** Decreased by ₹{abs(comp.expense_change_amount):,.2f} ({comp.expense_change_percent}% vs last week) 📉\n"
        
        if cur.category_breakdown:
            reply += "\n**Top Categories This Week:**\n"
            for c in cur.category_breakdown[:3]:
                reply += f"• {c.category}: ₹{c.amount:,.2f} ({c.percentage}%)\n"
        return reply, suggested_prompts, {"weekly": cur.model_dump()}

    # 2. Yearly Expenses
    elif intent == "yearly_expenses":
        year_report = compute_period_report(db, period_type="yearly", user_id=user_id)
        cur = year_report.current_period
        reply = (
            f"🗓️ **Total Expenses for {cur.period_label}:**\n"
            f"• **Total Year-to-Date Expenses:** ₹{cur.total_expenses:,.2f}\n"
            f"• **Total Recorded Inflow / Salary:** ₹{cur.total_income:,.2f}\n"
            f"• **Net Cumulative Balance:** ₹{cur.remaining_balance:,.2f}\n"
            f"• **Annual Savings Rate:** {cur.savings_rate}%\n"
        )
        if cur.category_breakdown:
            reply += "\n**Leading Expense Drivers This Year:**\n"
            for c in cur.category_breakdown[:4]:
                reply += f"• {c.category}: ₹{c.amount:,.2f} ({c.percentage}% of annual spend)\n"
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
                f"You haven't recorded a salary for **{current_m}** yet.\n"
                f"• Current month expenses logged: ₹{exp:,.2f}\n"
                f"💡 Tip: Click the **'Set Salary'** button in the dashboard to store your monthly salary and track your live balance!"
            )
        else:
            reply = (
                f"💰 **Monthly Salary Cash Flow ({current_m}):**\n"
                f"• **Recorded Salary:** ₹{sal:,.2f}\n"
                f"• **Total Expenses So Far:** ₹{exp:,.2f}\n"
                f"• **Remaining Balance Left:** ₹{rem:,.2f}\n"
                f"• **Current Savings Rate:** {rate}%\n"
            )
            if rem > 0:
                reply += f"You have ₹{rem:,.2f} remaining from your salary to allocate toward essentials and savings milestones."
            else:
                reply += f"⚠️ Caution: Your expenses exceed your salary by ₹{abs(rem):,.2f}. Avoid any discretionary purchases."
        return reply, suggested_prompts, metrics

    # 4. Compare This Month With Last Month
    elif intent == "compare_months":
        month_report = compute_period_report(db, period_type="monthly", user_id=user_id)
        cur = month_report.current_period
        prev = month_report.previous_period
        comp = month_report.comparison

        reply = (
            f"📊 **Month-over-Month Spending Comparison:**\n"
            f"• **{cur.period_label} Expenses:** ₹{cur.total_expenses:,.2f}\n"
            f"• **{prev.period_label} Expenses:** ₹{prev.total_expenses:,.2f}\n"
        )
        if prev.total_expenses > 0:
            if comp.expense_change_amount > 0:
                reply += f"• **Overall Change:** Spending increased by ₹{comp.expense_change_amount:,.2f} (+{comp.expense_change_percent}%).\n"
            else:
                reply += f"• **Overall Change:** Spending decreased by ₹{abs(comp.expense_change_amount):,.2f} ({comp.expense_change_percent}%).\n"
        else:
            reply += "• No transactions recorded in the previous month for a full baseline comparison.\n"

        if comp.increased_categories:
            reply += f"\n📈 **Categories With Increased Spending:**\n"
            for ic in comp.increased_categories[:3]:
                reply += f"• {ic['category']}: +₹{ic['increase_amount']:,.2f} (from ₹{ic['previous_amount']:,.2f} to ₹{ic['current_amount']:,.2f})\n"

        if comp.decreased_categories:
            reply += f"\n📉 **Categories With Savings / Reductions:**\n"
            for dc in comp.decreased_categories[:3]:
                reply += f"• {dc['category']}: -₹{dc['decrease_amount']:,.2f} (from ₹{dc['previous_amount']:,.2f} to ₹{dc['current_amount']:,.2f})\n"

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

        month_label = datetime.strptime(target_m, "%Y-%m").strftime("%B %Y")
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

        reply = f"🛒 **Audit for {cat_item.category} ({summary.period}):**\n"
        reply += f"• **Total Spent:** ₹{cat_item.amount:,.2f} ({cat_item.percentage}% of total expenses)\n"
        
        if cat_item.budget_limit > 0:
            reply += f"• **Monthly Budget Limit:** ₹{cat_item.budget_limit:,.2f}\n"
            if cat_item.amount > cat_item.budget_limit:
                over = cat_item.amount - cat_item.budget_limit
                reply += f"• **Status:** ⚠️ Exceeded by ₹{over:,.2f}! You have surpassed your limit.\n"
            elif cat_item.amount >= cat_item.budget_limit * 0.8:
                rem = cat_item.budget_limit - cat_item.amount
                reply += f"• **Status:** ⚡ Caution! Approaching limit with only ₹{rem:,.2f} remaining.\n"
            else:
                rem = cat_item.budget_limit - cat_item.amount
                reply += f"• **Status:** ✅ Within budget. ₹{rem:,.2f} remaining.\n"
        else:
            if cat_item.percentage > 20:
                reply += f"• **Assessment:** {cat_item.category} consumes {cat_item.percentage}% of all expenses. Consider setting a category budget limit to keep it below 15%."
            else:
                reply += f"• **Assessment:** Moderate spending at {cat_item.percentage}% of your expenses."

        return reply, suggested_prompts, cat_item.model_dump()

    # 7. How Can I Save Money
    elif intent == "save_money" or intent == "reduce_expenses":
        target_save = extract_amount_from_query(query) or 2000.0
        analysis = calculate_analysis(db, current_m, user_id=user_id)
        summary = calculate_summary(db, current_m, user_id=user_id)

        discretionary_cats = [c for c in summary.top_categories if not c.is_essential]

        reply = f"💡 **Practical Savings Strategy to Save ₹{target_save:,.2f} This Month:**\n\n"
        if not discretionary_cats:
            reply += (
                "You have minimal discretionary lifestyle expenses logged. "
                "To build savings, review fixed utility plans or explore income enhancement options."
            )
        else:
            reply += f"Your current discretionary lifestyle spend is **₹{analysis.discretionary_spending:,.2f}** ({analysis.discretionary_percentage}% of expenses).\n\n"
            reply += "**Recommended Action Plan:**\n"
            remaining_to_trim = target_save
            for idx, c in enumerate(discretionary_cats[:3], 1):
                trim_target = min(round(c.amount * 0.35, 2), remaining_to_trim)
                reply += f"{idx}. **Reduce {c.category} (Spent ₹{c.amount:,.2f}):** Trim by ~₹{trim_target:,.2f} by swapping delivery for home cooking or postponing non-essential purchases.\n"
                remaining_to_trim -= trim_target
                if remaining_to_trim <= 0:
                    break

            reply += f"\nImplementing these adjustments will free up ₹{target_save:,.2f} for your emergency fund and goals!"
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

        reply = f"🛍️ **Affordability Simulation for ₹{cost:,.2f}:**\n"
        reply += f"• Current Available Surplus: ₹{balance:,.2f}\n"
        reply += f"• Purchase Price: ₹{cost:,.2f}\n"
        reply += f"• Projected Balance After Purchase: ₹{new_balance:,.2f}\n"
        reply += f"• Projected Savings Rate: {new_rate}%\n\n"

        if new_balance >= 0:
            reply += f"✅ **Yes, you can afford this expense.** You will retain a comfortable surplus of ₹{new_balance:,.2f}. This purchase is safe for your cash flow."
        else:
            shortfall = abs(new_balance)
            reply += f"⚠️ **Caution: An expense of ₹{cost:,.2f} exceeds your available funds.** Shortfall of ₹{shortfall:,.2f} would trigger a cash deficit. Postponing is advised."
        return reply, suggested_prompts, {"cost": cost, "projected_balance": new_balance}

    # 9. Top Spending
    elif intent == "top_spending":
        summary = calculate_summary(db, current_m, user_id=user_id)
        if not summary.top_categories:
            return "You haven't recorded any expenses yet for this period.", suggested_prompts, {}

        top_cat = summary.top_categories[0]
        reply = f"Your highest spending category is **{top_cat.category}** at **₹{top_cat.amount:,.2f}** ({top_cat.percentage}% of total expenses).\n\n"
        reply += "**Top 4 Expense Drivers:**\n"
        for idx, c in enumerate(summary.top_categories[:4], 1):
            tag = "Essential" if c.is_essential else "Discretionary"
            reply += f"{idx}. **{c.category}**: ₹{c.amount:,.2f} ({c.percentage}%) — [{tag}]\n"
        return reply, suggested_prompts, summary.model_dump()

    # Default: General cash flow overview
    summary = calculate_summary(db, current_m, user_id=user_id)
    reply = (
        f"Here is your verified financial overview for **{summary.period}**:\n"
        f"• Monthly Salary Inflow: ₹{summary.current_month_salary:,.2f}\n"
        f"• Total Expenses: ₹{summary.total_expenses:,.2f}\n"
        f"• Remaining Balance: ₹{summary.available_balance:,.2f}\n"
        f"• Current Savings Rate: {summary.savings_rate}%\n"
        f"• Logged Transactions: {summary.transaction_count}\n"
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
        "goals": evaluated_goals,
        "period_query": query_data,
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
        engine_name="⚡ PaisaPilot Financial Rule Engine (Deterministic)",
        intent=intent,
        structured_data=query_data or financial_facts["summary"],
        suggested_prompts=suggested_prompts,
    )
