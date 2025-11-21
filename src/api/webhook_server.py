from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict
import hmac
import hashlib
import json
from urllib.parse import urlparse

from src.services.drive_webhook_handler import DriveWebhookHandler
from config.settings import settings
from src.utils.logger import logger

app = FastAPI(title="Interview System Webhook Server")

# Khởi tạo handler
webhook_handler = DriveWebhookHandler()


class WebhookNotification(BaseModel):
    kind: Optional[str] = None
    id: Optional[str] = None
    resourceId: Optional[str] = None
    resourceState: Optional[str] = None
    resourceUri: Optional[str] = None
    channelId: Optional[str] = None
    expiration: Optional[str] = None


@app.get("/")
async def root():
    return {"status": "ok", "service": "Interview System Webhook Server"}


@app.get("/webhook")
async def verify_webhook(
    request: Request,
    challenge: Optional[str] = None
):
    if challenge:
        logger.info(f"Webhook verification challenge: {challenge}")
        return JSONResponse(content={"challenge": challenge})

    return {"status": "ok"}


@app.post("/webhook")
async def handle_drive_webhook(
    request: Request,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_channel_token: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_resource_uri: Optional[str] = Header(None)
):
    try:
        # Log headers để debug
        logger.info("Received webhook notification")
        logger.info(f"Channel ID: {x_goog_channel_id}")
        logger.info(f"Resource State: {x_goog_resource_state}")
        logger.info(f"Resource URI: {x_goog_resource_uri}")

        # Kiểm tra resource state
        # Xử lý cả sự kiện 'sync' để luôn quét Drive Changes từ startPageToken
        # Chỉ bỏ qua nếu là các trạng thái chắc chắn không cần xử lý
        if x_goog_resource_state in {"trash", "delete"}:
            logger.info(f"Ignoring resource state: {x_goog_resource_state}")
            return {"status": "ignored", "reason": f"resource_state={x_goog_resource_state}"}

        # Lấy file ID từ resource URI
        # Format: https://www.googleapis.com/drive/v3/files/{fileId}
        if not x_goog_resource_uri:
            raise HTTPException(status_code=400, detail="Missing resource URI")

        # Loại bỏ query (?alt=json) để lấy đúng file_id (nếu cần trong tương lai)
        try:
            parsed = urlparse(x_goog_resource_uri or "")
            file_id = parsed.path.rstrip('/').split('/')[-1] if parsed.path else None
        except Exception:
            file_id = None

        # Chiến lược dựa trên Changes API: khi có sự kiện hợp lệ, list các thay đổi từ startPageToken
        # và xử lý các file audio thuộc folder đã đăng ký.
        # Vẫn giữ xử lý trực tiếp file_id nếu cần trong tương lai.
        result = webhook_handler.process_changes_since()

        if result["status"] == "success":
            logger.info(f"Successfully processed file: {result.get('file_name')}")
            logger.info(f"Interviewer: {result.get('interviewer_name', 'Unknown')}, Candidate: {result.get('candidate_name', 'Unknown')}")
            logger.info(f"Summary: {result.get('summary', '')[:100]}...")
            logger.info(f"Q&A pairs: {len(result.get('qa_pairs', []))}")
            return JSONResponse(
                status_code=200,
                content=result
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


@app.post("/process-file/{file_id}")
async def process_file_manual(file_id: str):
    try:
        logger.info(f"Manual processing request for file: {file_id}")
        result = webhook_handler.handle_file_created(file_id)

        return JSONResponse(
            status_code=200 if result["status"] == "success" else 500,
            content=result
        )
    except Exception as e:
        logger.error(f"Error in manual processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results")
async def get_latest_results():
    try:
        # Lưu kết quả cuối cùng trong handler (cần thêm storage)
        # Tạm thời trả về hướng dẫn
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


if __name__ == "__main__":
    import uvicorn
    port = getattr(settings, 'webhook_port', 8000)
    uvicorn.run(app, host="0.0.0.0", port=port)

