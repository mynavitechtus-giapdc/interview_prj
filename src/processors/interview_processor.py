from typing import Dict, Optional, Tuple
import time
import uuid

from src.database.pgvector_search import PgVectorSearch
from src.chains.grading_chain import GradingChain
from src.chains.qa_chain import QAChain
from src.chains.summarize_chain import SummarizeChain
from src.database.interview_db import InterviewDatabase
from src.database.user_db import UserDatabase
from config.settings import settings
from src.utils.logger import logger

class InterviewProcessor:

    def __init__(self):
        self.pgvector_search = PgVectorSearch()
        self.grading_chain = GradingChain()
        self.qa_chain = QAChain()
        self.summarize_chain = SummarizeChain()
        self.database = InterviewDatabase()
        self.user_database = UserDatabase()
        logger.info("Interview processor initialized")

    def _search_question_in_vectorstore(self, question_text: str) -> Tuple[Optional[dict], Optional[float]]:
        """
        Search for similar question in pgvector database
        Only accept questions with similarity >= 80%
        """
        matched_question, similarity_score = self.pgvector_search.search_question_with_threshold(
            question_text,
            k=settings.top_k_results
        )
        
        return matched_question, similarity_score
    
    def _get_answer_from_db(self, question_id: int) -> Optional[str]:
        try:
            answer = self.database.get_question_answer(question_id)
            if answer:
                logger.info(f"Retrieved answer from DB for question #{question_id}")
                return answer
            logger.warning(f"No answer in DB for question #{question_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving answer from DB: {e}")
            return None

    def _generate_answer_with_llm(self, question_text: str) -> str:
        try:
            # Get context from similar questions using pgvector
            context = self.pgvector_search.get_context_for_generation(question_text, k=3)
            
            generated_answer = self.qa_chain.generate_answer(question_text, context)
            logger.info("Generated answer using LLM")
            return generated_answer

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise

    def _re_summarize_question(self, question: str) -> str:
        try:
            summarized = self.summarize_chain.summarize(question)
            logger.info(f"Re-summarized: '{question}' -> '{summarized}'")
            return summarized
        except Exception as e:
            logger.warning(f"Failed to re-summarize: {e}")
            return question

    def process_answer(
        self,
        candidate_id: int,
        interviewer_id: int,
        candidate_answer: str,
        question_summarized: str,
        session_id: str = None
    ) -> Dict:
        start_time = time.time()
        logger.info(f"Processing answer from candidate {candidate_id} with interviewer {interviewer_id}")
        
        # Generate session_id if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        try:
            # === STEP 1: Search in vector store ===
            matched_question, similarity_score = self._search_question_in_vectorstore(
                question_summarized
            )

            # === BRANCH 1: Question FOUND in vector store ===
            if matched_question:
                logger.info(f"[FOUND] Question #{matched_question['question_id']} matched")

                question_id = matched_question['question_id']
                question_text = matched_question['question_text']

                # Check if answer exists in DB
                reference_answer = self._get_answer_from_db(question_id)

                if reference_answer:
                    # Path: Found question + Found answer in DB
                    logger.info("[PATH] Question found → Answer in DB → Grading")
                    answer_source = "database"
                else:
                    # Path: Found question + No answer in DB → Generate with LLM
                    logger.info("[PATH] Question found → No answer in DB → Generate with LLM")
                    reference_answer = self._generate_answer_with_llm(question_text)
                    answer_source = "ai_generated"

            # === BRANCH 2: Question NOT FOUND in vector store ===
            else:
                logger.warning("[NOT FOUND] Question not found in vector store")

                # Re-summarize question
                question_re_summarized = self._re_summarize_question(question_summarized)
                logger.info(f"[PATH] Not found → Re-summarize → Generate answer with LLM")

                # Generate answer using LLM
                reference_answer = self._generate_answer_with_llm(question_re_summarized)
                answer_source = "ai_generated_new_question"

                # Use re-summarized version
                question_text = question_re_summarized
                question_id = None  # Mark as new question
                similarity_score = 0.0

            # === STEP 2: Grade the answer ===
            logger.info("Grading candidate answer...")
            grade_result = self.grading_chain.grade(
                question=question_text,
                reference_answer=reference_answer,
                candidate_answer=candidate_answer
            )

            # === STEP 3: Save interaction to database ===
            processing_time = int((time.time() - start_time) * 1000)

            interaction_id = self.database.save_interaction(
                candidate_id=candidate_id,
                interviewer_id=interviewer_id,
                question_id=question_id,
                answer_original=candidate_answer,
                question_summarized=question_summarized,
                final_answer=reference_answer,
                is_passed=grade_result["passed"],
                grading_score=grade_result["score"],
                feedback=grade_result["feedback"],
                session_id=session_id,
                processing_time_ms=processing_time
            )

            logger.info(
                f"Saved interaction #{interaction_id} | "
                f"Score: {grade_result['score']} | "
                f"Passed: {grade_result['passed']} | "
                f"Source: {answer_source}"
            )

            # === STEP 4: Return result ===
            return {
                "status": "success",
                "interaction_id": interaction_id,
                "question_id": question_id,
                "question_summarized": question_summarized,
                "question_matched": question_text,
                "your_answer": candidate_answer,
                "reference_answer": reference_answer,
                "score": grade_result["score"],
                "passed": grade_result["passed"],
                "feedback": grade_result["feedback"],
                "answer_source": answer_source,
                "similarity_score": float(similarity_score) if similarity_score else 0.0,
                "processing_time_ms": processing_time,
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"Error processing answer: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Processing failed: {str(e)}"
            }
    
    def get_user_report(self, candidate_id: int) -> Dict:
        """Get candidate's interview report"""
        stats = self.database.get_user_statistics(candidate_id)
        interactions = self.database.get_user_interactions(candidate_id)
        
        return {
            "candidate_id": candidate_id,
            "statistics": stats,
            "interactions": interactions
        }

    def get_session_report(self, session_id: str) -> Dict:
        interactions = self.database.get_session_interactions(session_id)

        if not interactions:
            return {
                "session_id": session_id,
                "total_questions": 0,
                "message": "No interactions found"
            }

        total = len(interactions)
        passed = sum(1 for i in interactions if i["passed"])
        scores = [i["score"] for i in interactions if i["score"] is not None]
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "session_id": session_id,
            "total_questions": total,
            "passed_count": passed,
            "pass_rate": passed / total,
            "average_score": round(avg_score, 2),
            "interactions": interactions
        }
    
    def get_or_create_user(self, name: str, role: str) -> int:
        return self.user_database.get_or_create_user(name, role)