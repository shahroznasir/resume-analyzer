import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True)
    role = Column(String(50))  # 'user' or 'model'
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

db_url = os.getenv("DATABASE_URL")
engine = None

if db_url:
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            pass
        print("Connected to PostgreSQL database successfully.")  # noqa # spellchecker:disable-line
    except Exception as db_conn_err:
        print(f"Failed to connect to PostgreSQL. Error: {db_conn_err}")  # noqa # spellchecker:disable-line
        print("Falling back to local SQLite database...")
        engine = None

if not engine:
    db_path = "sqlite:///conversations.db"
    engine = create_engine(db_path, connect_args={"check_same_thread": False})
    print("Using SQLite database at 'conversations.db'.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def save_message_to_db(session_id: str, role: str, content: str):
    db = SessionLocal()
    try:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        db.commit()
    except Exception as save_err:
        print(f"Error saving message to DB: {save_err}")
    finally:
        db.close()

def get_history_from_db(session_id: str):
    db = SessionLocal()
    try:
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    except Exception as hist_err:
        print(f"Error retrieving history from DB: {hist_err}")
        return []
    finally:
        db.close()
