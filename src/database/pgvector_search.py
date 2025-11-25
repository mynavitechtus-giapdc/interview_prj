from typing import List, Tuple, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from langchain_community.embeddings import HuggingFaceEmbeddings

from config.database import db_manager, Question
from config.settings import settings
from src.utils.logger import logger


class PgVectorSearch:
    """Search questions using pgvector in PostgreSQL"""
    
    def __init__(self):
        self.db_manager = db_manager
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model
        )
        logger.info("PgVector search initialized")
    
    def search_similar_questions(
        self, 
        query_text: str, 
        k: int = None,
        threshold: float = None
    ) -> List[Tuple[Dict, float]]:
        """
        Search for similar questions using pgvector cosine similarity
        
        Args:
            query_text: Text to search for
            k: Number of results to return
            threshold: Minimum similarity threshold (optional)
        
        Returns:
            List of (question_dict, similarity_score) tuples
        """
        k = k or settings.top_k_results
        threshold = threshold or settings.similarity_threshold
        
        session: Session = self.db_manager.get_session()
        
        try:
            # Generate embedding for query
            query_embedding = self.embeddings.embed_query(query_text)
            
            # Convert to string format for PostgreSQL
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Use cosine similarity (1 - cosine distance)
            # pgvector's <=> operator returns cosine distance (0 = identical, 2 = opposite)
            # We convert to similarity: 1 - (distance / 2)
            # Note: Using string formatting for vector literal to avoid SQLAlchemy binding issues
            query_sql = f"""
                SELECT 
                    id,
                    name,
                    answer,
                    category,
                    level,
                    1 - (embedding <=> '{embedding_str}'::vector) AS similarity
                FROM questions
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> '{embedding_str}'::vector
                LIMIT :k
            """
            
            result = session.execute(
                text(query_sql),
                {"k": k}
            )
            
            results = []
            logger.info(f"\n=== PgVector Search Results for: '{query_text}' ===")
            
            for row in result:
                similarity = float(row.similarity)
                
                question_dict = {
                    'question_id': row.id,
                    'question_text': row.name,
                    'answer': row.answer,
                    'category': row.category,
                    'level': row.level
                }
                
                results.append((question_dict, similarity))
                
                logger.info(
                    f"[{len(results)}] Similarity: {similarity:.4f} ({similarity*100:.2f}%) | "
                    f"Q: {row.name[:80]}"
                )
            
            logger.info("="*80 + "\n")
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching with pgvector: {e}", exc_info=True)
            return []
        finally:
            session.close()
    
    def search_question_with_threshold(
        self,
        query_text: str,
        k: int = None
    ) -> Tuple[Optional[Dict], Optional[float]]:
        """
        Search for similar question and return only if above threshold
        
        Returns:
            (question_dict, similarity_score) or (None, None) if below threshold
        """
        results = self.search_similar_questions(query_text, k=k)
        
        if not results:
            logger.warning("No similar questions found in database")
            return None, None
        
        best_question, similarity_score = results[0]
        
        # Check similarity threshold
        if similarity_score < settings.similarity_threshold:
            logger.warning(
                f"Similarity too low: {similarity_score:.2%} < {settings.similarity_threshold:.2%}\n"
                f"Query: '{query_text}'\n"
                f"Best match: '{best_question['question_text']}'\n"
                f"→ Treating as NEW QUESTION"
            )
            return None, None
        
        logger.info(f"Found question #{best_question['question_id']} (similarity: {similarity_score:.2%})")
        return best_question, similarity_score
    
    def get_context_for_generation(self, query_text: str, k: int = 3) -> str:
        """
        Get context from similar questions for answer generation
        
        Returns:
            Formatted context string
        """
        results = self.search_similar_questions(query_text, k=k)
        
        if not results:
            return ""
        
        context_parts = []
        for question_dict, similarity in results:
            if question_dict.get('answer'):
                context_parts.append(
                    f"Câu hỏi tương tự: {question_dict['question_text']}\n"
                    f"Câu trả lời: {question_dict['answer']}"
                )
        
        return "\n\n".join(context_parts)
