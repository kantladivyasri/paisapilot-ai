from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import SavingsGoal
from app.schemas import SavingsGoalResponse
from app.agents.analyzer import calculate_summary


def evaluate_goal(goal: SavingsGoal, db: Optional[Session] = None) -> SavingsGoalResponse:
    """
    Evaluates a savings goal with deterministic timeline and feasibility checks.
    """
    remaining_amount = round(max(0.0, goal.target_amount - goal.current_amount), 2)
    
    if goal.target_amount > 0:
        progress_percentage = round(min(100.0, (goal.current_amount / goal.target_amount) * 100.0), 1)
    else:
        progress_percentage = 100.0

    # Calculate estimated months
    estimated_months = None
    if goal.monthly_contribution > 0:
        estimated_months = round(remaining_amount / goal.monthly_contribution, 1)

    # Check target date feasibility
    is_realistic = True
    feasibility_notes = "Goal pace is achievable."

    try:
        target_dt = datetime.strptime(goal.target_date, "%Y-%m-%d")
        now_dt = datetime.now()
        months_until_target = max(1.0, (target_dt.year - now_dt.year) * 12 + (target_dt.month - now_dt.month))
        required_monthly = round(remaining_amount / months_until_target, 2)
    except Exception:
        months_until_target = 12.0
        required_monthly = goal.monthly_contribution

    # Compare with user's available monthly cash flow if DB session provided
    if db:
        summary = calculate_summary(db)
        monthly_surplus = max(0.0, summary.available_balance)
        if goal.monthly_contribution > monthly_surplus and monthly_surplus > 0:
            is_realistic = False
            feasibility_notes = (
                f"Planned monthly contribution (₹{goal.monthly_contribution:,.2f}) exceeds your current "
                f"monthly surplus of ₹{monthly_surplus:,.2f}. Consider saving ₹{min(monthly_surplus, required_monthly):,.2f}/mo."
            )
        elif monthly_surplus == 0 and summary.total_income > 0:
            is_realistic = False
            feasibility_notes = "Current monthly cash flow has no remaining surplus to fund this goal."
        elif required_monthly > goal.monthly_contribution and goal.monthly_contribution > 0:
            feasibility_notes = (
                f"At ₹{goal.monthly_contribution:,.2f}/month, you may finish in {estimated_months} months. "
                f"To hit target by {goal.target_date}, consider ₹{required_monthly:,.2f}/month."
            )
    else:
        if estimated_months and months_until_target < estimated_months:
            feasibility_notes = f"Target date requires ₹{required_monthly:,.2f}/month vs planned ₹{goal.monthly_contribution:,.2f}/month."

    return SavingsGoalResponse(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        monthly_contribution=goal.monthly_contribution,
        progress_percentage=progress_percentage,
        remaining_amount=remaining_amount,
        estimated_months_to_complete=estimated_months,
        is_realistic=is_realistic,
        feasibility_notes=feasibility_notes,
        created_at=goal.created_at,
    )
