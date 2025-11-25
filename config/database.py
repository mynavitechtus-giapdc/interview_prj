from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class User(Base):
    """Users table"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="Tên người dùng")
    role = Column(String(50), nullable=False, default='candidate', comment="Role: interviewer hoặc candidate")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interviews_conducted = relationship(
        "UserInteraction", 
        foreign_keys="UserInteraction.interviewer_id",
        back_populates="interviewer"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', role='{self.role}')>"


class Question(Base):
    """Interview questions master table"""
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False, comment="Câu hỏi phỏng vấn")
    answer = Column(Text, nullable=False, comment="Câu trả lời mẫu")
    category = Column(String(50), comment="technical, behavioral, soft_skills")
    level = Column(String(20), comment="junior, mid, senior, all")
    embedding = Column(Vector(384), comment="Vector embedding for semantic search")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    interactions = relationship("UserInteraction", back_populates="question", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Question(id={self.id}, name='{self.name[:50]}...')>"


class InterviewSession(Base):
    """Interview session summary table"""
    __tablename__ = 'interview_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True, comment="UUID của buổi phỏng vấn")
    candidate_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    interviewer_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    position = Column(String(100), comment="Vị trí ứng tuyển")
    
    total_questions = Column(Integer, comment="Tổng số câu hỏi")
    passed_questions = Column(Integer, comment="Số câu hỏi đạt")
    average_score = Column(Float, comment="Điểm trung bình")
    overall_result = Column(String(20), comment="pass/fail")
    
    strengths = Column(Text, comment="Điểm mạnh của ứng viên")
    weaknesses = Column(Text, comment="Điểm yếu của ứng viên")
    summary = Column(Text, comment="Tóm tắt tổng quan")
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("User", foreign_keys=[candidate_id])
    interviewer = relationship("User", foreign_keys=[interviewer_id])
    
    def __repr__(self):
        return f"<InterviewSession(session_id='{self.session_id}', result='{self.overall_result}')>"


class UserInteraction(Base):
    """User interview interactions table"""
    __tablename__ = 'user_interactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True, comment="ID ứng viên")
    interviewer_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True, comment="ID người phỏng vấn")
    question_id = Column(Integer, ForeignKey('questions.id', ondelete='CASCADE'), nullable=True)
    
    question_summarized = Column(Text, comment="Summarized question")
    answer_original = Column(Text, nullable=False, comment="Candidate's answer")
    final_answer = Column(Text, comment="AI generated reference answer")
    
    is_passed = Column(Boolean, default=False, comment="Pass/Fail")
    grading_score = Column(Float, comment="Score 0-10")
    feedback = Column(Text, comment="AI feedback")
    
    session_id = Column(String(100), comment="Interview session")
    processing_time_ms = Column(Integer, comment="Processing time")
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    question = relationship("Question", back_populates="interactions")
    candidate = relationship(
        "User",
        foreign_keys=[candidate_id],
        backref="candidate_interactions"
    )
    interviewer = relationship(
        "User",
        foreign_keys=[interviewer_id],
        back_populates="interviews_conducted"
    )
    
    def __repr__(self):
        return f"<UserInteraction(id={self.id}, candidate_id={self.candidate_id}, interviewer_id={self.interviewer_id}, passed={self.is_passed})>"


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
        # Enable pgvector extension
        try:
            session = self.get_session()
            session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            session.commit()
            session.close()
            print(" Enabled pgvector extension")
        except Exception as e:
            print(f" Warning: Could not enable pgvector extension: {e}")
        
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