from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Dict

from config.settings import settings
from src.utils.logger import logger

class GradingChain:
    def __init__(self):
        self.llm = GoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.2  # Low temperature for consistent grading
        )
        
        self.template = """
            Bạn là chuyên gia đánh giá phỏng vấn kỹ thuật.
            Câu hỏi: {question}
            Câu trả lời tham khảo: {reference_answer}
            Câu trả lời của ứng viên: {candidate_answer}

            TIÊU CHÍ ĐÁNH GIÁ (Thang điểm 10):
            1. Độ chính xác của kiến thức (4 điểm)
            - Thông tin có đúng không?
            - Có hiểu lầm nào không?

            2. Tính đầy đủ so với câu trả lời tham khảo (3 điểm)
            - Các điểm chính đã được đề cập chưa?
            - Có thiếu thông tin quan trọng nào không?

            3. Cách trình bày và logic (2 điểm)
            - Rõ ràng và mạch lạc
            - Dễ hiểu

            4. Ví dụ thực tế (1 điểm)
            - Có ví dụ minh họa không?
            - Ví dụ có phù hợp không?

            LƯU Ý:
            - Ứng viên KHÔNG cần trả lời dài bằng câu trả lời tham khảo
            - Miễn là các điểm chính được đề cập ngắn gọn, có thể cho điểm cao
            - Câu trả lời ngắn gọn, súc tích > câu trả lời dài nhưng lan man
            - Ngưỡng đạt: >= {passing_score} điểm

            ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
            SCORE: [0-10]
            PASSED: [YES/NO]
            FEEDBACK: [Ngắn gọn 2-3 câu: điểm mạnh, điểm yếu, gợi ý cải thiện]

            Đánh giá:
        """
        self.prompt = PromptTemplate(
            template=self.template,
            input_variables=["question", "reference_answer", "candidate_answer", "passing_score"]
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def grade(self, question: str, reference_answer: str, candidate_answer: str) -> Dict:
        try:
            # Get passing score from settings with fallback (thang điểm 10)
            passing_score = getattr(settings, 'passing_score', 6)
            
            result = self.chain.run(
                question=question,
                reference_answer=reference_answer,
                candidate_answer=candidate_answer,
                passing_score=passing_score
            )
            
            # Parse result
            lines = result.strip().split('\n')
            score = 0.0
            passed = False
            feedback = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith('SCORE:'):
                    score_str = line.replace('SCORE:', '').strip()
                    # Extract number from string (support decimal)
                    try:
                        # Try to extract float number
                        import re
                        match = re.search(r'(\d+\.?\d*)', score_str)
                        if match:
                            score = float(match.group(1))
                    except:
                        score = 0.0
                    
                elif line.startswith('PASSED:'):
                    passed = 'YES' in line.upper()
                    
                elif line.startswith('FEEDBACK:'):
                    feedback = line.replace('FEEDBACK:', '').strip()
            
            # Collect remaining feedback lines
            feedback_start = False
            feedback_lines = []
            for line in lines:
                if line.startswith('FEEDBACK:'):
                    feedback_start = True
                    feedback_lines.append(line.replace('FEEDBACK:', '').strip())
                    continue
                if feedback_start and line.strip():
                    feedback_lines.append(line.strip())
            
            if feedback_lines:
                feedback = ' '.join(feedback_lines)
            
            # Validate score (thang điểm 10)
            score = max(0.0, min(10.0, score))
            
            logger.info(f"Grading result: Score={score}/10, Passed={passed}")
            
            return {
                "score": score,
                "passed": passed,
                "feedback": feedback.strip(),
                "raw_result": result
            }
            
        except Exception as e:
            logger.error(f"Error in grading: {e}", exc_info=True)
            return {
                "score": 0.0,
                "passed": False,
                "feedback": f"Error in grading: {str(e)}",
                "raw_result": ""
            }