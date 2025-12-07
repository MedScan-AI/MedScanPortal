from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Creating engine with PostgreSQL-specific settings
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Verifying connections before using them
    pool_recycle=3600,   # Recycling connections after 1 hour
    echo=False,         
    connect_args={
        "connect_timeout": 10,
        "sslmode": "require",
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency function to get database session.
    Usage in FastAPI endpoints:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()