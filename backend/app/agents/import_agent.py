import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.agents.categorizer import categorize_transaction
from app.models import Category, Transaction
from app.schemas import (
    ImportAgentCommitResponse,
    ImportAgentParsedItem,
    ImportAgentPreviewResponse,
    TransactionCreate,
)

logger = logging.getLogger(__name__)

MONTH_ABBR_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def parse_date_string(text: str) -> str:
    """
    Extracts and standardizes dates from SMS/text into YYYY-MM-DD.
    Defaults to today's date if no date is found.
    """
    now = datetime.now()
    clean_lower = text.lower()

    if "yesterday" in clean_lower:
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in clean_lower:
        return now.strftime("%Y-%m-%d")

    # Pattern 1: 08-Oct-2026 or 08-Oct-26 or 08/Oct/2026
    m1 = re.search(r"\b(\d{1,2})[-/\s]([a-zA-Z]{3})[-/\s](\d{2,4})\b", text)
    if m1:
        d, mon_str, y = m1.groups()
        mon = MONTH_ABBR_MAP.get(mon_str.lower()[:3], "10")
        year = y if len(y) == 4 else f"20{y}"
        return f"{year}-{mon}-{int(d):02d}"

    # Pattern 2: YYYY-MM-DD or YYYY/MM/DD
    m2 = re.search(r"\b(20\d\d)[-/](\d{1,2})[-/](\d{1,2})\b", text)
    if m2:
        y, m, d = m2.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"

    # Pattern 3: DD-MM-YYYY or DD/MM/YYYY or DD.MM.YYYY
    m3 = re.search(r"\b(\d{1,2})[-/\.](\d{1,2})[-/\.](20\d\d|\d{2})\b", text)
    if m3:
        d, m, y = m3.groups()
        year = y if len(y) == 4 else f"20{y}"
        return f"{year}-{int(m):02d}-{int(d):02d}"

    return now.strftime("%Y-%m-%d")


def extract_amount_and_type(text: str) -> Tuple[Optional[float], str]:
    """
    Extracts transaction amount and determines if it is an expense or income.
    Returns (amount, transaction_type).
    """
    t_lower = text.lower()

    # Remove payment method names like 'credit card' before checking for credit/income direction
    direction_text = re.sub(r"\bcredit\s*card\b", "", t_lower)

    # Check for income keywords
    is_income = any(w in direction_text for w in [
        "credited", "salary", "received", "deposited", "salary credit",
        "refund", "cashback", "added to", "interest received", "cr."
    ])

    # Check for explicit expense keywords
    is_expense = any(w in t_lower for w in [
        "debited", "spent", "paid", "withdrawn", "dr.", "sent to", "transferred to", "deducted"
    ])

    if is_expense and not ("credited" in direction_text or "received" in direction_text):
        txn_type = "expense"
    elif is_income:
        txn_type = "income"
    else:
        txn_type = "expense"

    # Match currency amounts: Rs. 1,500.00 / INR 500 / ₹ 2,340.50 / 450 rs
    amount_patterns = [
        r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)",
        r"([\d,]+(?:\.\d{1,2})?)\s*(?:rs\.?|inr|₹)",
        r"(?:debited by|credited with|spent|paid|amount)\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
        r"\b([\d,]+(?:\.\d{1,2})?)\s*(?:debited|credited)\b",
    ]

    for pat in amount_patterns:
        m = re.search(pat, t_lower)
        if m:
            raw_num = m.group(1).replace(",", "")
            try:
                val = float(raw_num)
                if val > 0:
                    return round(val, 2), txn_type
            except ValueError:
                continue

    # Fallback to any standalone numbers that look like currency (e.g. 500 or 1500.00)
    num_matches = re.findall(r"\b\d{2,6}(?:\.\d{1,2})?\b", text)
    for nm in num_matches:
        try:
            val = float(nm)
            # Filter out obvious years
            if val not in [2024, 2025, 2026, 2027]:
                return round(val, 2), txn_type
        except ValueError:
            continue

    return None, txn_type


