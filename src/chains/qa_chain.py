from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from config.settings import settings
from src.utils.logger import logger

class QAChain:
    def __init__(self):
        self.llm = GoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key
        )
        
        self.template = """
            Bạn là chuyên gia phỏng vấn kỹ thuật, nhiệm vụ của bạn là tạo câu trả lời tham khảo ngắn gọn cho câu hỏi phỏng vấn.

            Câu hỏi phỏng vấn: {question}

            Ngữ cảnh từ các câu hỏi tương tự:
            {context}

            Hãy tạo câu trả lời tham khảo cho câu hỏi trên.
            
            [QUY TẮC NGHIÊM NGẶT]:
            1. **Câu trả lời phải ngắn gọn, đi thẳng vào vấn đề, và được định dạng bằng bullet points Markdown.**
            2. **KHÔNG vượt quá 150 từ** tổng cộng. Chỉ tập trung vào các điểm kỹ thuật quan trọng nhất.
            3. Phải chính xác về mặt kỹ thuật và dễ dàng để người phỏng vấn chấm điểm.

            Câu trả lời tham khảo: """
        
        self.prompt = PromptTemplate(
            template=self.template,
            input_variables=["question", "context"]
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def generate_answer(self, question: str, context: str = "") -> str:
        """Generate reference answer for question"""
        try:
            answer = self.chain.run(question=question, context=context)
            logger.info("Generated reference answer")
            return answer.strip()
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"Error: Unable to generate answer - {str(e)}"