from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Boolean
import json
import os
import uuid
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'trendspark.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


from sqlalchemy import ForeignKey

class ReportDB(Base):
    __tablename__ = "reports"

    report_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))   # 🔥 NEW
    idea_name = Column(String)
    overall_score = Column(Float)
    summary = Column(Text)
    full_json = Column(Text)

class UserDB(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)


Base.metadata.create_all(bind=engine)

def save_report(report, user_id: str):
    db = SessionLocal()
    try:
        db_report = ReportDB(
            report_id=str(uuid.uuid4()),  # ✅ FIXED
            user_id=user_id,
            idea_name=report.idea_name,
            overall_score=report.overall_score,
            summary=report.executive_summary,
            full_json=json.dumps(report.model_dump())
        )
        db.add(db_report)
        db.commit()
    finally:
        db.close()