def extract_merchant_description(text: str) -> str:
    """
    Extracts the clean merchant or payee name from Indian banking alerts or raw text.
    """
    clean = text.strip()

    # 1. Match explicit narration tags first (e.g. Info: SALARY OCT 2026, Narration: Amazon)
    tag_match = re.search(r"(?:info:|narration:|desc:)\s*([A-Za-z0-9\s&'-]{3,40}?)(?:\.|\,|$|\n)", clean, re.IGNORECASE)
    if tag_match:
        extracted = tag_match.group(1).strip()
        if len(extracted) >= 2 and not re.search(r"\b(?:account|a/c)\b", extracted, re.IGNORECASE):
            return extracted.title()

    # 2. Known brand / transaction keyword match (Swiggy, Reliance Fresh, Salary, Bescom, etc.)
    brand_keywords = [
        "Swiggy", "Zomato", "Blinkit", "Zepto", "Instamart", "Bigbasket",
        "Uber", "Ola", "Rapido", "Amazon", "Flipkart", "Myntra", "Ajio",
        "D-Mart", "Reliance Fresh", "Reliance Retail", "Bescom", "Netflix", "Spotify",
        "Apollo Pharmacy", "Tata 1mg", "Bookmyshow", "PhonePe", "Google Pay",
        "Cred", "Electricity Bill", "House Rent", "Flat Rent", "Salary Credit", "Salary"
    ]
    for brand in brand_keywords:
        if re.search(rf"\b{re.escape(brand)}\b", clean, re.IGNORECASE):
            return brand

    # 3. Match "at <MERCHANT>" or "by UPI to <PAYEE>" or "paid to <PAYEE>"
    patterns = [
        r"(?:upi to|vpa to|transfer to)\s+([A-Za-z0-9\s&'-]{3,30}?)(?:\s+on|\s+ref|\.|\,|$)",
        r"(?:paid to|sent to)\s+([A-Za-z0-9\s&'-]{3,30}?)(?:\s+for|\s+via|\.|\,|$)",
        r"(?:at)\s+([A-Za-z0-9\s&'-]{3,30}?)(?:\s+on|\s+via|\s+ref|\s+by|\.|\,|$)",
        r"(?:to|towards)\s+([A-Za-z0-9\s&'-]{3,30}?)(?:\s+on|\s+via|\s+ref|\s+by|\.|\,|$)",
        r"(?:for)\s+([A-Za-z0-9\s&'-]{3,30}?)(?:\s+on|\s+via|\.|\,|$)",
    ]

    for pat in patterns:
        m = re.search(pat, clean, re.IGNORECASE)
        if m:
            extracted = m.group(1).strip()
            # If it's a bank account reference (e.g. "Account XX5432" or "A/C 1234"), skip it
            if re.search(r"\b(?:account|a/c)\b", extracted, re.IGNORECASE):
                continue
            # Clean up trailing noise
            extracted = re.sub(r"(?:ref|ref\s*no|upi\s*ref|avl\s*bal|balance|a/c).*$", "", extracted, flags=re.IGNORECASE).strip()
            if len(extracted) >= 2:
                return extracted.title()

    # 3. Fallback: Take first 40 chars sanitized
    simplified = re.sub(r"[^\w\s]", " ", clean)
    simplified = " ".join(simplified.split()[:5])
    return simplified.title() or "Unspecified Transaction"


def detect_payment_method(text: str) -> Optional[str]:
    """Detects payment channel (UPI, Credit Card, Debit Card, Net Banking)."""
    t_lower = text.lower()
    if "upi" in t_lower or "google pay" in t_lower or "gpay" in t_lower or "phonepe" in t_lower or "paytm" in t_lower:
        return "UPI"
    if "credit card" in t_lower or "cc ending" in t_lower:
        return "Credit Card"
    if "debit card" in t_lower or "dc ending" in t_lower or "atm" in t_lower:
        return "Debit Card"
    if "net banking" in t_lower or "neft" in t_lower or "rtgs" in t_lower or "imps" in t_lower:
        return "Bank Transfer"
    return "Online Payment"


