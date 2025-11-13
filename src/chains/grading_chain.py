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
            You are an expert in technical interview evaluation.
            Question: {question}
            Reference Answer: {reference_answer}
            Candidate's Answer: {candidate_answer}

            EVALUATION CRITERIA:
            1. Accuracy of Knowledge (40 points)
            - Is the information correct?
            - Are there any misconceptions?

            2. Completeness compared to the reference (30 points)
            - Are the main points covered?
            - Is any important information missing?

            3. Presentation and Logic (20 points)
            - Clear and coherent
            - Easy to understand

            4. Practical Examples (10 points)
            - Are there illustrative examples?
            - Are the examples appropriate?

            NOTES:
            - The candidate does NOT need to answer as long as the reference
            - As long as the main points are covered concisely, high scores can be awarded
            - Concise, to-the-point answers > long but rambling answers
            - Pass threshold: >= {passing_score} points

            MANDATORY OUTPUT FORMAT:
            SCORE: [0-100]
            PASSED: [YES/NO]
            FEEDBACK: [Short 2-3 sentences: strengths, weaknesses, suggestions]

            Evaluation:
        """
        self.prompt = PromptTemplate(
            template=self.template,
            input_variables=["question", "reference_answer", "candidate_answer", "passing_score"]
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
    
    def grade(self, question: str, reference_answer: str, candidate_answer: str) -> Dict:
        try:
            # Get passing score from settings with fallback
            passing_score = getattr(settings, 'passing_score', 60)
            
            result = self.chain.run(
                question=question,
                reference_answer=reference_answer,
                candidate_answer=candidate_answer,
                passing_score=passing_score
            )
            
            # Parse result
            lines = result.strip().split('\n')
            score = 0
            passed = False
            feedback = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith('SCORE:'):
                    score_str = line.replace('SCORE:', '').strip()
                    # Extract number from string
                    score = int(''.join(filter(str.isdigit, score_str)))
                    
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
            
            # Validate score
            score = max(0, min(100, score))
            
            logger.info(f"Grading result: Score={score}, Passed={passed}")
            
            return {
                "score": score,
                "passed": passed,
                "feedback": feedback.strip(),
                "raw_result": result
            }
            
        except Exception as e:
            logger.error(f"Error in grading: {e}", exc_info=True)
            return {
                "score": 0,
                "passed": False,
                "feedback": f"Error in grading: {str(e)}",
                "raw_result": ""
            }