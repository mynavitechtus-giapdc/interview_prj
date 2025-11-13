import json
import uuid
from src.processors.interview_processor import InterviewProcessor
from src.utils.logger import logger

# Mock JSON input
MOCK_JSON_INPUT = {
    "user_id": "candidate_001",
    "session_id": None,
    "interviews": [
        {
            "question_summarized": "How do you handle conflicts within your team?",
            "candidate_answer": "I **actively listen** to all sides and determine the **root cause** of the conflict. I prioritize **data-driven, objective solutions** over personal opinions. The focus is always on communication, empathy, and aligning the team toward the **common project goal."
        }
    ]
}


def process_interview_batch(json_input: dict) -> dict:
    try:
        # Initialize
        print("\nInitializing processor...")
        processor = InterviewProcessor()
        
        # Extract data
        user_id = json_input.get('user_id', 'unknown_user')
        session_id = json_input.get('session_id') or str(uuid.uuid4())
        interviews = json_input.get('interviews', [])
        
        print(f"User ID: {user_id}")
        print(f"Session ID: {session_id}")
        print(f"Total questions: {len(interviews)}")
        
        # Process each interview
        results = []
        passed_count = 0
        total_score = 0
        
        print("\n" + "-"*80)
        print("PROCESSING INTERVIEWS...")
        print("-"*80 + "\n")
        
        for i, interview in enumerate(interviews, 1):
            print(f"[{i}/{len(interviews)}] Processing...")
            
            result = processor.process_answer(
                user_id=user_id,
                candidate_answer=interview['candidate_answer'],
                question_summarized=interview['question_summarized'],
                session_id=session_id
            )
            
            if result['status'] == 'success':
                print(f"  Question: {result['question_matched']}")
                print(f"  Answer: {interview['candidate_answer'][:80]}...")
                print(f"  Score: {result['score']}/100")
                print(f"  Result: {'PASS' if result['passed'] else 'FAIL'}")
                print(f"  Source: {result['answer_source']}")
                print(f"  Similarity: {result['similarity_score']:.2%}")
                
                results.append(result)
                if result['passed']:
                    passed_count += 1
                total_score += result['score']
            else:
                print(f"  Error: {result.get('message')}")
                results.append(result)
            
            print("-"*80 + "\n")
        
        # Summary
        avg_score = total_score / len(results) if results else 0
        pass_rate = passed_count / len(results) if results else 0
        
        print("="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total Questions: {len(results)}")
        print(f"Passed: {passed_count}/{len(results)}")
        print(f"Pass Rate: {pass_rate:.1%}")
        print(f"Average Score: {avg_score:.1f}/100")
        print("="*80 + "\n")
        
        return {
            "status": "success",
            "user_id": user_id,
            "session_id": session_id,
            "total_questions": len(results),
            "passed_count": passed_count,
            "pass_rate": pass_rate,
            "average_score": avg_score,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error processing batch: {e}", exc_info=True)
        print(f"\nError: {e}\n")
        return {
            "status": "error",
            "message": str(e)
        }


def main():
    """Main function"""
    
    print("\n" + "="*80)
    print("EXTERNAL SERVICE SIMULATION")
    print("="*80)
    print("\nReceived JSON input:")
    print(json.dumps(MOCK_JSON_INPUT, indent=2, ensure_ascii=False))
    print("\n" + "="*80)
    
    # Process
    result = process_interview_batch(MOCK_JSON_INPUT)
    
    # Output
    print("\n" + "="*80)
    print("OUTPUT JSON:")
    print("="*80)
    print(json.dumps({
        "status": result["status"],
        "user_id": result["user_id"],
        "session_id": result["session_id"],
        "summary": {
            "total_questions": result["total_questions"],
            "passed_count": result["passed_count"],
            "pass_rate": result["pass_rate"],
            "average_score": result["average_score"]
        }
    }, indent=2, ensure_ascii=False))
    print("="*80 + "\n")


if __name__ == "__main__":
    main()