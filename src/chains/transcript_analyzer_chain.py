from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Dict, List
import json
import re

from config.settings import settings
from src.utils.logger import logger


class TranscriptAnalyzerChain:

    def __init__(self):
        self.llm = GoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.3  # Moderate temperature for analysis
        )

        self.analysis_template = """
You are an expert in analyzing interview transcripts. Your task is to analyze the transcript, identify participants, create a Q&A-focused summary, and extract Question-Answer pairs.

Transcript:
{transcript}

TASKS:
1. Identify the interviewer's name (người phỏng vấn) and candidate's name (ứng viên) from the transcript
2. Create a concise summary focusing ONLY on job-related / technical questions and their answers (2-3 sentences)
3. Extract all Question-Answer pairs that are about the role, skills, technical knowledge, or professional experience. Skip greetings, logistics, small talk, or unrelated chit-chat.
4. Format each Q&A pair clearly

OUTPUT FORMAT (JSON):
{{
    "interviewer_name": "Name of the interviewer (or 'Unknown' if not found)",
    "candidate_name": "Name of the candidate/interviewee (or 'Unknown' if not found)",
    "summary": "Brief summary focusing on the questions asked and answers provided (2-3 sentences about Q&A only)",
    "qa_pairs": [
        {{
            "question": "The question asked",
            "answer": "The answer given"
        }},
        {{
            "question": "Another question",
            "answer": "Another answer"
        }}
    ]
}}

IMPORTANT RULES:
- Extract ONLY Q&A pairs that relate to professional/technical assessment, job responsibilities, skills, experience, company/product, or interview expectations.
- Ignore general greetings, personal chit-chat (weather, introductions, small talk), logistical instructions, or closing remarks unless they include job-relevant content.
- If a question doesn't have a clear answer, mark the answer as "No clear answer provided"
- Keep questions and answers in their original form, but clean up filler words if needed
- The summary should ONLY focus on what questions were asked and what answers were given, not general conversation topics
- Identify names from introductions, greetings, or when people address each other
- Return ONLY valid JSON, no additional text

JSON Output:
"""

        self.prompt = PromptTemplate(
            template=self.analysis_template,
            input_variables=["transcript"]
        )

        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def analyze_transcript(self, transcript: str) -> Dict:
        try:
            logger.info("Analyzing transcript...")
            logger.info(f"Transcript length: {len(transcript)} characters")

            # Gọi LLM để phân tích
            result = self.chain.run(transcript=transcript)

            # Parse JSON từ kết quả
            parsed_result = self._parse_json_response(result)

            # Validate và clean up
            if not parsed_result:
                logger.warning("Failed to parse JSON, trying fallback method")
                return self._fallback_analysis(transcript)

            # Validate structure
            if "summary" not in parsed_result:
                parsed_result["summary"] = "Summary not available"

            if "qa_pairs" not in parsed_result or not isinstance(parsed_result["qa_pairs"], list):
                parsed_result["qa_pairs"] = []

            if "interviewer_name" not in parsed_result:
                parsed_result["interviewer_name"] = "Unknown"

            if "candidate_name" not in parsed_result:
                parsed_result["candidate_name"] = "Unknown"

            logger.info(f"Analysis completed: {len(parsed_result.get('qa_pairs', []))} Q&A pairs found")
            logger.info(f"Interviewer: {parsed_result.get('interviewer_name')}, Candidate: {parsed_result.get('candidate_name')}")

            return {
                "interviewer_name": parsed_result.get("interviewer_name", "Unknown"),
                "candidate_name": parsed_result.get("candidate_name", "Unknown"),
                "summary": parsed_result.get("summary", ""),
                "qa_pairs": parsed_result.get("qa_pairs", [])
            }

        except Exception as e:
            logger.error(f"Error analyzing transcript: {e}", exc_info=True)
            return self._fallback_analysis(transcript)

    def _parse_json_response(self, response: str) -> Dict:
        try:
            # Tìm JSON block trong response
            # Có thể có markdown code block hoặc chỉ JSON thuần
            response = response.strip()

            # Loại bỏ markdown code blocks nếu có
            if response.startswith("```"):
                # Tìm và extract JSON từ code block
                match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response, re.DOTALL)
                if match:
                    response = match.group(1)
                else:
                    # Loại bỏ ```json và ```
                    response = re.sub(r'```json\s*', '', response)
                    response = re.sub(r'```\s*', '', response)

            # Parse JSON
            parsed = json.loads(response)
            return parsed

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            logger.warning(f"Response was: {response[:500]}")

            # Thử extract JSON object manually
            try:
                # Tìm JSON object trong text
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    return json.loads(json_str)
            except:
                pass

            return None

    def _fallback_analysis(self, transcript: str) -> Dict:
        logger.info("Using fallback analysis method")

        # Tách transcript thành sentences
        sentences = re.split(r'[.!?]\s+', transcript)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Đơn giản: tìm câu hỏi (có dấu ? hoặc từ khóa câu hỏi)
        qa_pairs = []
        current_question = None
        current_answer = []

        question_keywords = ['what', 'how', 'why', 'when', 'where', 'who', 'can you', 'could you',
                           'do you', 'did you', 'have you', 'would you', 'gì', 'như thế nào',
                           'tại sao', 'khi nào', 'ở đâu', 'ai', 'bạn có']

        for sentence in sentences:
            # Kiểm tra xem có phải câu hỏi không
            is_question = '?' in sentence or any(
                sentence.lower().startswith(kw) for kw in question_keywords
            )

            if is_question:
                # Lưu Q&A pair trước đó nếu có
                if current_question:
                    qa_pairs.append({
                        "question": current_question,
                        "answer": " ".join(current_answer) if current_answer else "No clear answer provided"
                    })

                # Bắt đầu Q&A pair mới
                current_question = sentence
                current_answer = []
            else:
                # Thêm vào answer
                if current_question:
                    current_answer.append(sentence)

        # Lưu Q&A pair cuối cùng
        if current_question:
            qa_pairs.append({
                "question": current_question,
                "answer": " ".join(current_answer) if current_answer else "No clear answer provided"
            })

        # Tạo summary đơn giản (chỉ tập trung vào Q&A)
        question_previews = [q['question'][:30] for q in qa_pairs[:3] if 'question' in q]
        summary = f"Cuộc phỏng vấn gồm {len(qa_pairs)} câu hỏi và câu trả lời. " + \
                  (f"Các câu hỏi chủ yếu về: {', '.join(question_previews)}..." if question_previews else "Đã trích xuất các câu hỏi và câu trả lời.")

        # Thử tìm tên từ transcript (đơn giản)
        interviewer_name = "Unknown"
        candidate_name = "Unknown"

        # Tìm tên trong các câu giới thiệu
        intro_patterns = [
            r'(?:tôi là|tôi tên là|mình là|mình tên là)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'(?:xin chào|chào)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]

        for pattern in intro_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            if matches:
                if not candidate_name or candidate_name == "Unknown":
                    candidate_name = matches[0] if isinstance(matches[0], str) else matches[0][0]
                break

        return {
            "interviewer_name": interviewer_name,
            "candidate_name": candidate_name,
            "summary": summary,
            "qa_pairs": qa_pairs
        }

