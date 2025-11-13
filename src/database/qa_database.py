import json
from datetime import datetime
from typing import Dict, List, Optional
import os

from config.settings import settings
from src.utils.logger import logger

class QADatabase:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.database_path
        self.data = self._load_or_create_db()
    
    def _load_or_create_db(self) -> Dict:
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info("Loaded existing database")
                return data
            else:
                data = {
                    "qa_pairs": [],
                    "scores": [],
                    "metadata": [],
                    "created_at": datetime.now().isoformat()
                }
                self._save_db(data)
                logger.info("Created new database")
                return data
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            raise
    
    def _save_db(self, data: Dict = None):
        data = data or self.data
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def save_qa_pair(
        self, 
        question: str,
        answer: str, 
        reference_answer: Optional[str] = None,
        matched_question: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        qa_id = len(self.data["qa_pairs"]) + 1
        self.data["qa_pairs"].append({
            "id": qa_id,
            "question": question,
            "answer": answer,
            "reference_answer": reference_answer,
            "matched_question": matched_question,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {})
        })
        self._save_db()
        logger.info(f"Saved Q&A pair #{qa_id}: {question[:50]}...")
        return qa_id
    
    def save_score(self, question_id: int, score: int, passed: bool):
        """Lưu điểm đánh giá"""
        self.data["scores"].append({
            "question_id": question_id,
            "score": score,
            "passed": passed,
            "timestamp": datetime.now().isoformat()
        })
        self._save_db()
        logger.info(f"Saved score for question #{question_id}: {score}")
    
    def save_metadata(self, metadata: Dict):
        """Lưu metadata"""
        self.data["metadata"].append({
            "timestamp": datetime.now().isoformat(),
            **metadata
        })
        self._save_db()
    
    def get_all_qa_pairs(self) -> List[Dict]:
        """Lấy tất cả Q&A pairs"""
        return self.data["qa_pairs"]
    
    def get_statistics(self) -> Dict:
        """Lấy thống kê"""
        total_qa = len(self.data["qa_pairs"])
        total_scores = len(self.data["scores"])
        passed_count = sum(1 for s in self.data["scores"] if s["passed"])
        
        return {
            "total_qa_pairs": total_qa,
            "total_scores": total_scores,
            "passed_count": passed_count,
            "pass_rate": passed_count / total_scores if total_scores > 0 else 0
        }