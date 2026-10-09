import calendar
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool, BaseTool
from sqlalchemy.orm import Session

from app.agents.analyzer import calculate_analysis, calculate_summary
from app.agents.budget_agent import get_current_budget
from app.agents.period_analyzer import compute_period_report
from app.agents.prediction_agent import compute_forecast
from app.agents.salary_service import calculate_salary_dashboard_metrics, get_salary_for_month
from app.models import Category, SavingsGoal, Transaction


def get_nidhi_langchain_tools(db: Session, user_id: str = "default_user") -> List[BaseTool]:
    """
    Factory creating structured LangChain tools bound to the active database session.
    All tools query real verified financial records from SQLite with deterministic logic.
    """
    current_month_str = datetime.now().strftime("%Y-%m")

    @tool
    def get_salary_and_balance_tool(month: Optional[str] = None) -> str:
        """
        Get the user's recorded monthly salary, total outflow spent so far,
        remaining balance (salary minus expenses), and current savings rate.
        Args:
            month: Optional string in YYYY-MM format (e.g. '2026-10'). Defaults to current month.
        """
        target_m = month if (month and len(month) == 7 and "-" in month) else current_month_str
        metrics = calculate_salary_dashboard_metrics(db, target_m, user_id=user_id)
        
        salary = metrics["current_month_salary"]
        expenses = metrics["total_expenses"]
        balance = metrics["remaining_balance"]
        savings_rate = metrics["savings_rate"]

        if salary <= 0:
            return (
                f"For {target_m}, monthly salary is not configured (₹0.00). "
                f"Total expenses recorded so far: ₹{expenses:,.2f}. "
                f"Remaining balance: ₹{balance:,.2f}."
            )

        return (
            f"Financial Status for {target_m}:\n"
            f"- Monthly Salary: ₹{salary:,.2f}\n"
            f"- Total Expenses So Far: ₹{expenses:,.2f}\n"
            f"- Remaining Available Balance: ₹{balance:,.2f}\n"
            f"- Savings Rate: {savings_rate:.1f}%\n"
            f"- Balance Status: {'Surplus (Safe to spend)' if balance >= 0 else 'Deficit (Expenses exceed salary)'}"
        )

    @tool
    def query_category_spending_tool(category_name: str, month: Optional[str] = None) -> str:
        """
        Query exact spending, transaction count, percentage of expenses, and budget limit
        for a specific category (e.g. Food, Groceries, Shopping, Rent, Entertainment, Transportation, Bills).
        Args:
            category_name: The category to look up (case-insensitive).
            month: Optional string in YYYY-MM format. Defaults to current month.
        """
        target_m = month if (month and len(month) == 7 and "-" in month) else current_month_str
        
        # Match category case-insensitively
        cat_records = db.query(Category).filter(Category.user_id == user_id).all()
        matched_cat = None
        for c in cat_records:
            if c.name.lower() == category_name.lower():
                matched_cat = c
                break
        
        real_cat_name = matched_cat.name if matched_cat else category_name.capitalize()
        budget_limit = matched_cat.budget_limit if matched_cat and matched_cat.budget_limit else None

        txns = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "expense",
                Transaction.date.startswith(target_m),
            )
            .all()
        )

        cat_spent = sum(t.amount for t in txns if t.category.lower() == category_name.lower())
        cat_count = sum(1 for t in txns if t.category.lower() == category_name.lower())
        total_spent = sum(t.amount for t in txns)
        pct = (cat_spent / total_spent * 100) if total_spent > 0 else 0.0

        res = (
            f"Category Spending for '{real_cat_name}' in {target_m}:\n"
            f"- Total Spent: ₹{cat_spent:,.2f}\n"
            f"- Transactions Logged: {cat_count}\n"
            f"- Share of Total Outflow: {pct:.1f}% (Total month spend: ₹{total_spent:,.2f})\n"
        )

        if budget_limit:
            remaining = budget_limit - cat_spent
            res += (
                f"- Monthly Budget Limit: ₹{budget_limit:,.2f}\n"
                f"- Remaining Budget Allowance: ₹{remaining:,.2f} "
                f"({'Within Limit' if remaining >= 0 else '⚠️ Over Budget!'})"
            )
        else:
            res += "- Budget Limit: No specific cap set."

        return res

    @tool
    def get_period_spending_report_tool(
        period_type: str = "monthly",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """
        Get verified financial spending and income totals for a specific time period.
        Args:
            period_type: One of 'daily', 'weekly', 'monthly', 'yearly', or 'custom'.
            start_date: Start date string in YYYY-MM-DD format (used for 'custom').
            end_date: End date string in YYYY-MM-DD format (used for 'custom').
        """
        params = {}
        if period_type == "custom":
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date

        report = compute_period_report(db, period_type, params, user_id=user_id)
        curr = report.current_period
        prev = report.previous_period
        comp = report.comparison

        categories_summary = ", ".join(
            [
                f"{getattr(c, 'category', str(c))}: ₹{getattr(c, 'amount', 0):,.2f} ({getattr(c, 'percentage', 0)}%)"
                for c in curr.category_breakdown[:4]
            ]
        ) or "None"

        return (
            f"Spending Report for {curr.period_label} ({curr.start_date} to {curr.end_date}):\n"
            f"- Total Income Inflow: ₹{curr.total_income:,.2f}\n"
            f"- Total Expenses Outflow: ₹{curr.total_expenses:,.2f}\n"
            f"- Net Balance: ₹{curr.remaining_balance:,.2f}\n"
            f"- Savings Rate: {curr.savings_rate:.1f}%\n"
            f"- Transactions Logged: {curr.transaction_count}\n"
            f"- Top Categories: {categories_summary}\n"
            f"- Compared to Previous ({prev.period_label}): Outflow changed by {comp.expense_change_percent}% "
            f"({'+' if comp.expense_change_amount >= 0 else ''}₹{comp.expense_change_amount:,.2f})."
        )

    @tool
    def predict_month_end_forecast_tool(month: Optional[str] = None) -> str:
        """
        Calculate month-end expense and savings projections, daily spending run-rate,
        and detect any unwanted or discretionary overspending (shopping, dining, entertainment).
        Args:
            month: Optional string in YYYY-MM format. Defaults to current month.
        """
        target_m = month if (month and len(month) == 7 and "-" in month) else current_month_str
        fc = compute_forecast(db, target_m, user_id=user_id)

        alerts_text = "None (Discretionary habits are within regular benchmarks)."
        if fc.unwanted_spending_alerts:
            alerts_list = []
            for a in fc.unwanted_spending_alerts:
                alerts_list.append(
                    f"⚠️ {a.category}: Spent ₹{a.current_spent:,.2f} (Projected ₹{a.projected_spent:,.2f}, "
                    f"+{a.excess_percentage}% over baseline ₹{a.regular_baseline:,.2f}). Rec: {a.recommendation}"
                )
            alerts_text = "\n".join(alerts_list)

        return (
            f"Month-End Projection ({fc.month} evaluated on {fc.evaluation_date}):\n"
            f"- Days Elapsed: {fc.days_passed} of {fc.total_days} ({fc.days_remaining} days remaining)\n"
            f"- Actual Expenses So Far: ₹{fc.current_expenses:,.2f}\n"
            f"- Average Daily Spending Pace: ₹{fc.daily_spending_pace:,.2f}/day (Regular baseline: ₹{fc.regular_daily_baseline:,.2f}/day)\n"
            f"- Estimated Month-End Outflow: ₹{fc.projected_expenses:,.2f} (PROJECTION)\n"
            f"- Monthly Salary: ₹{fc.monthly_salary:,.2f}\n"
            f"- Estimated Month-End Savings: ₹{fc.projected_savings:,.2f} ({fc.projected_savings_rate:.1f}% savings rate)\n"
            f"- Trajectory Status: {fc.projected_status.upper()}\n"
            f"- Sufficient Baseline Available: {fc.has_sufficient_history}\n"
            f"- Discretionary Overspending Alerts:\n{alerts_text}"
        )

    @tool
    def check_affordability_simulation_tool(item_name: str, item_cost: float) -> str:
        """
        Simulate whether the user can afford a proposed purchase without causing a deficit
        or violating their savings target.
        Args:
            item_name: Description of what user wants to buy (e.g. 'New Phone', 'Shoes').
            item_cost: Cost of the item in INR (positive number).
        """
        metrics = calculate_salary_dashboard_metrics(db, current_month_str, user_id=user_id)
        salary = metrics["current_month_salary"]
        current_expenses = metrics["total_expenses"]
        current_balance = metrics["remaining_balance"]

        if item_cost <= 0:
            return "Item cost must be a positive number."

        post_balance = current_balance - item_cost
        post_expenses = current_expenses + item_cost
        post_savings_rate = ((salary - post_expenses) / salary * 100) if salary > 0 else 0.0

        can_afford = post_balance >= 0

        verdict = (
            f"Affordability Simulation for '{item_name}' (Cost: ₹{item_cost:,.2f}):\n"
            f"- Current Remaining Balance: ₹{current_balance:,.2f}\n"
            f"- Estimated Post-Purchase Balance: ₹{post_balance:,.2f}\n"
            f"- Current Expenses: ₹{current_expenses:,.2f} -> Post-Purchase: ₹{post_expenses:,.2f}\n"
            f"- Post-Purchase Savings Rate: {post_savings_rate:.1f}%\n"
            f"- Can Afford: {'YES ✅' if can_afford else 'NO ❌ (Would cause a deficit of ₹' + f'{abs(post_balance):,.2f})'}\n"
            f"- Recommendation: "
            f"{'Safe to purchase while remaining cash-flow positive.' if can_afford else 'Pause or defer this discretionary expense to avoid debt.'}"
        )
        return verdict

    @tool
    def get_budget_and_savings_goals_tool() -> str:
        """
        Retrieve active monthly budget allocations, 50/30/20 breakdown,
        and current savings goals milestones with target dates and feasibility.
        """
        budget = get_current_budget(db, current_month_str, user_id=user_id)
        goals = db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id).all()

        budget_summary = "No budget configured yet."
        if budget:
            budget_summary = (
                f"Needs: ₹{budget.essential_expenses:,.2f}, Wants Allowance: ₹{budget.discretionary_allowance:,.2f}, "
                f"Savings Target: ₹{budget.savings_target:,.2f}, Emergency Fund Target: ₹{budget.emergency_fund_target:,.2f}. "
                f"Balanced: {budget.is_balanced}"
            )

        goals_text = "No savings goals created."
        if goals:
            g_list = []
            for g in goals:
                pct = (g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0
                g_list.append(
                    f"🎯 {g.name}: Saved ₹{g.current_amount:,.2f} of ₹{g.target_amount:,.2f} ({pct:.1f}%) "
                    f"by {g.target_date}"
                )
            goals_text = "\n".join(g_list)

        return (
            f"Budget & Goals Status:\n"
            f"- Monthly Budget: {budget_summary}\n"
            f"- Savings Goals:\n{goals_text}"
        )

    @tool
    def list_recent_transactions_tool(limit: int = 5, category: Optional[str] = None) -> str:
        """
        List the most recent recorded financial transactions (credits and debits)
        with date, description, category, payment method, and amount.
        Args:
            limit: Number of transactions to return (1 to 20, default 5).
            category: Optional filter by category name.
        """
        limit_val = max(1, min(20, limit))
        q = db.query(Transaction).filter(Transaction.user_id == user_id)
        if category:
            q = q.filter(Transaction.category.ilike(f"%{category}%"))
        
        txns = q.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit_val).all()
        if not txns:
            return "No transactions found matching criteria."

        lines = []
        for t in txns:
            sign = "+" if t.transaction_type == "income" else "-"
            lines.append(
                f"- {t.date} | {t.description} ({t.category}) | {t.payment_method or 'UPI'} | {sign}₹{t.amount:,.2f}"
            )
        return "Recent Transactions:\n" + "\n".join(lines)

    @tool
    def import_transactions_agent_tool(raw_text_or_sms_batch: str, commit_immediately: bool = False) -> str:
        """
        Automated Transaction Import Agent tool:
        Extracts, categorizes, validates, and detects duplicates from raw bank SMS alerts,
        UPI notifications, statement lines, or natural language expense notes.
        Args:
            raw_text_or_sms_batch: Raw text containing one or more bank SMS messages or transaction sentences.
            commit_immediately: If True, saves non-duplicate records into the database. If False, returns preview.
        """
        from app.agents.import_agent import TransactionImportAgent
        from app.schemas import TransactionCreate

        preview = TransactionImportAgent.preview_import(raw_text_or_sms_batch, db, user_id=user_id)
        if preview.total_detected == 0:
            return "No transactions could be parsed from the provided text. Please verify the wording or format."

        lines = [f"Import Agent Extracted {preview.total_detected} Transaction(s):"]
        for p in preview.parsed_transactions:
            dup_tag = " [⚠️ Potential Duplicate]" if p.is_duplicate else " [✨ New]"
            sign = "+" if p.transaction_type == "income" else "-"
            lines.append(
                f"- {p.date}: {p.description} -> {p.category} ({sign}₹{p.amount:,.2f}) | {p.payment_method or 'Online'}{dup_tag}"
            )

        lines.append(f"\nTotal Outflow: ₹{preview.total_expenses:,.2f} | Total Inflow: ₹{preview.total_income:,.2f}")

        if commit_immediately:
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
            if txns_to_commit:
                commit_res = TransactionImportAgent.commit_transactions(txns_to_commit, db, user_id=user_id)
                lines.append(f"Successfully saved {commit_res.imported_count} new transaction(s) to your database!")
            else:
                lines.append("All detected items were identified as duplicates. No new records saved.")
        else:
            lines.append("Preview mode: These were not yet saved. Confirm to record them in your database.")

        return "\n".join(lines)

    return [
        get_salary_and_balance_tool,
        query_category_spending_tool,
        get_period_spending_report_tool,
        predict_month_end_forecast_tool,
        check_affordability_simulation_tool,
        get_budget_and_savings_goals_tool,
        list_recent_transactions_tool,
        import_transactions_agent_tool,
    ]

