import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Engine
engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """確保 pgvector 擴充套件已在 PostgreSQL 中啟用"""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            logger.info("pgvector 擴充套件已確認/啟用成功。")
    except Exception as e:
        logger.warning(f"初始化資料庫擴充套件時發生非致命錯誤 (若為首次建立連線可能需等待): {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
