import uuid
from src.processors.interview_processor import InterviewProcessor
from src.chains.session_summary_chain import SessionSummaryChain
from src.database.session_db import SessionDatabase
from src.utils.logger import logger


def process_interview_batch(json_input: dict) -> dict:
    """
    Xử lý batch interview từ webhook response
    
    Args:
        json_input: Dictionary chứa thông tin interview từ webhook
            - candidate_name: Tên ứng viên
            - interviewer_name: Tên người phỏng vấn
            - position: Vị trí ứng tuyển
            - qa_pairs: List các cặp câu hỏi-trả lời
            
    Returns:
        Dictionary chứa kết quả xử lý
    """
    try:
        processor = InterviewProcessor()
        
        # Extract data
        candidate_name = json_input.get('candidate_name', 'Unknown Candidate')
        interviewer_name = json_input.get('interviewer_name', 'Unknown Interviewer')
        qa_pairs = json_input.get('qa_pairs', [])
        session_id = str(uuid.uuid4())
        
        # Tạo hoặc lấy candidate và interviewer
        candidate_id = processor.get_or_create_user(candidate_name, 'candidate')
        interviewer_id = processor.get_or_create_user(interviewer_name, 'interviewer')
        
        print(f"\n{'='*80}")
        print(f"Session: {session_id}")
        print(f"Candidate: {candidate_name} (ID: {candidate_id})")
        print(f"Interviewer: {interviewer_name} (ID: {interviewer_id})")
        print(f"{'='*80}\n")
        
        # Process each interview
        results = []
        passed_count = 0
        total_score = 0
        
        for i, qa_pair in enumerate(qa_pairs, 1):
            question_summarized = qa_pair.get('question', '')
            candidate_answer = qa_pair.get('answer', '')
            
            print(f"[Q{i}] {question_summarized}")
            
            result = processor.process_answer(
                candidate_id=candidate_id,
                interviewer_id=interviewer_id,
                candidate_answer=candidate_answer,
                question_summarized=question_summarized,
                session_id=session_id
            )
            
            if result['status'] == 'success':
                # Kiểm tra có trong DB hay không
                question_id = result.get('question_id')
                
                if question_id:
                    # Có trong DB - hiển thị question_id
                    print(f"    ✓ Found in DB | Question ID: {question_id}")
                else:
                    # Không có trong DB - hiển thị AI summary
                    print(f"    ⚠ New Question - AI Generated")
                    print(f"    Standardized: {result['question_matched']}")
                    print(f"    Reference: {result['reference_answer'][:120]}...")
                
                print(f"    Score: {result['score']}/10 | {'✓ PASS' if result['passed'] else '✗ FAIL'}")
                print()
                
                results.append(result)
                if result['passed']:
                    passed_count += 1
                total_score += result['score']
            else:
                print(f"    ✗ Error: {result.get('message')}\n")
                results.append(result)
        
        # Summary
        avg_score = total_score / len(results) if results else 0
        pass_rate = passed_count / len(results) if results else 0
        overall_result = "pass" if avg_score >= 6.0 else "fail"
        
        print(f"{'='*80}")
        print(f"SUMMARY: {passed_count}/{len(results)} passed | Avg: {avg_score:.1f}/10 | Rate: {pass_rate:.0%}")
        print(f"{'='*80}\n")
        
        # Generate AI summary
        print("Generating AI summary...")
        summary_chain = SessionSummaryChain()
        session_db = SessionDatabase()
        
        # Prepare questions data for summary
        questions_data = []
        for result in results:
            if result.get('status') == 'success':
                questions_data.append({
                    'question': result.get('question_matched', ''),
                    'answer': result.get('your_answer', ''),
                    'score': result.get('score', 0),
                    'passed': result.get('passed', False),
                    'feedback': result.get('feedback', '')
                })
        
        # Generate summary
        position = json_input.get('position', 'N/A')
        ai_summary = summary_chain.generate_summary(
            candidate_name=candidate_name,
            position=position,
            questions_data=questions_data
        )
        
        # Save to database
        try:
            session_db.save_session_summary(
                session_id=session_id,
                candidate_id=candidate_id,
                interviewer_id=interviewer_id,
                position=position,
                total_questions=len(results),
                passed_questions=passed_count,
                average_score=avg_score,
                overall_result=overall_result,
                strengths=ai_summary['strengths'],
                weaknesses=ai_summary['weaknesses'],
                summary=ai_summary['summary']
            )
            print("✓ Session summary saved to database\n")
        except Exception as e:
            logger.error(f"Failed to save session summary: {e}")
            print(f"✗ Failed to save summary: {e}\n")
        
        # Display summary
        print(f"{'='*80}")
        print("AI SUMMARY")
        print(f"{'='*80}")
        print(f"\nĐIỂM MẠNH:")
        print(ai_summary['strengths'])
        print(f"\nĐIỂM YẾU:")
        print(ai_summary['weaknesses'])
        print(f"\nTÓM TẮT:")
        print(ai_summary['summary'])
        print(f"\n{'='*80}\n")
        
        return {
            "status": "success",
            "candidate_name": candidate_name,
            "candidate_id": candidate_id,
            "interviewer_name": interviewer_name,
            "interviewer_id": interviewer_id,
            "session_id": session_id,
            "position": position,
            "total_questions": len(results),
            "passed_count": passed_count,
            "pass_rate": pass_rate,
            "average_score": avg_score,
            "overall_result": overall_result,
            "strengths": ai_summary['strengths'],
            "weaknesses": ai_summary['weaknesses'],
            "summary": ai_summary['summary'],
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error processing batch: {e}", exc_info=True)
        print(f"\nError: {e}\n")
        return {
            "status": "error",
            "message": str(e)
        }
