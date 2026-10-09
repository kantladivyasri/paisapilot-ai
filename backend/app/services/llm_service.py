import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


def get_groq_api_key() -> Optional[str]:
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    key = os.getenv("GROQ_API_KEY", "").strip()
    return key if key else None


def get_gemini_api_key() -> Optional[str]:
    load_dotenv(dotenv_path=ENV_PATH, override=True)
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return key if key else None


def get_groq_model() -> str:
    return os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip()


def get_gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()


def get_ollama_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()


def save_env_setting(key: str, value: str) -> None:
    """Safely updates or appends a key-value pair in backend/.env file."""
    lines = []
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    os.environ[key] = value


def build_system_prompt(financial_facts: Dict[str, Any], conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    """Builds an expert personal finance prompt deeply grounded in verified database facts."""
    summary = financial_facts.get("summary", {})
    top_cats = financial_facts.get("top_categories", [])
    budget = financial_facts.get("budget", {})
    goals = financial_facts.get("goals", [])
    period_info = financial_facts.get("period_query", {})
    salary_info = financial_facts.get("salary_info", {})

    facts_text = f"""
--- VERIFIED FINANCIAL DATA (FROM USER'S SQLITE DATABASE) ---
1. CASH FLOW & SALARY OVERVIEW:
   • Monthly Salary Recorded: ₹{summary.get('current_month_salary', salary_info.get('amount', 0)):,.2f}
   • Total Inflows: ₹{summary.get('total_income', 0):,.2f}
   • Total Expenses: ₹{summary.get('total_expenses', 0):,.2f}
   • Net Remaining Balance: ₹{summary.get('available_balance', 0):,.2f}
   • Savings Rate: {summary.get('savings_rate', 0)}%
   • Total Transactions: {summary.get('transaction_count', 0)}
   • Reporting Cycle: {summary.get('period', 'Current Month')}

2. ESSENTIAL VS DISCRETIONARY SPENDING:
   • Essential Obligations (Rent, Groceries, Utilities, Healthcare, Education): ₹{financial_facts.get('essential_spending', 0):,.2f}
   • Discretionary Lifestyle Spending (Dining, Shopping, Entertainment): ₹{financial_facts.get('discretionary_spending', 0):,.2f}

3. CATEGORY BREAKDOWN WITH BUDGET LIMITS:
"""
    for c in top_cats:
        tag = "Essential" if c.get("is_essential") else "Discretionary"
        limit_str = f" | Budget: ₹{c.get('budget_limit', 0):,.2f} ({c.get('budget_status', 'normal')})" if c.get('budget_limit', 0) > 0 else ""
        facts_text += f"   • {c['category']}: ₹{c['amount']:,.2f} ({c['percentage']}% of expenses) [{tag}]{limit_str}\n"

    if period_info:
        cat_str = f" for Category '{period_info['category']}'" if period_info.get("category") else ""
        period_lbl = period_info.get('period_label') or period_info.get('month', 'Specified Period')
        amt = period_info.get('total_expenses') if period_info.get('total_expenses') is not None else period_info.get('amount', 0)
        facts_text += f"""
4. PERIOD / SPECIFIC QUERY RESULTS:
   • Period: {period_lbl}{cat_str}
   • Recorded Spending/Amount: ₹{amt:,.2f}
   • Total Inflow/Income: ₹{period_info.get('total_income', 0):,.2f}
   • Remaining Balance: ₹{period_info.get('remaining_balance', 0):,.2f}
   • Comparison vs Previous: {period_info.get('comparison_text', 'N/A')}
"""

    if budget.get("is_set"):
        facts_text += f"""
5. MONTHLY BUDGET STATUS:
   • Balanced Budget Configured: {budget.get('is_balanced')}
   • Monthly Income Baseline: ₹{budget.get('monthly_income', 0):,.2f}
   • Essential Expenses Budget: ₹{budget.get('essential_expenses', 0):,.2f}
   • Discretionary Allowance: ₹{budget.get('discretionary_allowance', 0):,.2f}
   • Target Savings Allocation: ₹{budget.get('savings_target', 0):,.2f}
   • Emergency Fund Allocation: ₹{budget.get('emergency_fund_target', 0):,.2f}
"""

    if goals:
        facts_text += "\n6. ACTIVE SAVINGS MILESTONES:\n"
        for g in goals:
            facts_text += f"   • {g['name']}: Saved ₹{g['current_amount']:,.2f} of ₹{g['target_amount']:,.2f} ({g['progress_percentage']}%) | Target Date: {g['target_date']}\n"

    forecast_info = financial_facts.get("forecast", {})
    if forecast_info:
        alerts = forecast_info.get("unwanted_spending_alerts", [])
        alerts_txt = ""
        for a in alerts:
            alerts_txt += f"      - {a.get('category')}: Spent ₹{a.get('current_spent', 0):,.2f} so far, projected ₹{a.get('projected_spent', 0):,.2f} (+{a.get('excess_percentage', 0)}% over regular baseline ₹{a.get('regular_baseline', 0):,.2f}). Recommendation: {a.get('recommendation')}\n"

        facts_text += f"""
7. AI EXPENSE & SAVINGS PREDICTION (FORECAST):
   • Evaluated Days: {forecast_info.get('days_passed', 0)} of {forecast_info.get('total_days', 30)} ({forecast_info.get('days_remaining', 0)} days remaining)
   • Daily Spending Pace: ₹{forecast_info.get('daily_spending_pace', 0):,.2f}/day (Regular Baseline: ₹{forecast_info.get('regular_daily_baseline', 0):,.2f}/day)
   • Projected Month-End Total Expenses: ₹{forecast_info.get('projected_expenses', 0):,.2f}
   • Projected Month-End Net Savings: ₹{forecast_info.get('projected_savings', 0):,.2f} ({forecast_info.get('projected_savings_rate', 0)}%)
   • Trajectory Status: {forecast_info.get('projected_status', 'healthy').upper()}
   • Overspending on Unwanted Items: {forecast_info.get('is_overspending_on_unwanted', False)}
   • Overspending Summary: {forecast_info.get('overspending_summary', '')}
   • Discretionary Anomaly Alerts:
{alerts_txt if alerts_txt else '      None, discretionary pace is safely under control.'}
"""

    tool_res = financial_facts.get("tool_calculation_result")
    if tool_res:
        facts_text += f"""
8. EXACT VERIFIED DATABASE TOOL ANSWER:
{tool_res}
"""

    history_text = ""
    if conversation_history:
        history_text = "\nRECENT CONVERSATION CONTEXT:\n"
        for msg in conversation_history[-5:]:
            sender = "User" if msg.get("role") == "user" else "Assistant"
            history_text += f"{sender}: {msg.get('content')}\n"

    system_prompt = (
        "You are PaisaPilot AI, a brilliant, empathetic, and highly analytical personal finance copilot for users in India.\n\n"
        "CORE DIRECTIVES:\n"
        "1. STRICT FACTUAL GROUNDING: You must ONLY use the exact financial figures provided in the verified facts below. "
        "NEVER make up balances, invent transactions, or hallucinate numbers. You have verified live access to their database records.\n"
        "2. INDIAN CONTEXT & CURRENCY: Always format money in Indian Rupees (₹) with appropriate Indian comma numbering (e.g. ₹11,000, ₹1,500.00).\n"
        "3. ACCURATE CALCULATIONS: When asked about affordability, remaining salary, weekly spending, past months, or category totals, cite the exact numbers from Sections 1-4 and Section 8 below and explain the math step-by-step.\n"
        "4. PRACTICAL & ACTIONABLE: Differentiate between fixed essentials (Rent, Groceries, Utilities) and lifestyle wants (Dining, Shopping), offering realistic, empathetic saving advice.\n"
        "5. PREDICTIVE EXPENSE & UNWANTED SPENDING WARNINGS: When asked to predict monthly expenses/savings or check if they are spending too much on unwanted/wasteful things, cite Section 7 (Forecast). Explicitly warn them if discretionary categories are trending higher than their regular baseline, state the projected month-end excess, and suggest concrete expense cuts.\n"
        "6. TONE: Warm, encouraging, financially prudent, and clear.\n"
        f"{facts_text}"
        f"{history_text}"
    )
    return system_prompt


async def generate_groq_response(
    user_query: str,
    financial_facts: Dict[str, Any],
    api_key: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """Sends request to Groq API with deterministic financial grounding and conversation history."""
    key = api_key or get_groq_api_key()
    if not key:
        return None

    model = get_groq_model()
    system_prompt = build_system_prompt(financial_facts, conversation_history)

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        for m in conversation_history[-4:]:
            role = "user" if m.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": m.get("content", "")})
    messages.append({"role": "user", "content": user_query})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 800,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GROQ_ENDPOINT, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
            else:
                print(f"Groq API error ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"Groq API call error: {e}")
        return None

    return None


async def generate_gemini_response(
    user_query: str,
    financial_facts: Dict[str, Any],
    api_key: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """Sends request to Google Gemini API with deterministic financial grounding."""
    key = api_key or get_gemini_api_key()
    if not key:
        return None

    model = get_gemini_model()
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    system_prompt = build_system_prompt(financial_facts, conversation_history)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\nUser Question: {user_query}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 800,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(endpoint, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                return content.strip()
    except Exception as e:
        print(f"Gemini API call error: {e}")
        return None

    return None


async def generate_ollama_response(
    user_query: str, financial_facts: Dict[str, Any]
) -> Optional[str]:
    """Attempts local Ollama generation if available."""
    url = f"{get_ollama_url()}/api/generate"
    system_prompt = build_system_prompt(financial_facts)
    payload = {
        "model": "llama3",
        "prompt": f"{system_prompt}\n\nUser Question: {user_query}",
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
    except Exception:
        return None
    return None
