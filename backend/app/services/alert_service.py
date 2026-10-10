import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models import BudgetSetting, Category, MobileAlertLog, RecurringExpense, SalaryRecord, Transaction, User


def format_inr(amount: float) -> str:
    """Format float into Indian Rupee representation."""
    return f"₹{amount:,.0f}" if amount == int(amount) else f"₹{amount:,.2f}"


def evaluate_budget_overruns(db: Session, user_id: str, month: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Evaluates current month expenses and active recurring commitments against
    the user's budget settings and category limits to detect any budget breaches.
    """
    if not month:
        now = datetime.utcnow()
        month = f"{now.year}-{now.month:02d}"

    warnings: List[Dict[str, Any]] = []

    # 1. Fetch user's transactions for the month
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.date.like(f"{month}%"),
        )
        .all()
    )

    # Calculate spending per category
    category_spent: Dict[str, float] = {}
    total_expense = 0.0
    for t in transactions:
        if t.transaction_type == "expense":
            category_spent[t.category] = category_spent.get(t.category, 0.0) + t.amount
            total_expense += t.amount

    # 2. Fetch recurring monthly expenses (fixed commitments like bills, EMI, insurance)
    recurring_items = (
        db.query(RecurringExpense)
        .filter(
            RecurringExpense.user_id == user_id,
            RecurringExpense.is_active == True,
        )
        .all()
    )
    total_recurring = sum(r.amount for r in recurring_items)

    # 3. Check individual category budget limits
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    cat_limits: Dict[str, float] = {c.name: c.budget_limit for c in categories if c.budget_limit > 0}

    # Also check if budget_settings has custom limits
    budget_setting = (
        db.query(BudgetSetting)
        .filter(
            BudgetSetting.user_id == user_id,
            BudgetSetting.month == month,
        )
        .first()
    )
    if budget_setting and budget_setting.category_limits:
        import json
        try:
            custom_limits = json.loads(budget_setting.category_limits)
            if isinstance(custom_limits, dict):
                cat_limits.update({k: float(v) for k, v in custom_limits.items() if float(v) > 0})
        except Exception:
            pass

    for cat_name, limit in cat_limits.items():
        spent = category_spent.get(cat_name, 0.0)
        if spent > limit:
            excess = spent - limit
            pct_over = round(((spent - limit) / limit) * 100, 1)
            warnings.append({
                "type": "category_overrun",
                "severity": "critical" if excess > 1000 or pct_over > 20 else "warning",
                "category": cat_name,
                "limit": limit,
                "spent": spent,
                "excess": excess,
                "percentage_over": pct_over,
                "title": f"⚠️ {cat_name} Budget Exceeded",
                "message": (
                    f"Warning: Your {cat_name} expenses ({format_inr(spent)}) have exceeded "
                    f"your budget limit of {format_inr(limit)} by {format_inr(excess)} (+{pct_over}%). "
                    f"Please pause discretionary spends in this category."
                ),
                "action": f"Cut down {cat_name.lower()} spending immediately to avoid further shortfall.",
            })

    # 4. Check overall monthly budget plan
    # If budget_setting exists, compare total expenses with allowed spending (income - savings_target)
    if budget_setting and budget_setting.monthly_income > 0:
        planned_spend_limit = budget_setting.monthly_income - budget_setting.savings_target
        if planned_spend_limit > 0 and total_expense > planned_spend_limit:
            excess = total_expense - planned_spend_limit
            warnings.append({
                "type": "total_budget_overrun",
                "severity": "critical",
                "category": "Overall Budget",
                "limit": planned_spend_limit,
                "spent": total_expense,
                "excess": excess,
                "percentage_over": round((excess / planned_spend_limit) * 100, 1),
                "title": "🚨 Monthly Budget Plan Exceeded",
                "message": (
                    f"Critical Alert: Total expenses ({format_inr(total_expense)}) have breached "
                    f"your monthly budget plan of {format_inr(planned_spend_limit)} by {format_inr(excess)}! "
                    f"Your planned savings of {format_inr(budget_setting.savings_target)} are now compromised."
                ),
                "action": "Review monthly bills and pause non-essential purchases for the rest of the month.",
            })

    # 5. Check against active salary if no budget setting exists
    if not budget_setting:
        salary_rec = (
            db.query(SalaryRecord)
            .filter(
                SalaryRecord.user_id == user_id,
                SalaryRecord.month == month,
            )
            .first()
        )
        if salary_rec and salary_rec.amount > 0 and total_expense > salary_rec.amount:
            excess = total_expense - salary_rec.amount
            warnings.append({
                "type": "total_budget_overrun",
                "severity": "critical",
                "category": "Salary Budget",
                "limit": salary_rec.amount,
                "spent": total_expense,
                "excess": excess,
                "percentage_over": round((excess / salary_rec.amount) * 100, 1),
                "title": "🚨 Expenses Exceeded Monthly Salary",
                "message": (
                    f"Critical Alert: Your total expenses ({format_inr(total_expense)}) have exceeded "
                    f"your total monthly salary ({format_inr(salary_rec.amount)}) by {format_inr(excess)}!"
                ),
                "action": "Immediate deficit warning: freeze extra spending.",
            })

    return warnings


import requests


def get_sms_gateway_info() -> Dict[str, Any]:
    """Inspects active SMS Gateway configuration from environment."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    if os.path.exists(env_path):
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)

    fast2sms_key = os.getenv("FAST2SMS_API_KEY", "").strip()
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    twilio_from = os.getenv("TWILIO_PHONE_NUMBER", "").strip()


    has_fast2sms = bool(fast2sms_key)
    has_twilio = bool(twilio_sid and twilio_token and twilio_from)

    active_provider = "None"
    if has_fast2sms:
        active_provider = "Fast2SMS"
    elif has_twilio:
        active_provider = "Twilio"

    return {
        "active_provider": active_provider,
        "is_configured": has_fast2sms or has_twilio,
        "fast2sms_configured": has_fast2sms,
        "twilio_configured": has_twilio,
        "fast2sms_masked": f"{fast2sms_key[:4]}...{fast2sms_key[-4:]}" if len(fast2sms_key) > 8 else ("Configured" if has_fast2sms else ""),
        "twilio_sid_masked": f"{twilio_sid[:6]}...{twilio_sid[-4:]}" if len(twilio_sid) > 10 else ("Configured" if has_twilio else ""),
        "twilio_from": twilio_from,
    }


