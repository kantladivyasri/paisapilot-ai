import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq

from app.agents.langchain_tools import get_nidhi_langchain_tools
from app.services.llm_service import (
    get_gemini_api_key,
    get_gemini_model,
    get_groq_api_key,
    get_groq_model,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Nidhi Pilot AI, an intelligent agentic personal finance assistant in India.\n\n"
    "AGENTIC OPERATING PRINCIPLES:\n"
    "1. TOOL INVOCATION FIRST: You have real-time tools connecting directly to the user's verified financial database.\n"
    "   - To check salary, balances, or outflow -> invoke get_salary_and_balance_tool.\n"
    "   - For specific category spend (e.g. food, shopping, rent) or biggest expense -> invoke query_category_spending_tool.\n"
    "   - For period totals (weekly, monthly, yearly, date ranges) -> invoke get_period_spending_report_tool.\n"
    "   - For monthly forecasts or overspending on unwanted items -> invoke predict_month_end_forecast_tool.\n"
    "   - For purchasing questions ('Can I afford X?') -> invoke check_affordability_simulation_tool.\n"
    "   - For budgets and savings targets -> invoke get_budget_and_savings_goals_tool.\n"
    "   - For recent transactions -> invoke list_recent_transactions_tool.\n"
    "   - For importing transactions from SMS, UPI alerts, or statement text -> invoke import_transactions_agent_tool.\n"
    "2. STRICT FACTUAL GROUNDING: Rely exclusively on the tool results. Never invent numbers, dates, salaries, or baselines.\n"
    "3. CONCISE & PROFESSIONAL: Deliver clear, natural, direct answers in 1–3 concise sentences for simple queries. "
    "Use bullet points only when presenting multiple figures.\n"
    "4. INDIAN RUPEE FORMAT: Always format currency using the Indian numbering system with the rupee symbol (e.g. ₹3,500.00).\n"
    "5. NO RAW JSON OR TOOL LEAKS: Present findings in clean Markdown. Never output raw JSON dictionaries or internal function call parameters."
)


def get_agent_llm(
    groq_key: Optional[str] = None,
    gemini_key: Optional[str] = None,
) -> Tuple[Optional[Any], str]:
    """
    Initializes the primary LangChain Chat Model (Groq or Gemini) based on provided key or environment configuration.
    """
    gk = groq_key if groq_key is not None else get_groq_api_key()
    if gk:
        model_name = get_groq_model()
        try:
            llm = ChatGroq(
                api_key=gk,
                model=model_name,
                temperature=0.1,
                max_retries=2,
            )
            return llm, f"Groq ({model_name})"
        except Exception as e:
            logger.warning(f"Failed to initialize ChatGroq: {e}")

    gk_gemini = gemini_key if gemini_key is not None else get_gemini_api_key()
    if gk_gemini:
        model_name = get_gemini_model()
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                google_api_key=gk_gemini,
                model=model_name,
                temperature=0.1,
            )
            return llm, f"Google Gemini ({model_name})"
        except Exception as e:
            logger.warning(f"Failed to initialize ChatGoogleGenerativeAI: {e}")

    return None, ""


async def run_nidhi_langchain_agent(
    query: str,
    db: Session,
    user_id: str = "default_user",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    max_steps: int = 5,
    groq_key: Optional[str] = None,
    gemini_key: Optional[str] = None,
) -> Tuple[Optional[str], List[str], str]:
    """
    Runs the autonomous LangChain tool-calling financial agent.
    Returns:
        (agent_reply_text, tools_called_list, engine_display_name)
    """
    llm, engine_name = get_agent_llm(groq_key=groq_key, gemini_key=gemini_key)
    if not llm:
        return None, [], ""

    tools = get_nidhi_langchain_tools(db, user_id=user_id)
    tools_by_name = {t.name: t for t in tools}

    try:
        llm_with_tools = llm.bind_tools(tools)
    except Exception as e:
        logger.warning(f"Failed to bind tools to LLM: {e}")
        return None, [], ""

    # Build conversation messages
    messages: List[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

    if conversation_history:
        for msg in conversation_history[-6:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=query))

    tools_called: List[str] = []

    # Autonomous Tool-Calling Execution Loop
    for step in range(max_steps):
        try:
            ai_msg: AIMessage = await llm_with_tools.ainvoke(messages)
        except Exception as e:
            logger.error(f"Error during agent step {step}: {e}")
            # Try synchronous fallback if ainvoke is not available on custom transport
            try:
                ai_msg = llm_with_tools.invoke(messages)
            except Exception as e2:
                logger.error(f"Synchronous invoke also failed: {e2}")
                return None, tools_called, engine_name

        messages.append(ai_msg)

        # Check if the agent called any tools
        tool_calls = getattr(ai_msg, "tool_calls", None)
        if not tool_calls:
            # Agent concluded its reasoning and produced final response
            reply_text = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
            return reply_text.strip(), tools_called, engine_name

        # Execute tool calls
        for tc in tool_calls:
            name = tc.get("name")
            args = tc.get("args", {})
            call_id = tc.get("id") or f"call_{len(tools_called)}"

            if name not in tools_called:
                tools_called.append(name)

            tool_instance = tools_by_name.get(name)
            if tool_instance:
                try:
                    tool_output = tool_instance.invoke(args)
                except Exception as te:
                    tool_output = f"Tool execution error for {name}: {str(te)}"
            else:
                tool_output = f"Unknown tool: {name}"

            messages.append(
                ToolMessage(
                    content=str(tool_output),
                    tool_call_id=call_id,
                    name=name,
                )
            )

    # If reached max steps, return last AI message content if present
    last_msg = messages[-1]
    if isinstance(last_msg, AIMessage) and last_msg.content:
        return str(last_msg.content).strip(), tools_called, engine_name

    return None, tools_called, engine_name
