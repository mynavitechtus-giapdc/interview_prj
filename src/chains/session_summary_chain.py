"""
Chain for generating interview session summary
"""
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Dict, List

from config.settings import settings
from src.utils.logger import logger


class SessionSummaryChain:
    """Generate summary for interview session"""
    
    def __init__(self):
        self.llm = GoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.3
        )
        
        self.template = """
            Bạn là chuyên gia phân tích phỏng vấn. Nhiệm vụ của bạn là tóm tắt kết quả phỏng vấn của ứng viên.

            THÔNG TIN PHỎNG VẤN:
            - Ứng viên: {candidate_name}
            - Vị trí: {position}
            - Tổng số câu hỏi: {total_questions}
            - Số câu đạt: {passed_questions}
            - Điểm trung bình: {average_score}/10

            CHI TIẾT CÁC CÂU HỎI:
            {questions_detail}

            YÊU CẦU:
            Dựa trên thông tin trên, hãy phân tích và tóm tắt:

            1. ĐIỂM MẠNH (2-3 điểm cụ thể):
            - Liệt kê các lĩnh vực/kỹ năng mà ứng viên thể hiện tốt
            - Dựa trên các câu hỏi đạt điểm cao và feedback tích cực

            2. ĐIỂM YẾU (2-3 điểm cụ thể):
            - Liệt kê các lĩnh vực/kỹ năng cần cải thiện
            - Dựa trên các câu hỏi đạt điểm thấp và feedback tiêu cực

            3. TÓM TẮT TỔNG QUAN (2-3 câu):
            - Đánh giá chung về năng lực của ứng viên
            - Khuyến nghị về việc có nên tuyển dụng hay không

            ĐỊNH DẠNG ĐẦU RA:
            STRENGTHS:
            - [Điểm mạnh 1]
            - [Điểm mạnh 2]
            - [Điểm mạnh 3]

            WEAKNESSES:
            - [Điểm yếu 1]
            - [Điểm yếu 2]
            - [Điểm yếu 3]

            SUMMARY:
            [Tóm tắt tổng quan 2-3 câu]

            Phân tích:
        """
        
        self.prompt = PromptTemplate(
            template=self.template,
            input_variables=[
                "candidate_name",
                "position",
                "total_questions",
                "passed_questions",
                "average_score",
                "questions_detail"
            ]
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def generate_summary(
        self,
        candidate_name: str,
        position: str,
        questions_data: List[Dict]
    ) -> Dict[str, str]:
        """
        Generate interview session summary
        
        Args:
            candidate_name: Tên ứng viên
            position: Vị trí ứng tuyển
            questions_data: List of dicts with keys: question, answer, score, passed, feedback
        
        Returns:
            Dict with keys: strengths, weaknesses, summary
        """
        try:
            # Calculate statistics
            total_questions = len(questions_data)
            passed_questions = sum(1 for q in questions_data if q.get('passed', False))
            scores = [q.get('score', 0) for q in questions_data if q.get('score') is not None]
            average_score = sum(scores) / len(scores) if scores else 0.0
            
            # Format questions detail
            questions_detail = ""
            for i, q in enumerate(questions_data, 1):
                questions_detail += f"\nCâu {i}:\n"
                questions_detail += f"  Q: {q.get('question', 'N/A')}\n"
                questions_detail += f"  A: {q.get('answer', 'N/A')[:100]}...\n"
                questions_detail += f"  Score: {q.get('score', 0)}/10\n"
                questions_detail += f"  Passed: {'✓' if q.get('passed') else '✗'}\n"
                questions_detail += f"  Feedback: {q.get('feedback', 'N/A')}\n"
            
            # Generate summary
            result = self.chain.run(
                candidate_name=candidate_name,
                position=position,
                total_questions=total_questions,
                passed_questions=passed_questions,
                average_score=round(average_score, 1),
                questions_detail=questions_detail
            )
            
            # Parse result
            strengths = ""
            weaknesses = ""
            summary = ""
            
            lines = result.strip().split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('STRENGTHS:'):
                    current_section = 'strengths'
                    continue
                elif line.startswith('WEAKNESSES:'):
                    current_section = 'weaknesses'
                    continue
                elif line.startswith('SUMMARY:'):
                    current_section = 'summary'
                    continue
                
                if current_section == 'strengths' and line:
                    strengths += line + '\n'
                elif current_section == 'weaknesses' and line:
                    weaknesses += line + '\n'
                elif current_section == 'summary' and line:
                    summary += line + ' '
            
            logger.info("Generated session summary successfully")
            
            return {
                "strengths": strengths.strip(),
                "weaknesses": weaknesses.strip(),
                "summary": summary.strip()
            }
            
        except Exception as e:
            logger.error(f"Error generating session summary: {e}", exc_info=True)
            return {
                "strengths": "Không thể tạo tóm tắt điểm mạnh",
                "weaknesses": "Không thể tạo tóm tắt điểm yếu",
                "summary": f"Lỗi khi tạo tóm tắt: {str(e)}"
            }