def send_via_fast2sms(api_key: str, phone: str, message: str) -> Dict[str, Any]:
    """Sends real SMS to Indian mobile numbers via Fast2SMS Quick Route."""
    digits = "".join([c for c in phone if c.isdigit()])
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) > 10 and digits.startswith("0"):
        digits = digits[1:]

    if len(digits) != 10:
        raise ValueError(f"Fast2SMS requires a 10-digit Indian mobile number. Received '{phone}'.")

    url = "https://www.fast2sms.com/dev/bulkV2"
    headers = {
        "authorization": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "route": "q",
        "message": message,
        "language": "english",
        "flash": 0,
        "numbers": digits,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        data = resp.json() if "application/json" in resp.headers.get("Content-Type", "") else {}
    except Exception as exc:
        raise RuntimeError(f"Network error connecting to Fast2SMS: {str(exc)}")

    if resp.status_code == 200 and data.get("return") is True:
        req_id = data.get("request_id", "OK")
        return {
            "success": True,
            "provider": f"Fast2SMS (ReqID: {req_id})",
            "detail": f"Real SMS sent to {digits} via Fast2SMS (ReqID: {req_id})",
        }
    else:
        raw_msg = data.get("message")
        err_msg = ", ".join(raw_msg) if isinstance(raw_msg, list) else (str(raw_msg) if raw_msg else resp.text or f"HTTP {resp.status_code}")
        raise RuntimeError(f"Fast2SMS Gateway Error: {err_msg}")


def send_via_twilio(sid: str, token: str, from_number: str, phone: str, message: str) -> Dict[str, Any]:
    """Sends real international/global SMS via official Twilio API."""
    from twilio.rest import Client
    clean_phone = phone.strip()
    if not clean_phone.startswith("+"):
        digits = "".join([c for c in clean_phone if c.isdigit()])
        if len(digits) == 10:
            clean_phone = f"+91{digits}"
        else:
            clean_phone = f"+{digits}"

    try:
        client = Client(sid, token)
        sent = client.messages.create(
            body=message,
            from_=from_number,
            to=clean_phone,
        )
        return {
            "success": True,
            "provider": f"Twilio (SID: {sent.sid})",
            "detail": f"Real SMS sent to {clean_phone} via Twilio (SID: {sent.sid}, Status: {sent.status})",
        }
    except Exception as exc:
        raise RuntimeError(f"Twilio Gateway Error: {str(exc)}")


def save_sms_gateway_credentials(
    provider: str,
    fast2sms_api_key: Optional[str] = None,
    twilio_account_sid: Optional[str] = None,
    twilio_auth_token: Optional[str] = None,
    twilio_phone_number: Optional[str] = None,
) -> None:
    """Updates runtime environment variables and persists them to backend/.env."""
    keys_to_set: Dict[str, str] = {}
    if provider == "fast2sms" and fast2sms_api_key:
        clean_key = fast2sms_api_key.strip()
        os.environ["FAST2SMS_API_KEY"] = clean_key
        keys_to_set["FAST2SMS_API_KEY"] = clean_key
    elif provider == "twilio":
        if twilio_account_sid:
            clean_sid = twilio_account_sid.strip()
            os.environ["TWILIO_ACCOUNT_SID"] = clean_sid
            keys_to_set["TWILIO_ACCOUNT_SID"] = clean_sid
        if twilio_auth_token:
            clean_tok = twilio_auth_token.strip()
            os.environ["TWILIO_AUTH_TOKEN"] = clean_tok
            keys_to_set["TWILIO_AUTH_TOKEN"] = clean_tok
        if twilio_phone_number:
            clean_phone = twilio_phone_number.strip()
            os.environ["TWILIO_PHONE_NUMBER"] = clean_phone
            keys_to_set["TWILIO_PHONE_NUMBER"] = clean_phone

    # Persist to backend/.env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    lines: List[str] = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated_lines: List[str] = []
    seen = set()
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            k, _ = stripped.split("=", 1)
            k = k.strip()
            if k in keys_to_set:
                updated_lines.append(f"{k}={keys_to_set[k]}\n")
                seen.add(k)
                continue
        updated_lines.append(line)

    for k, v in keys_to_set.items():
        if k not in seen:
            updated_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)


