import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from app.agents.categorizer import categorize_transaction
from app.models import Transaction
from app.schemas import (
    CsvImportDuplicateWarning,
    CsvImportResponse,
    CsvImportRowError,
)

COLUMN_ALIASES = {
    "description": [
        "description", "narration", "particulars", "details",
        "merchant", "title", "memo", "desc", "remark", "notes"
    ],
    "amount": [
        "amount", "amt", "value", "transaction amount", "spend"
    ],
    "debit": ["debit", "withdrawal", "dr"],
    "credit": ["credit", "deposit", "cr"],
    "type": ["type", "kind", "transaction type", "trans_type", "txn_type"],
    "date": [
        "date", "txn_date", "transaction date", "booking date",
        "value date", "timestamp"
    ],
    "category": ["category", "cat", "tag", "expense category"],
}


def normalize_column_name(col: str) -> Optional[str]:
    """Matches a CSV header string to one of our standard keys."""
    clean = re.sub(r"[^a-zA-Z0-9]", "", col.lower().strip())
    for standard_key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            clean_alias = re.sub(r"[^a-zA-Z0-9]", "", alias.lower().strip())
            if clean == clean_alias:
                return standard_key
    return None


def parse_date_flexibly(val: Any) -> Optional[str]:
    """Tries parsing a date into YYYY-MM-DD format."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    if not s:
        return None

    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
        "%Y/%m/%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        # Fallback to dateutil/pandas parser
        parsed = pd.to_datetime(s, dayfirst=True)
        if not pd.isna(parsed):
            return parsed.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def parse_and_import_csv(content: bytes, filename: str, db: Session, user_id: str = "default_user") -> CsvImportResponse:
    """
    Parses CSV content safely with pandas, validates row-by-row, detects potential duplicates,
    and inserts valid records into the database.
    """
    try:
        # Try utf-8 first, fallback to latin-1
        try:
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(content), encoding="latin-1")
    except Exception as e:
        return CsvImportResponse(
            total_rows_processed=0,
            imported_count=0,
            duplicate_warning_count=0,
            error_count=1,
            warnings=[],
            errors=[CsvImportRowError(row_number=0, raw_data={}, error=f"Failed to parse CSV file: {str(e)}")],
            message="CSV parsing failed. Please verify the file format.",
        )

    if df.empty:
        return CsvImportResponse(
            total_rows_processed=0,
            imported_count=0,
            duplicate_warning_count=0,
            error_count=0,
            warnings=[],
            errors=[],
            message="CSV file is empty.",
        )

    # Map column headers
    col_mapping = {}
    for original_col in df.columns:
        normalized = normalize_column_name(str(original_col))
        if normalized:
            col_mapping[normalized] = original_col

    # Check for minimal required columns
    has_amount = "amount" in col_mapping or ("debit" in col_mapping and "credit" in col_mapping)
    has_desc = "description" in col_mapping
    has_date = "date" in col_mapping

    if not has_desc or not has_amount or not has_date:
        missing = []
        if not has_desc:
            missing.append("Description/Narration")
        if not has_amount:
            missing.append("Amount or Debit/Credit")
        if not has_date:
            missing.append("Date")
        return CsvImportResponse(
            total_rows_processed=len(df),
            imported_count=0,
            duplicate_warning_count=0,
            error_count=len(df),
            warnings=[],
            errors=[
                CsvImportRowError(
                    row_number=0,
                    raw_data={c: str(df.iloc[0][c]) for c in df.columns} if len(df) > 0 else {},
                    error=f"Missing essential columns: {', '.join(missing)}.",
                )
            ],
            message=f"Could not find required columns ({', '.join(missing)}) in the uploaded CSV.",
        )

    # Cache existing transactions to detect duplicates
    existing_records = (
        db.query(Transaction.description, Transaction.amount, Transaction.date)
        .filter(Transaction.user_id == user_id)
        .all()
    )
    existing_set = set((r[0].lower().strip(), round(r[1], 2), r[2]) for r in existing_records)

    imported_rows: List[Transaction] = []
    warnings: List[CsvImportDuplicateWarning] = []
    errors: List[CsvImportRowError] = []

    for idx, row in df.iterrows():
        row_num = idx + 1
        raw_dict = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}

        # 1. Parse description
        desc_val = str(row.get(col_mapping["description"], "")).strip()
        if not desc_val or desc_val.lower() == "nan":
            errors.append(CsvImportRowError(row_number=row_num, raw_data=raw_dict, error="Empty description"))
            continue

        # 2. Parse date
        date_str = parse_date_flexibly(row.get(col_mapping["date"]))
        if not date_str:
            errors.append(CsvImportRowError(row_number=row_num, raw_data=raw_dict, error="Invalid or missing date"))
            continue

        # 3. Parse amount and transaction type
        amount = 0.0
        txn_type = "expense"

        if "amount" in col_mapping:
            raw_amt_str = str(row.get(col_mapping["amount"], "")).replace(",", "").strip()
            try:
                raw_amt = float(raw_amt_str)
                if raw_amt < 0:
                    amount = abs(raw_amt)
                    txn_type = "expense"
                else:
                    amount = raw_amt
                    # check type column if exists
                    if "type" in col_mapping:
                        t_val = str(row.get(col_mapping["type"], "")).lower()
                        if "credit" in t_val or "income" in t_val or "cr" in t_val:
                            txn_type = "income"
                        else:
                            txn_type = "expense"
            except ValueError:
                errors.append(CsvImportRowError(row_number=row_num, raw_data=raw_dict, error="Invalid amount format"))
                continue
        elif "debit" in col_mapping and "credit" in col_mapping:
            raw_deb = str(row.get(col_mapping["debit"], "")).replace(",", "").strip()
            raw_cred = str(row.get(col_mapping["credit"], "")).replace(",", "").strip()
            
            try:
                deb_val = float(raw_deb) if raw_deb and raw_deb.lower() != "nan" else 0.0
            except ValueError:
                deb_val = 0.0

            try:
                cred_val = float(raw_cred) if raw_cred and raw_cred.lower() != "nan" else 0.0
            except ValueError:
                cred_val = 0.0

            if cred_val > 0:
                amount = cred_val
                txn_type = "income"
            elif deb_val > 0:
                amount = deb_val
                txn_type = "expense"
            else:
                errors.append(CsvImportRowError(row_number=row_num, raw_data=raw_dict, error="No debit or credit amount found"))
                continue

        if amount <= 0:
            errors.append(CsvImportRowError(row_number=row_num, raw_data=raw_dict, error="Amount must be positive"))
            continue

        amount = round(amount, 2)

        # 4. Determine category and essential status
        category = None
        if "category" in col_mapping:
            cat_val = str(row.get(col_mapping["category"], "")).strip()
            if cat_val and cat_val.lower() != "nan":
                category = cat_val

        auto_cat, is_essential = categorize_transaction(desc_val, txn_type)
        if not category:
            category = auto_cat

        # 5. Duplicate check warning
        key = (desc_val.lower().strip(), amount, date_str)
        if key in existing_set:
            warnings.append(
                CsvImportDuplicateWarning(
                    row_number=row_num,
                    description=desc_val,
                    amount=amount,
                    date=date_str,
                    warning="Potential duplicate: A transaction with identical description, amount, and date already exists.",
                )
            )

        # Create model
        t_model = Transaction(
            user_id=user_id,
            description=desc_val,
            amount=amount,
            transaction_type=txn_type,
            category=category,
            payment_method="Net Banking",
            is_essential=is_essential,
            date=date_str,
            notes=f"Imported from {filename} (Row {row_num})",
        )
        imported_rows.append(t_model)
        existing_set.add(key)  # add to prevent duplicate warnings within same file

    # Bulk insert valid rows
    if imported_rows:
        db.add_all(imported_rows)
        db.commit()

    return CsvImportResponse(
        total_rows_processed=len(df),
        imported_count=len(imported_rows),
        duplicate_warning_count=len(warnings),
        error_count=len(errors),
        warnings=warnings,
        errors=errors,
        message=f"Successfully imported {len(imported_rows)} transactions with {len(warnings)} potential duplicates warned and {len(errors)} errors.",
    )
