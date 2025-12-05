"""
Service layer for interview API
"""
from typing import List, Dict, Optional
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from config.database import db_manager, UserInteraction, User, InterviewSession
from src.utils.logger import logger


class InterviewService:
    """Service for interview statistics and listing"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def get_interview_list(
        self, 
        page: int = 1, 
        page_size: int = 10,
        interviewer_name: Optional[str] = None,
        candidate_name: Optional[str] = None,
        position: Optional[str] = None,
        result: Optional[str] = None  # "pass" or "fail"
    ) -> Dict:
        """
        Get paginated list of interviews with statistics
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            interviewer_name: Filter by interviewer name
            candidate_name: Filter by candidate name
            position: Filter by position (not implemented yet)
            result: Filter by result ("pass" or "fail")
        
        Returns:
            Dict with totalInterview, totalPass, totalFailed, results, pagination
        """
        session: Session = self.db_manager.get_session()
        
        try:
            # Query from InterviewSession table (much simpler!)
            query = session.query(
                InterviewSession,
                User.name.label('candidate_name')
            ).join(
                User,
                User.id == InterviewSession.candidate_id
            )
            
            # Apply filters
            if candidate_name:
                query = query.filter(User.name.ilike(f'%{candidate_name}%'))
            
            if result:
                query = query.filter(InterviewSession.overall_result == result.lower())
            
            if position:
                query = query.filter(InterviewSession.position.ilike(f'%{position}%'))
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            results = query.order_by(
                desc(InterviewSession.created_at)
            ).offset(offset).limit(page_size).all()
            
            # Format results
            formatted_results = []
            
            for idx, (sess, candidate_name_val) in enumerate(results, start=offset + 1):
                # Get interviewer name
                interviewer = session.query(User).filter(
                    User.id == sess.interviewer_id
                ).first()
                interviewer_name = interviewer.name if interviewer else "Unknown"
                
                formatted_results.append({
                    "id": idx,
                    "session_id": sess.session_id,
                    "interviewer": interviewer_name,
                    "candidate": candidate_name_val,
                    "date": sess.created_at.strftime("%Y-%m-%d"),
                    "position": sess.position or "N/A",
                    "overallResult": sess.overall_result,
                    "overallScore": round(sess.average_score, 1) if sess.average_score else 0.0,
                    "totalQuestions": sess.total_questions,
                    "passedQuestions": sess.passed_questions or 0
                })
            
            # Calculate total statistics
            all_sessions = session.query(InterviewSession).all()
            total_pass_all = sum(1 for s in all_sessions if s.overall_result == 'pass')
            total_failed_all = len(all_sessions) - total_pass_all
            
            return {
                "totalInterview": total_count,
                "totalPass": total_pass_all,
                "totalFailed": total_failed_all,
                "results": formatted_results,
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "totalPages": (total_count + page_size - 1) // page_size,
                    "totalItems": total_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting interview list: {e}", exc_info=True)
            raise
        finally:
            session.close()
    
    def get_interview_detail(self, session_id: str) -> Optional[Dict]:
        """Get detailed information for a specific interview session"""
        session: Session = self.db_manager.get_session()
        
        try:
            # Get session summary
            session_record = session.query(InterviewSession).filter(
                InterviewSession.session_id == session_id
            ).first()
            
            if not session_record:
                return None
            
            # Get candidate and interviewer
            candidate = session.query(User).filter(
                User.id == session_record.candidate_id
            ).first()
            interviewer = session.query(User).filter(
                User.id == session_record.interviewer_id
            ).first()
            
            # Get interactions
            interactions = session.query(UserInteraction).filter(
                UserInteraction.session_id == session_id
            ).all()
            
            # Format questions
            questions = []
            for i in interactions:
                questions.append({
                    "question": i.question.name if i.question_id and i.question else i.question_summarized or "N/A",
                    "answer": i.answer_original,
                    "correctAnswer": i.final_answer,
                    "score": i.grading_score,
                    "passed": i.is_passed,
                    "feedback": i.feedback
                })
            
            return {
                "session_id": session_id,
                "candidate": candidate.name if candidate else "Unknown",
                "interviewer": interviewer.name if interviewer else "Unknown",
                "position": session_record.position or "N/A",
                "date": session_record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "overallScore": round(session_record.average_score, 1) if session_record.average_score else 0.0,
                "overallResult": session_record.overall_result,
                "totalQuestions": session_record.total_questions,
                "passedQuestions": session_record.passed_questions,
                "strengths": session_record.strengths,
                "weaknesses": session_record.weaknesses,
                "summary": session_record.summary,
                "questions": questions
            }
            
        except Exception as e:
            logger.error(f"Error getting interview detail: {e}", exc_info=True)
            raise
        finally:
            session.close()