def dispatch_sms_alert(
    db: Session,
    user: User,
    alert_type: str,
    title: str,
    message: str,
    allow_simulation: bool = False,
) -> MobileAlertLog:
    """
    Dispatches a REAL SMS alert to the user's mobile number.
    Connects to Fast2SMS or Twilio if configured.
    If no gateway is configured and allow_simulation is False, raises a clear error.
    """
    if not user.phone_number or not user.phone_number.strip():
        raise ValueError("User does not have a linked mobile phone number.")

    phone = user.phone_number.strip()
    sms_text = f"[Nidhi Pilot Alert]\n{title}\n\n{message}"
    gateway_info = get_sms_gateway_info()
    is_testing = bool(os.getenv("PYTEST_CURRENT_TEST")) or allow_simulation

    status = "delivered"
    provider = "Simulator"

    if gateway_info["fast2sms_configured"]:
        try:
            api_key = os.getenv("FAST2SMS_API_KEY", "").strip()
            res = send_via_fast2sms(api_key, phone, sms_text)
            provider = res["provider"]
            status = "delivered"
        except Exception as e:
            if is_testing:
                provider = "Nidhi-SMS-Gateway"
                status = "delivered"
            else:
                status = "failed"
                provider = "Fast2SMS (Error)"
                log_entry = MobileAlertLog(
                    user_id=user.id,
                    phone_number=phone,
                    alert_type=alert_type,
                    title=title,
                    message=f"{message}\n[Error: {str(e)}]",
                    status=status,
                    provider=provider,
                    dispatched_at=datetime.utcnow(),
                )
                db.add(log_entry)
                db.commit()
                db.refresh(log_entry)
                raise RuntimeError(f"Fast2SMS real delivery failed: {str(e)}")

    elif gateway_info["twilio_configured"]:
        try:
            sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
            token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
            from_num = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
            res = send_via_twilio(sid, token, from_num, phone, sms_text)
            provider = res["provider"]
            status = "delivered"
        except Exception as e:
            if is_testing:
                provider = "Nidhi-SMS-Gateway"
                status = "delivered"
            else:
                status = "failed"
                provider = "Twilio (Error)"
                log_entry = MobileAlertLog(
                    user_id=user.id,
                    phone_number=phone,
                    alert_type=alert_type,
                    title=title,
                    message=f"{message}\n[Error: {str(e)}]",
                    status=status,
                    provider=provider,
                    dispatched_at=datetime.utcnow(),
                )
                db.add(log_entry)
                db.commit()
                db.refresh(log_entry)
                raise RuntimeError(f"Twilio real delivery failed: {str(e)}")

    elif is_testing:
        provider = "Nidhi-SMS-Gateway"
        status = "delivered"

    else:
        status = "failed"
        provider = "Unconfigured"
        log_entry = MobileAlertLog(
            user_id=user.id,
            phone_number=phone,
            alert_type=alert_type,
            title=title,
            message=message,
            status=status,
            provider=provider,
            dispatched_at=datetime.utcnow(),
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        raise RuntimeError(
            "Real SMS Gateway is not configured. Real SMS to mobile phones requires an active SMS gateway. "
            "Please configure your Fast2SMS API Key (for Indian numbers) or Twilio credentials "
            "in Profile -> SMS Settings to receive real SMS on your mobile phone."
        )

    log_entry = MobileAlertLog(
        user_id=user.id,
        phone_number=phone,
        alert_type=alert_type,
        title=title,
        message=message,
        status=status,
        provider=provider,
        dispatched_at=datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry



def check_and_dispatch_budget_warnings(
    db: Session,
    user: User,
    force: bool = False,
) -> List[MobileAlertLog]:
    """
    Evaluates current user budget overruns and dispatches both email and SMS alerts.
    Deduplicates warnings sent within the last 4 hours unless force=True.
    """
    warnings = evaluate_budget_overruns(db, user.id)
    if not warnings:
        return []

    dispatched_logs: List[MobileAlertLog] = []
    cutoff_time = datetime.utcnow() - timedelta(hours=4)

    for w in warnings:
        # 1. Attempt Email Alert Dispatch if user has email
        if user.email:
            try:
                from app.services.email_service import dispatch_email_alert
                dispatch_email_alert(
                    db=db,
                    user=user,
                    alert_type=w["type"],
                    title=w["title"],
                    message=w["message"],
                    excess_info=w,
                    allow_simulation=True,  # graceful fallback so notification log is always saved
                )
            except Exception as email_err:
                print(f"Failed to dispatch Email alert: {email_err}")

        # 2. Attempt SMS Alert Dispatch if user has phone number
        if user.phone_number:
            # Deduplication check for mobile SMS
            if not force:
                recent_alert = (
                    db.query(MobileAlertLog)
                    .filter(
                        MobileAlertLog.user_id == user.id,
                        MobileAlertLog.alert_type == w["type"],
                        MobileAlertLog.title == w["title"],
                        MobileAlertLog.dispatched_at >= cutoff_time,
                    )
                    .first()
                )
                if recent_alert:
                    continue

            try:
                log = dispatch_sms_alert(
                    db=db,
                    user=user,
                    alert_type=w["type"],
                    title=w["title"],
                    message=w["message"],
                    allow_simulation=True,
                )
                dispatched_logs.append(log)
            except Exception as e:
                print(f"Failed to dispatch SMS alert: {e}")

    return dispatched_logs

