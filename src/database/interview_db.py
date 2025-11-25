from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from config.database import db_manager, Question, UserInteraction
from src.utils.logger import logger

class InterviewDatabase:
    def __init__(self):
        self.db_manager = db_manager
    
    def get_all_questions(self) -> List[Dict]:
        session: Session = self.db_manager.get_session()
        
        try:
            questions = session.query(Question).all()
            return [
                {
                    "id": q.id,
                    "name": q.name,
                    "answer": q.answer,
                    "category": q.category,
                    "level": q.level
                }
                for q in questions
            ]
        finally:
            session.close()
    
    def get_question_by_id(self, question_id: int) -> Optional[Dict]:
        session: Session = self.db_manager.get_session()
        
        try:
            question = session.query(Question).filter(Question.id == question_id).first()
            if question:
                return {
                    "id": question.id,
                    "name": question.name,
                    "answer": question.answer,
                    "category": question.category,
                    "level": question.level
                }
            return None
        finally:
            session.close()
    
    def add_question(self, name: str, answer: str, category: str = None, level: str = None) -> int:
        session: Session = self.db_manager.get_session()
        
        try:
            question = Question(
                name=name,
                answer=answer,
                category=category,
                level=level
            )
            session.add(question)
            session.commit()
            session.refresh(question)
            
            logger.info(f"Added question #{question.id}")
            return question.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding question: {e}")
            raise
        finally:
            session.close()
    
    def save_interaction(
        self,
        candidate_id: int,
        interviewer_id: int,
        question_id: int,
        answer_original: str,
        question_summarized: str = None,
        final_answer: str = None,
        is_passed: bool = False,
        grading_score: int = None,
        feedback: str = None,
        session_id: str = None,
        processing_time_ms: int = None
    ) -> int:
        session: Session = self.db_manager.get_session()
        
        try:
            interaction = UserInteraction(
                candidate_id=candidate_id,
                interviewer_id=interviewer_id,
                question_id=question_id,
                question_summarized=question_summarized,
                answer_original=answer_original,
                final_answer=final_answer,
                is_passed=is_passed,
                grading_score=grading_score,
                feedback=feedback,
                session_id=session_id,
                processing_time_ms=processing_time_ms
            )
            
            session.add(interaction)
            session.commit()
            session.refresh(interaction)
            
            logger.info(f"Saved interaction #{interaction.id} for candidate {candidate_id} with interviewer {interviewer_id}")
            return interaction.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving interaction: {e}")
            raise
        finally:
            session.close()
    
    def get_user_interactions(self, candidate_id: int) -> List[Dict]:
        session: Session = self.db_manager.get_session()
        
        try:
            interactions = session.query(UserInteraction).filter(
                UserInteraction.candidate_id == candidate_id
            ).order_by(UserInteraction.created_at.desc()).all()
            
            return [
                {
                    "id": i.id,
                    "question": i.question.name if i.question else i.question_summarized,
                    "answer": i.answer_original,
                    "score": i.grading_score,
                    "passed": i.is_passed,
                    "feedback": i.feedback,
                    "created_at": i.created_at.isoformat()
                }
                for i in interactions
            ]
        finally:
            session.close()
    
    def get_session_interactions(self, session_id: str) -> List[Dict]:
        session: Session = self.db_manager.get_session()
        
        try:
            interactions = session.query(UserInteraction).filter(
                UserInteraction.session_id == session_id
            ).order_by(UserInteraction.created_at).all()
            
            return [
                {
                    "question": i.question.name if i.question else i.question_summarized,
                    "answer": i.answer_original,
                    "score": i.grading_score,
                    "passed": i.is_passed
                }
                for i in interactions
            ]
        finally:
            session.close()
    
    def get_statistics(self) -> Dict:
        session: Session = self.db_manager.get_session()
        
        try:
            total_questions = session.query(Question).count()
            total_interactions = session.query(UserInteraction).count()
            total_users = session.query(func.count(func.distinct(UserInteraction.candidate_id))).scalar()
            passed_count = session.query(UserInteraction).filter(
                UserInteraction.is_passed == True
            ).count()
            
            avg_score = session.query(func.avg(UserInteraction.grading_score)).scalar() or 0
            
            return {
                "total_questions": total_questions,
                "total_interactions": total_interactions,
                "total_users": total_users,
                "passed_count": passed_count,
                "pass_rate": passed_count / total_interactions if total_interactions > 0 else 0,
                "average_score": round(float(avg_score), 2)
            }
        finally:
            session.close()
    
    def get_user_statistics(self, candidate_id: int) -> Dict:
        session: Session = self.db_manager.get_session()
        
        try:
            interactions = session.query(UserInteraction).filter(
                UserInteraction.candidate_id == candidate_id
            ).all()
            
            if not interactions:
                return {
                    "candidate_id": candidate_id,
                    "total_questions": 0,
                    "passed_count": 0,
                    "pass_rate": 0,
                    "average_score": 0
                }
            
            total = len(interactions)
            passed = sum(1 for i in interactions if i.is_passed)
            scores = [i.grading_score for i in interactions if i.grading_score is not None]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            return {
                "candidate_id": candidate_id,
                "total_questions": total,
                "passed_count": passed,
                "pass_rate": passed / total,
                "average_score": round(avg_score, 2)
            }
        finally:
            session.close()

    def get_question_answer(self, question_id: int) -> str:
        session = self.db_manager.get_session()
        
        try:
            from config.database import Question
            
            question = session.query(Question).filter(
                Question.id == question_id
            ).first()
            
            if question and question.answer:
                logger.info(f"Retrieved answer for question #{question_id}")
                return question.answer
            
            logger.warning(f"No answer found for question #{question_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting question answer: {e}")
            return None
        finally:
            session.close()