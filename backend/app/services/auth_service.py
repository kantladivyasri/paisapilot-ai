import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, User

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "nidhi-pilot-ai-secure-jwt-secret-key-at-least-32-bytes-long-2025")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

security = HTTPBearer(auto_error=False)

DEFAULT_CATEGORIES_TEMPLATE = [
    {"name": "Food & Dining", "color": "#f97316", "icon": "Utensils", "is_essential": False, "is_default": True, "budget_limit": 3000.0},
    {"name": "Rent & Housing", "color": "#6366f1", "icon": "Home", "is_essential": True, "is_default": True, "budget_limit": 8000.0},
    {"name": "Groceries", "color": "#10b981", "icon": "ShoppingBag", "is_essential": True, "is_default": True, "budget_limit": 4000.0},
    {"name": "Transportation", "color": "#06b6d4", "icon": "Car", "is_essential": True, "is_default": True, "budget_limit": 2000.0},
    {"name": "Bills & Utilities", "color": "#eab308", "icon": "Zap", "is_essential": True, "is_default": True, "budget_limit": 2500.0},
    {"name": "Education", "color": "#8b5cf6", "icon": "GraduationCap", "is_essential": True, "is_default": True, "budget_limit": 3000.0},
    {"name": "Shopping", "color": "#ec4899", "icon": "Package", "is_essential": False, "is_default": True, "budget_limit": 2500.0},
    {"name": "Healthcare", "color": "#14b8a6", "icon": "Activity", "is_essential": True, "is_default": True, "budget_limit": 1500.0},
    {"name": "Entertainment", "color": "#a855f7", "icon": "Film", "is_essential": False, "is_default": True, "budget_limit": 1500.0},
    {"name": "Miscellaneous", "color": "#64748b", "icon": "MoreHorizontal", "is_essential": False, "is_default": True, "budget_limit": 1000.0},
    {"name": "Salary", "color": "#10b981", "icon": "ArrowDownLeft", "is_essential": False, "is_default": True, "budget_limit": 0.0},
    {"name": "Freelance / Investment", "color": "#22c55e", "icon": "TrendingUp", "is_essential": False, "is_default": True, "budget_limit": 0.0},
]


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Verify plaintext password against bcrypt hash."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, username: Optional[str] = None) -> str:
    """Generate signed JWT token valid for 30 days."""
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "username": username or "",
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None


def generate_user_id() -> str:
    """Generate a clean user id."""
    return f"usr_{uuid.uuid4().hex[:12]}"


def seed_user_default_categories(db: Session, user_id: str) -> None:
    """Ensure user has the default categories seeded for budgeting and tracking."""
    existing = db.query(Category).filter(Category.user_id == user_id).first()
    if not existing:
        for cat in DEFAULT_CATEGORIES_TEMPLATE:
            db.add(
                Category(
                    user_id=user_id,
                    name=cat["name"],
                    color=cat["color"],
                    icon=cat["icon"],
                    is_essential=cat["is_essential"],
                    is_default=cat["is_default"],
                    budget_limit=cat["budget_limit"],
                )
            )
        db.commit()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolves the current user from Authorization header.
    Backward compatibility:
    If no Authorization header is provided, falls back to 'default_user'.
    If an invalid or expired token is provided, raises 401 Unauthorized.
    """
    if not credentials or not credentials.credentials:
        default_user = db.query(User).filter(User.id == "default_user").first()
        if not default_user:
            default_user = User(
                id="default_user",
                username="demo_user",
                email="demo@nidhi.pilot",
                name="Primary User",
                currency="INR",
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
        return default_user

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token does not exist",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Strict dependency: Requires a valid Authorization Bearer token.
    Raises 401 if missing or invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return get_current_user(credentials=credentials, db=db)
