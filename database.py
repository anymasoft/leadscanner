# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite URL — база будет создана в текущей директории
SQLALCHEMY_DATABASE_URL = "sqlite:///./leadscanner.db"

# Создаём движок
# check_same_thread=False — необходимо для работы с SQLite в асинхронном контексте (FastAPI + APScheduler)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Создаём фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


# Зависимость для получения сессии БД в роутах
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()