from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from config.settings import settings
from src.utils.logger import logger

class SummarizeChain:
    def __init__(self):
        self.llm = GoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.1  # Low temperature for consistent summarization
        )
        
        self.template = """
            Bạn là chuyên gia chuẩn hóa câu hỏi phỏng vấn.

            Câu hỏi gốc: {question}

            Nhiệm vụ: Tóm tắt câu hỏi thành định dạng NGẮN GỌN, RÕ RÀNG, giữ nguyên ý nghĩa cốt lõi.

            Quy tắc:
            - Loại bỏ từ thừa và cụm từ dài dòng.
            - Giữ lại các từ khóa kỹ thuật quan trọng.
            - Chuyển đổi thành định dạng câu hỏi chuẩn.
            - Không thêm thông tin mới.
            - **NGHIÊM NGẶT TỐI ĐA 1 câu, khoảng 15-20 từ.**

            Ví dụ:
            Input: "Em muốn hỏi là, kiểu như, sự khác nhau giữa var, let và const trong JavaScript là gì ạ?"
            Output: "Sự khác nhau giữa var, let và const trong JavaScript là gì?"

            Input: "Anh có thể giải thích cho em về sự khác biệt chính giữa REST API và GraphQL được không ạ?"
            Output: "REST API và GraphQL khác nhau như thế nào?"

            Input: "Docker là gì và khi nào chúng ta nên sử dụng nó trong môi trường production?"
            Output: "Docker là gì và khi nào nên sử dụng trong production?"

            Câu hỏi chuẩn hóa:"""
        
        self.prompt = PromptTemplate(
            template=self.template,
            input_variables=["question"]
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def summarize(self, question: str) -> str:
        """Summarize and normalize question"""
        try:
            summarized = self.chain.run(question=question)
            result = summarized.strip()
            
            # Fallback if result is too long or empty
            if not result or len(result) > len(question) * 1.5:
                logger.warning("Summarization failed, using original question")
                return question
            
            logger.info(f"Summarized: '{question}' -> '{result}'")
            return result
            
        except Exception as e:
            logger.error(f"Error in summarization: {e}")
            return question  # Fallback to original