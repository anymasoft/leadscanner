# models.py
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

SQLALCHEMY_DATABASE_URL = "sqlite:///./leadscanner.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)
    tariff = Column(String, default="free")  # free, pro, business
    max_chats = Column(Integer, default=3)   # лимит чатов
    max_keywords_per_chat = Column(Integer, default=5)

class ChatMonitor(Base):
    __tablename__ = "chat_monitors"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    chat_username = Column(String)           # @username чата
    keywords = Column(Text)                  # JSON: ["ищу бухгалтера", "нужен финансист"]
    last_message_id = Column(Integer, default=0)
    notifications_to = Column(String)        # email, telegram, webhook

Base.metadata.create_all(bind=engine)