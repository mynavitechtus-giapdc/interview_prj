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
            You are a technical interview expert tasked with creating a concise reference answer for a given interview question.

            Interview Question: {question}

            Context from similar questions:
            {context}

            Generate a reference answer for the question above.
            
            [STRICT RULES]:
            1. **The answer must be brief, directly to the point, and formatted using Markdown bullet points.**
            2. **Do NOT exceed 150 words** in total. Focus only on the most essential technical points.
            3. Must be technically accurate and easy for an interviewer to grade.

            Reference Answer: """
        
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