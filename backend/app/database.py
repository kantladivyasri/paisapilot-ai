import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./paisapilot.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Enforce foreign key constraints, WAL mode, and busy timeout in SQLite
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations_and_seed(db_engine):
    """
    Safely applies column additions for existing SQLite databases
    and ensures standard default categories exist.
    """
    Base.metadata.create_all(bind=db_engine)

    with db_engine.connect() as conn:
        # Check SQLite table column info for transactions
        try:
            columns_res = conn.execute(text("PRAGMA table_info(transactions)")).fetchall()
            existing_cols = {row[1] for row in columns_res}

            if "payment_method" not in existing_cols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN payment_method VARCHAR(30) DEFAULT 'UPI'"))
            if "user_id" not in existing_cols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN user_id VARCHAR(50) DEFAULT 'default_user'"))
            if "updated_at" not in existing_cols:
                conn.execute(text("ALTER TABLE transactions ADD COLUMN updated_at DATETIME"))

            # Check budget_settings columns
            b_cols = conn.execute(text("PRAGMA table_info(budget_settings)")).fetchall()
            existing_b_cols = {row[1] for row in b_cols}
            if "emergency_fund_target" not in existing_b_cols:
                conn.execute(text("ALTER TABLE budget_settings ADD COLUMN emergency_fund_target FLOAT DEFAULT 0.0"))
            if "user_id" not in existing_b_cols:
                conn.execute(text("ALTER TABLE budget_settings ADD COLUMN user_id VARCHAR(50) DEFAULT 'default_user'"))
            if "updated_at" not in existing_b_cols:
                conn.execute(text("ALTER TABLE budget_settings ADD COLUMN updated_at DATETIME"))

            # Check savings_goals columns
            g_cols = conn.execute(text("PRAGMA table_info(savings_goals)")).fetchall()
            existing_g_cols = {row[1] for row in g_cols}
            if "user_id" not in existing_g_cols:
                conn.execute(text("ALTER TABLE savings_goals ADD COLUMN user_id VARCHAR(50) DEFAULT 'default_user'"))
            if "updated_at" not in existing_g_cols:
                conn.execute(text("ALTER TABLE savings_goals ADD COLUMN updated_at DATETIME"))

            conn.commit()
        except Exception as e:
            print(f"Migration notice: {e}")

    # Seed default user and default categories
    from app.models import Category, User

    session_factory = sessionmaker(bind=db_engine)
    session = session_factory()
    try:
        # Seed default user if not exists
        default_user = session.query(User).filter(User.id == "default_user").first()
        if not default_user:
            session.add(User(id="default_user", name="Primary User", currency="INR"))

        # Seed categories if none exist
        cat_count = session.query(Category).count()
        if cat_count == 0:
            defaults = [
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
            for d in defaults:
                session.add(
                    Category(
                        user_id="default_user",
                        name=d["name"],
                        color=d["color"],
                        icon=d["icon"],
                        is_essential=d["is_essential"],
                        is_default=d["is_default"],
                        budget_limit=d["budget_limit"],
                    )
                )
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Default seeding notice: {e}")
    finally:
        session.close()
