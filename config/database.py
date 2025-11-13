from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Question(Base):
    """Interview questions master table"""
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False, comment="Câu hỏi phỏng vấn")
    answer = Column(Text, nullable=False, comment="Câu trả lời mẫu")
    category = Column(String(50), comment="technical, behavioral, soft_skills")
    level = Column(String(20), comment="junior, mid, senior, all")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    interactions = relationship("UserInteraction", back_populates="question", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Question(id={self.id}, name='{self.name[:50]}...')>"


class UserInteraction(Base):
    """User interview interactions table"""
    __tablename__ = 'user_interactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True, comment="Candidate ID")
    question_id = Column(Integer, ForeignKey('questions.id', ondelete='CASCADE'), nullable=True)
    
    question_summarized = Column(Text, comment="Summarized question")
    answer_original = Column(Text, nullable=False, comment="Candidate's answer")
    final_answer = Column(Text, comment="AI generated reference answer")
    
    is_passed = Column(Boolean, default=False, comment="Pass/Fail")
    grading_score = Column(Integer, comment="Score 0-100")
    feedback = Column(Text, comment="AI feedback")
    
    session_id = Column(String(100), comment="Interview session")
    processing_time_ms = Column(Integer, comment="Processing time")
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    question = relationship("Question", back_populates="interactions")
    
    def __repr__(self):
        return f"<UserInteraction(id={self.id}, user={self.user_id}, passed={self.is_passed})>"


class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv(
            'DATABASE_URL',
            'postgresql://interview_admin:interview123@localhost:5432/interview_system'
        )
        
        self.engine = create_engine(
            self.db_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False
        )
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(self.engine)
        print(" Created all database tables")
    
    def drop_tables(self):
        """Drop all tables"""
        Base.metadata.drop_all(self.engine)
        print("  Dropped all database tables")
    
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
    
    def test_connection(self):
        """Test database connection"""
        try:
            session = self.get_session()
            session.execute(text("SELECT 1"))
            session.close()
            print(" Database connection successful")
            return True
        except Exception as e:
            print(f" Database connection failed: {e}")
            return False

db_manager = DatabaseManager()