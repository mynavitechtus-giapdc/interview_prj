"""
Database operations for interview sessions
"""
from typing import Optional, Dict
from sqlalchemy.orm import Session

from config.database import db_manager, InterviewSession
from src.utils.logger import logger


class SessionDatabase:
    """Database operations for interview sessions"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def save_session_summary(
        self,
        session_id: str,
        candidate_id: int,
        interviewer_id: int,
        position: str,
        total_questions: int,
        passed_questions: int,
        average_score: float,
        overall_result: str,
        strengths: str,
        weaknesses: str,
        summary: str
    ) -> int:
        """
        Save or update interview session summary
        
        Returns:
            session record id
        """
        session: Session = self.db_manager.get_session()
        
        try:
            # Check if session already exists
            existing = session.query(InterviewSession).filter(
                InterviewSession.session_id == session_id
            ).first()
            
            if existing:
                # Update existing
                existing.position = position
                existing.total_questions = total_questions
                existing.passed_questions = passed_questions
                existing.average_score = average_score
                existing.overall_result = overall_result
                existing.strengths = strengths
                existing.weaknesses = weaknesses
                existing.summary = summary
                
                session.commit()
                logger.info(f"Updated session summary for {session_id}")
                return existing.id
            else:
                # Create new
                new_session = InterviewSession(
                    session_id=session_id,
                    candidate_id=candidate_id,
                    interviewer_id=interviewer_id,
                    position=position,
                    total_questions=total_questions,
                    passed_questions=passed_questions,
                    average_score=average_score,
                    overall_result=overall_result,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    summary=summary
                )
                
                session.add(new_session)
                session.commit()
                session.refresh(new_session)
                
                logger.info(f"Created session summary for {session_id}")
                return new_session.id
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving session summary: {e}", exc_info=True)
            raise
        finally:
            session.close()
    
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get session summary by session_id"""
        session: Session = self.db_manager.get_session()
        
        try:
            record = session.query(InterviewSession).filter(
                InterviewSession.session_id == session_id
            ).first()
            
            if not record:
                return None
            
            return {
                "session_id": record.session_id,
                "candidate_id": record.candidate_id,
                "interviewer_id": record.interviewer_id,
                "position": record.position,
                "total_questions": record.total_questions,
                "passed_questions": record.passed_questions,
                "average_score": record.average_score,
                "overall_result": record.overall_result,
                "strengths": record.strengths,
                "weaknesses": record.weaknesses,
                "summary": record.summary,
                "created_at": record.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}", exc_info=True)
            return None
        finally:
            session.close()
