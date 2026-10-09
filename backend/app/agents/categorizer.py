import re
from typing import Tuple

# Category rules with regex patterns tailored for Indian & modern digital transactions
CATEGORIES_RULES = [
    (
        "Salary",
        "income",
        r"\b(salary|payroll|stipend|wages|employer|direct dep|corp credit|salary credit)\b",
        False,
    ),
    (
        "Freelance",
        "income",
        r"\b(freelance|client|upwork|fiverr|consulting|invoice|retainer|project fee)\b",
        False,
    ),
    (
        "Investments",
        "income",
        r"\b(dividend|interest received|fd maturity|mutual fund redemp|stock gain)\b",
        False,
    ),
    (
        "Rent",
        "expense",
        r"\b(rent|landlord|house rent|flat rent|pg accommodation|pg rent|society maintenance|maintenance fee)\b",
        True,
    ),
    (
        "Groceries",
        "expense",
        r"\b(grocery|groceries|blinkit|zepto|instamart|bigbasket|supermarket|d-mart|dmart|vegetables|sabzi|milk|spencer|nature'?s basket|ration|kirana)\b",
        True,
    ),
    (
        "Food",
        "expense",
        r"\b(swiggy|zomato|restaurant|cafe|coffee|mcdonald|dominos|pizza|burger|kfc|starbucks|chai|dining|eats|biryani|subway|haldiram|bakery)\b",
        False,
    ),
    (
        "Electricity",
        "expense",
        r"\b(electricity|power bill|bescom|tneb|mahavitaran|bses|cesc|water bill|piped gas|lpg|indane|hp gas|bharat gas|cylinder|utility bill)\b",
        True,
    ),
    (
        "Transport",
        "expense",
        r"\b(uber|ola|rapido|metro|auto|train|irctc|petrol|diesel|fuel|shell|hpcl|bpcl|ioc|fastag|bus|redbus|flight|indigo|air india|toll)\b",
        True,
    ),
    (
        "Education",
        "expense",
        r"\b(tuition|coaching|school|college|university|udemy|coursera|books|course|exam fee|stationery|library|edtech|unacademy)\b",
        True,
    ),
    (
        "Shopping",
        "expense",
        r"\b(amazon|flipkart|myntra|ajio|zara|h&m|clothes|apparel|footwear|mall|croma|reliance digital|meesho|nykaa|tatacliq|lenskart)\b",
        False,
    ),
    (
        "Healthcare",
        "expense",
        r"\b(hospital|clinic|pharmacy|medicine|apollo|pharmeasy|1mg|tata 1mg|doctor|dentist|diagnostic|lab test|meds|netmeds|health insurance)\b",
        True,
    ),
    (
        "Entertainment",
        "expense",
        r"\b(netflix|spotify|hotstar|disney\+|prime video|pvr|inox|cinema|movie|bookmyshow|gaming|steam|playstation|youtube prem|concert|club)\b",
        False,
    ),
]

ESSENTIAL_CATEGORIES = {
    "Rent",
    "Rent & Housing",
    "Groceries",
    "Electricity",
    "Bills & Utilities",
    "Transport",
    "Transportation",
    "Education",
    "Healthcare",
    "Utilities",
}


def categorize_transaction(description: str, transaction_type: str = "expense") -> Tuple[str, bool]:
    """
    Categorizes a transaction based on description and transaction_type.
    Returns (category_name, is_essential).
    """
    clean_desc = (description or "").lower().strip()

    # Match against rule list
    for category, kind, pattern, essential in CATEGORIES_RULES:
        if transaction_type == kind and re.search(pattern, clean_desc, re.IGNORECASE):
            return category, essential

    # If kind didn't match, still check expense categories if it's an expense
    if transaction_type == "expense":
        for category, kind, pattern, essential in CATEGORIES_RULES:
            if kind == "expense" and re.search(pattern, clean_desc, re.IGNORECASE):
                return category, essential
        return "Other", False
    else:
        # Default income category
        return "Other Income", False


def is_category_essential(category: str) -> bool:
    """Returns whether the given category is considered essential by default."""
    return category in ESSENTIAL_CATEGORIES
