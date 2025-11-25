"""
FastAPI routes for interview system
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from src.api.interview_service import InterviewService
from src.utils.logger import logger

router = APIRouter(prefix="/api/v1", tags=["interviews"])
service = InterviewService()


@router.get("/interviews")
async def get_interviews(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    interviewer: Optional[str] = Query(None, description="Filter by interviewer name"),
    candidate: Optional[str] = Query(None, description="Filter by candidate name"),
    position: Optional[str] = Query(None, description="Filter by position"),
    result: Optional[str] = Query(None, regex="^(pass|fail)$", description="Filter by result (pass/fail)")
):
    """
    Get paginated list of interviews
    
    **Query Parameters:**
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - interviewer: Filter by interviewer name (partial match)
    - candidate: Filter by candidate name (partial match)
    - position: Filter by position
    - result: Filter by result ("pass" or "fail")
    
    **Response:**
    ```json
    {
      "totalInterview": 100,
      "totalPass": 80,
      "totalFailed": 20,
      "results": [
        {
          "id": 1,
          "session_id": "uuid-123",
          "interviewer": "Nguyễn Văn A",
          "candidate": "Trần Thị B",
          "date": "2025-11-15",
          "position": "Senior Developer",
          "overallResult": "pass",
          "overallScore": 8.5,
          "totalQuestions": 5,
          "passedQuestions": 4
        }
      ],
      "pagination": {
        "page": 1,
        "pageSize": 10,
        "totalPages": 10,
        "totalItems": 100
      }
    }
    ```
    """
    try:
        result_data = service.get_interview_list(
            page=page,
            page_size=page_size,
            interviewer_name=interviewer,
            candidate_name=candidate,
            position=position,
            result=result
        )
        return result_data
    except Exception as e:
        logger.error(f"Error in get_interviews endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interviews/{session_id}")
async def get_interview_detail(session_id: str):
    """
    Get detailed information for a specific interview session
    
    **Path Parameters:**
    - session_id: UUID of the interview session
    
    **Response:**
    ```json
    {
      "session_id": "uuid-123",
      "candidate": "Trần Thị B",
      "interviewer": "Nguyễn Văn A",
      "date": "2025-11-15 14:30:00",
      "overallScore": 8.5,
      "overallResult": "pass",
      "totalQuestions": 5,
      "passedQuestions": 4,
      "questions": [
        {
          "question": "REST và GraphQL khác nhau như thế nào?",
          "answer": "REST sử dụng nhiều endpoint...",
          "score": 8.5,
          "passed": true,
          "feedback": "Câu trả lời tốt..."
        }
      ]
    }
    ```
    """
    try:
        detail = service.get_interview_detail(session_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Interview session not found")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_interview_detail endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "interview-system"}
