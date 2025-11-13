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
            You are an expert in standardizing interview questions.

            Original Question: {question}

            Task: Summarize the question into a CONCISE, CLEAR format, preserving the core meaning.

            Rules:
            - Eliminate filler words and redundant phrases.
            - Retain important technical keywords.
            - Convert the input into a standard question format.
            - Do not introduce new information.
            - **STRICTLY MAX 1 sentence, around 15-20 words.**

            Examples:
            Input: "I wanna ask, like, what's the difference between var, let, and const in JavaScript, please?"
            Output: "What is the difference between var, let, and const in JavaScript?"

            Input: "Could you possibly explain to me the main differences between REST API and GraphQL?"
            Output: "How do REST API and GraphQL differ?"

            Input: "What is docker and when should we use it in production?"
            Output: "What is Docker and when should it be used in production?"

            Standardized Question:"""
        
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