class TransactionImportAgent:
    """
    Autonomous Transaction Import Agent:
    - Ingests SMS notifications, statement copies, or natural language batches.
    - Accurately identifies Merchant, Amount, Date, Category, and Direction.
    - Evaluates duplicate probability against existing records.
    - Previews or directly commits valid transactions into the SQLite database.
    """

    @classmethod
    def split_input_into_lines(cls, text: str) -> List[str]:
        """Splits raw unstructured input into individual transaction message candidates."""
        lines = []
        raw_lines = text.strip().splitlines()
        for l in raw_lines:
            sub = l.strip()
            if not sub:
                continue
            # If multiple SMS are concatenated with double periods or delimiters
            if "Dear SBI" in sub or "HDFC Bank" in sub or "ICICI Bank" in sub or "Axis Bank" in sub:
                chunks = re.split(r"(?=(?:Dear|HDFC|ICICI|Axis|Kotak|SBI|Alert:))", sub)
                for c in chunks:
                    c_clean = c.strip()
                    if len(c_clean) > 10:
                        lines.append(c_clean)
            else:
                lines.append(sub)
        return lines

    @classmethod
    def parse_single_line(cls, line: str, db: Session, user_id: str = "default_user") -> Optional[ImportAgentParsedItem]:
        """Parses a single SMS or transaction sentence into a structured transaction candidate."""
        amount, txn_type = extract_amount_and_type(line)
        if not amount or amount <= 0:
            return None

        date_str = parse_date_string(line)
        description = extract_merchant_description(line)
        category, is_essential = categorize_transaction(description, txn_type)
        pay_method = detect_payment_method(line)

        # Check for duplicates in existing database records
        is_duplicate = False
        duplicate_reason = None

        existing_match = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.date == date_str,
                Transaction.amount == amount,
                Transaction.transaction_type == txn_type,
            )
            .first()
        )

        if existing_match:
            is_duplicate = True
            duplicate_reason = (
                f"Duplicate record: exact amount ₹{amount:,.2f} on {date_str} ('{existing_match.description}')"
            )

        return ImportAgentParsedItem(
            raw_text=line,
            description=description,
            amount=amount,
            transaction_type=txn_type,
            category=category,
            is_essential=is_essential,
            date=date_str,
            confidence=0.96 if is_duplicate is False else 0.85,
            is_duplicate=is_duplicate,
            duplicate_reason=duplicate_reason,
            merchant=description,
            payment_method=pay_method,
        )

    @classmethod
    def preview_import(
        cls, text: str, db: Session, user_id: str = "default_user"
    ) -> ImportAgentPreviewResponse:
        """
        Runs the extraction pipeline without committing, returning candidates for review.
        """
        candidates = cls.split_input_into_lines(text)
        parsed_items: List[ImportAgentParsedItem] = []

        total_expenses = 0.0
        total_income = 0.0
        duplicate_count = 0

        for line in candidates:
            item = cls.parse_single_line(line, db, user_id=user_id)
            if item:
                parsed_items.append(item)
                if item.transaction_type == "expense":
                    total_expenses += item.amount
                else:
                    total_income += item.amount

                if item.is_duplicate:
                    duplicate_count += 1

        summary_notes = (
            f"Detected {len(parsed_items)} transaction(s) "
            f"({len(parsed_items) - duplicate_count} new, {duplicate_count} potential duplicates). "
            f"Total Outflow: ₹{total_expenses:,.2f}, Total Inflow: ₹{total_income:,.2f}."
        )

        return ImportAgentPreviewResponse(
            total_detected=len(parsed_items),
            parsed_transactions=parsed_items,
            total_expenses=round(total_expenses, 2),
            total_income=round(total_income, 2),
            duplicate_count=duplicate_count,
            summary_notes=summary_notes,
        )

    @classmethod
    def commit_transactions(
        cls,
        transactions: List[TransactionCreate],
        db: Session,
        user_id: str = "default_user",
        skip_duplicates: bool = True,
    ) -> ImportAgentCommitResponse:
        """
        Safely commits validated transactions to the SQLite database.
        Ensures foreign categories exist or creates them on-the-fly.
        """
        imported_count = 0
        skipped_count = 0
        total_expenses = 0.0
        total_income = 0.0
        sample_descs = []

        # Cache existing categories for this user
        existing_cats = {c.name: c for c in db.query(Category).filter(Category.user_id == user_id).all()}

        for txn in transactions:
            if skip_duplicates:
                # Double-check duplicate check
                dup = (
                    db.query(Transaction)
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.date == txn.date,
                        Transaction.amount == txn.amount,
                        Transaction.transaction_type == txn.transaction_type,
                        Transaction.description == txn.description,
                    )
                    .first()
                )
                if dup:
                    skipped_count += 1
                    continue

            # Ensure category exists
            cat_name = txn.category or "Miscellaneous"
            if cat_name not in existing_cats:
                new_cat = Category(
                    user_id=user_id,
                    name=cat_name,
                    color="#10b981",
                    icon="Tag",
                    is_essential=txn.is_essential,
                    budget_limit=0.0,
                )
                db.add(new_cat)
                db.flush()
                existing_cats[cat_name] = new_cat

            new_txn = Transaction(
                user_id=user_id,
                description=txn.description,
                amount=txn.amount,
                transaction_type=txn.transaction_type,
                category=cat_name,
                is_essential=txn.is_essential,
                date=txn.date,
                notes=txn.notes,
            )
            db.add(new_txn)
            imported_count += 1

            if txn.transaction_type == "expense":
                total_expenses += txn.amount
            else:
                total_income += txn.amount

            if len(sample_descs) < 3:
                sample_descs.append(f"{txn.description} (₹{txn.amount:,.2f})")

        db.commit()

        msg = (
            f"Successfully imported {imported_count} transaction(s)."
        )
        if skipped_count > 0:
            msg += f" {skipped_count} duplicate(s) were safely skipped."

        return ImportAgentCommitResponse(
            imported_count=imported_count,
            skipped_duplicates=skipped_count,
            total_expenses=round(total_expenses, 2),
            total_income=round(total_income, 2),
            message=msg,
            sample_descriptions=sample_descs,
        )
