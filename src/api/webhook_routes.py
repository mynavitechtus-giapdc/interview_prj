"""
Webhook routes for Google Drive integration
"""
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional
from urllib.parse import urlparse

from src.services.drive_webhook_handler import DriveWebhookHandler
from src.processors.batch_processor import process_interview_batch
from src.utils.logger import logger


router = APIRouter(prefix="", tags=["webhook"])

# Lazy initialization of webhook handler
_webhook_handler = None


def get_webhook_handler():
    """Get or create webhook handler instance"""
    global _webhook_handler
    if _webhook_handler is None:
        _webhook_handler = DriveWebhookHandler()
    return _webhook_handler


@router.get("/webhook")
async def verify_webhook(
    request: Request,
    challenge: Optional[str] = None
):
    """Verify webhook endpoint for Google Drive"""
    if challenge:
        logger.info(f"Webhook verification challenge: {challenge}")
        return JSONResponse(content={"challenge": challenge})

    return {"status": "ok"}


@router.post("/webhook")
async def handle_drive_webhook(
    request: Request,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_channel_token: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_resource_uri: Optional[str] = Header(None)
):
    """Handle Google Drive webhook notifications"""
    try:
        # Log headers để debug
        logger.info("Received webhook notification")
        logger.info(f"Channel ID: {x_goog_channel_id}")
        logger.info(f"Resource State: {x_goog_resource_state}")
        logger.info(f"Resource URI: {x_goog_resource_uri}")

        # Kiểm tra resource state
        if x_goog_resource_state in {"trash", "delete"}:
            logger.info(f"Ignoring resource state: {x_goog_resource_state}")
            return {"status": "ignored", "reason": f"resource_state={x_goog_resource_state}"}

        # Lấy file ID từ resource URI
        if not x_goog_resource_uri:
            raise HTTPException(status_code=400, detail="Missing resource URI")

        try:
            parsed = urlparse(x_goog_resource_uri or "")
            file_id = parsed.path.rstrip('/').split('/')[-1] if parsed.path else None
        except Exception:
            file_id = None

        # Xử lý changes từ Drive
        webhook_handler = get_webhook_handler()
        result = webhook_handler.process_changes_since()

        if result["status"] == "success":
            logger.info(f"Successfully processed file: {result.get('file_name')}")
            logger.info(f"Interviewer: {result.get('interviewer_name', 'Unknown')}, Candidate: {result.get('candidate_name', 'Unknown')}")
            logger.info(f"Summary: {result.get('summary', '')[:100]}...")
            logger.info(f"Q&A pairs: {len(result.get('qa_pairs', []))}")
            
            # Gọi batch processor để xử lý interview
            logger.info("Starting batch processing...")
            batch_result = process_interview_batch(result)
            
            if batch_result["status"] == "success":
                logger.info(f"Batch processing completed successfully")
                logger.info(f"Session ID: {batch_result.get('session_id')}")
                logger.info(f"Overall result: {batch_result.get('overall_result')}")
                
                # Trả về kết quả kết hợp
                return JSONResponse(
                    status_code=200,
                    content={
                        "webhook_result": result,
                        "batch_processing": batch_result
                    }
                )
            else:
                logger.error(f"Batch processing failed: {batch_result.get('message')}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "webhook_result": result,
                        "batch_processing": batch_result
                    }
                )
            
        elif result["status"] == "skipped":
            logger.info(f"Skipped file: {result.get('message')}")
            return JSONResponse(
                status_code=200,
                content=result
            )
        else:
            logger.error(f"Error processing file: {result.get('message')}")
            return JSONResponse(
                status_code=500,
                content=result
            )

    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process-file/{file_id}")
async def process_file_manual(file_id: str):
    """Manually process a specific file from Google Drive"""
    try:
        logger.info(f"Manual processing request for file: {file_id}")
        webhook_handler = get_webhook_handler()
        result = webhook_handler.handle_file_created(file_id)

        if result["status"] == "success":
            # Gọi batch processor để xử lý interview
            logger.info("Starting batch processing...")
            batch_result = process_interview_batch(result)
            
            return JSONResponse(
                status_code=200 if batch_result["status"] == "success" else 500,
                content={
                    "webhook_result": result,
                    "batch_processing": batch_result
                }
            )
        
        return JSONResponse(
            status_code=200 if result["status"] == "success" else 500,
            content=result
        )
    except Exception as e:
        logger.error(f"Error in manual processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/results")
async def get_latest_results():
    """Get information about webhook results"""
    try:
        return {
            "message": "Để xem Q&A pairs, hãy kiểm tra log hoặc response JSON từ webhook/process-file endpoint",
            "note": "Q&A pairs được trả về trong response JSON khi xử lý file thành công",
            "example": {
                "status": "success",
                "interviewer_name": "...",
                "candidate_name": "...",
                "summary": "...",
                "qa_pairs": [
                    {
                        "question": "...",
                        "answer": "..."
                    }
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error getting results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
