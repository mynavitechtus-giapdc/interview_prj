from typing import Dict, Optional
import os
import tempfile
from datetime import datetime
import json
import subprocess
import glob
import shutil
import unicodedata

from src.services.google_drive_service import GoogleDriveService
from src.services.speech_to_text_service import SpeechToTextService
from src.chains.transcript_analyzer_chain import TranscriptAnalyzerChain
from src.utils.logger import logger


class DriveWebhookHandler:

    def __init__(self):
        self.drive_service = GoogleDriveService()
        self.speech_service = SpeechToTextService()
        self.transcript_analyzer = TranscriptAnalyzerChain()
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'interview_audio')
        os.makedirs(self.temp_dir, exist_ok=True)

    def handle_file_created(self, file_id: str, file_name: Optional[str] = None) -> Dict:
        try:
            logger.info(f"Processing new file: {file_id}")

            # Lấy thông tin file
            file_info = self.drive_service.get_file_info(file_id)
            if not file_info:
                return {
                    "status": "error",
                    "message": "Could not retrieve file information"
                }

            file_name = file_name or file_info.get('name', 'unknown')
            mime_type = file_info.get('mimeType', '')

            logger.info(f"File: {file_name}, Type: {mime_type}")

            # Kiểm tra media (audio hoặc video)
            if not self.drive_service.is_media_file(file_id):
                return {
                    "status": "skipped",
                    "message": f"File is not a supported media (type: {mime_type})",
                    "file_id": file_id,
                    "file_name": file_name
                }

            # Tải file về
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_extension = self._get_file_extension(mime_type)
            local_file_path = os.path.join(
                self.temp_dir,
                f"{file_name}_{timestamp}{file_extension}"
            )

            logger.info(f"Downloading file to {local_file_path}...")
            file_content = self.drive_service.download_file(file_id, local_file_path)

            if not file_content:
                return {
                    "status": "error",
                    "message": "Failed to download file"
                }

            # Chuẩn hóa về WAV 16k mono bằng ffmpeg (cho cả audio/video)
            audio_path = os.path.join(self.temp_dir, f"{file_name}_{timestamp}.wav")
            try:
                logger.info("Normalizing media to wav 16k mono via ffmpeg...")
                # ffmpeg -y -i input -vn -ac 1 -ar 16000 -acodec pcm_s16le output.wav
                subprocess.run(
                    ["ffmpeg", "-y", "-i", local_file_path, "-vn", "-ac", "1", "-ar", "16000",
                     "-acodec", "pcm_s16le", audio_path],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                logger.info(f"Audio ready at {audio_path}")
            except Exception as e:
                logger.error(f"ffmpeg convert failed: {e}")
                return {
                    "status": "error",
                    "message": f"Failed to prepare audio: {e}"
                }

            # Nếu dài > ~60s, cắt thành các đoạn 55s và ghép transcript
            chunks_dir = os.path.join(self.temp_dir, f"chunks_{timestamp}")
            os.makedirs(chunks_dir, exist_ok=True)
            chunk_pattern = os.path.join(chunks_dir, "chunk_%03d.wav")
            try:
                logger.info("Segmenting audio into 55s chunks via ffmpeg...")
                # ffmpeg -i in.wav -f segment -segment_time 55 -ar 16000 -ac 1 -c:a pcm_s16le chunk_%03d.wav
                subprocess.run(
                    ["ffmpeg", "-y", "-i", audio_path, "-f", "segment", "-segment_time", "55",
                     "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "-reset_timestamps", "1", chunk_pattern],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            except Exception as e:
                logger.error(f"ffmpeg segment failed: {e}")
                # Nếu segment lỗi, fallback: nhận toàn bộ (có thể fail nếu >60s)
                chunks = [audio_path]
            else:
                # Thu thập các chunk được tạo; nếu chỉ có 1 chunk thì vẫn dùng
                chunks = sorted(glob.glob(os.path.join(chunks_dir, "chunk_*.wav")))
                if not chunks:
                    chunks = [audio_path]

            # Chuyển đổi audio sang text (theo từng chunk nếu có)
            logger.info("Starting speech-to-text conversion...")
            transcripts: list[str] = []
            for idx, chunk_path in enumerate(chunks, 1):
                logger.info(f"Transcribing chunk {idx}/{len(chunks)}: {os.path.basename(chunk_path)}")
                piece = self.speech_service.transcribe_audio_file(
                    chunk_path,
                    language_code="vi-VN"
                )
                if piece:
                    transcripts.append(piece)
                else:
                    logger.warning(f"Empty transcript for chunk {idx}")

            transcript = " ".join(transcripts).strip()

            if not transcript:
                return {
                    "status": "error",
                    "message": "Failed to transcribe audio",
                    "file_id": file_id,
                    "file_name": file_name
                }

            # Xóa file tạm
            try:
                # Clean up temp files
                if os.path.exists(local_file_path):
                    os.remove(local_file_path)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                if os.path.isdir(chunks_dir):
                    shutil.rmtree(chunks_dir, ignore_errors=True)
            except Exception:
                pass

            # Phân tích transcript: tóm tắt và tách Q&A pairs
            logger.info("Analyzing transcript...")
            analysis_result = self.transcript_analyzer.analyze_transcript(transcript)

            qa_pairs = analysis_result.get("qa_pairs", [])
            qa_pairs = self._filter_professional_qa_pairs(qa_pairs)

            result = {
                "status": "success",
                "interviewer_name": analysis_result.get("interviewer_name", "Unknown"),
                "candidate_name": analysis_result.get("candidate_name", "Unknown"),
                "summary": analysis_result.get("summary", ""),
                "qa_pairs": qa_pairs,
                "processed_at": datetime.now().isoformat()
            }

            logger.info(f"Successfully processed file: {file_name}")
            logger.info(f"Transcript length: {len(transcript)} characters")
            logger.info(f"Interviewer: {result['interviewer_name']}, Candidate: {result['candidate_name']}")
            logger.info(f"Summary: {analysis_result.get('summary', '')[:100]}...")

            # Log chi tiết Q&A pairs
            qa_pairs = result["qa_pairs"]
            logger.info(f"Found {len(qa_pairs)} Q&A pairs")

            if qa_pairs:
                logger.info("")
                logger.info("=" * 80)
                logger.info("Q&A PAIRS:")
                logger.info("=" * 80)
                for idx, qa in enumerate(qa_pairs, 1):
                    question = qa.get('question', 'N/A') if isinstance(qa, dict) else str(qa)
                    answer = qa.get('answer', 'N/A') if isinstance(qa, dict) else 'N/A'
                    logger.info(f"[{idx}] Question: {question}")
                    logger.info(f"     Answer: {answer}")
                    logger.info("")
                logger.info("=" * 80)
            else:
                logger.warning("No Q&A pairs found in analysis result!")
                logger.info(f"Analysis result keys: {list(analysis_result.keys())}")
                logger.info(f"Analysis result: {analysis_result}")

            return result

        except Exception as e:
            logger.error(f"Error handling file created: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "file_id": file_id
            }

    def process_changes_since(self) -> Dict:
        try:
            with open('data/webhook_info.json', 'r') as f:
                info = json.load(f)
        except Exception:
            return {"status": "error", "message": "webhook_info.json not found"}

        start_token = info.get('start_page_token')
        folder_id = info.get('folder_id')
        if not start_token:
            return {"status": "error", "message": "start_page_token missing"}

        logger.info(f"Processing changes since token: {start_token}, folder_id: {folder_id}")

        service = self.drive_service.service
        changes_processed = 0
        files_processed = 0
        next_token = start_token
        last_result = None  # Lưu kết quả của file cuối cùng được xử lý thành công

        while True:
            resp = service.changes().list(
                pageToken=next_token,
                fields="changes(fileId, file(name, mimeType, parents)),nextPageToken,newStartPageToken",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()

            changes = resp.get('changes', [])
            logger.info(f"Found {len(changes)} changes in this page")

            for ch in changes:
                file = (ch.get('file') or {})
                file_id = ch.get('fileId')
                if not file_id:
                    logger.info(f"Skipping change: no fileId")
                    continue

                file_name = file.get('name', 'unknown')
                parents = file.get('parents') or []
                mime_type = file.get('mimeType', '')

                logger.info(f"Checking file: {file_name} (ID: {file_id}), mimeType: {mime_type}, parents: {parents}")

                # Kiểm tra folder_id
                if folder_id and folder_id not in parents:
                    logger.warning(f"Skipping {file_name}: not in target folder. Expected folder_id: {folder_id}, but file parents: {parents}")
                    continue

                # Kiểm tra mime_type
                if not (mime_type.startswith('audio/') or mime_type.startswith('video/')):
                    logger.warning(f"Skipping {file_name}: not audio/video (mimeType: {mime_type})")
                    continue

                logger.info(f"Processing media file: {file_name} (ID: {file_id})")
                files_processed += 1
                try:
                    result = self.handle_file_created(file_id, file_name)
                    # Lưu kết quả nếu xử lý thành công
                    if result.get("status") == "success":
                        last_result = result
                        logger.info(f"Successfully processed: {file_name}")
                    else:
                        logger.warning(f"Failed to process {file_name}: {result.get('message', 'Unknown error')}")
                except Exception:
                    self._log_exception(f"Error processing changed file: {file_id}")
                changes_processed += 1

            next_token = resp.get('nextPageToken')
            if not next_token:
                new_token = resp.get('newStartPageToken') or info.get('start_page_token')
                info['start_page_token'] = new_token
                logger.info(f"Updated start_page_token to: {new_token}")
                try:
                    with open('data/webhook_info.json', 'w') as f:
                        json.dump(info, f, indent=2)
                except Exception:
                    self._log_exception("Failed to persist new start_page_token")
                break

        logger.info(f"Changes processing complete: {changes_processed} changes, {files_processed} files processed")

        # Trả về kết quả với summary và qa_pairs từ file cuối cùng (nếu có)
        response = {
            "status": "success",
            "changes_processed": changes_processed,
            "files_processed": files_processed
        }

        # Thêm thông tin từ file cuối cùng được xử lý thành công
        if last_result:
            response.update({
                "interviewer_name": last_result.get("interviewer_name", "Unknown"),
                "candidate_name": last_result.get("candidate_name", "Unknown"),
                "summary": last_result.get("summary", ""),
                "qa_pairs": last_result.get("qa_pairs", []),
                "processed_at": last_result.get("processed_at")
            })

        return response

    def _log_exception(self, msg: str) -> None:
        try:
            logger.exception(msg)
        except Exception:
            pass

    def _filter_professional_qa_pairs(self, qa_pairs: list) -> list:
        if not qa_pairs:
            return []

        ignore_keywords = [
            "giới thiệu", "introduce", "bạn tên", "bao nhiêu tuổi", "sở thích",
            "gia đình", "ở đâu", "đến từ đâu", "sở hữu", "cảm ơn", "xin chào",
            "today", "buổi phỏng vấn", "schedule", "thời gian", "logistics"
        ]

        professional_pairs = []
        for qa in qa_pairs:
            question_raw = qa.get("question", "")
            question = question_raw.lower()
            normalized_question = self._normalize_text(question)
            if not question:
                continue
            if any(keyword in question for keyword in ignore_keywords) or \
               any(keyword in normalized_question for keyword in ignore_keywords):
                logger.info(f"Filtering out non-professional Q&A: {qa.get('question')}")
                continue
            professional_pairs.append(qa)

        return professional_pairs

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        normalized = unicodedata.normalize('NFD', text)
        return ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')
    def _get_file_extension(self, mime_type: str) -> str:
        mime_to_ext = {
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/wav': '.wav',
            'audio/wave': '.wav',
            'audio/x-wav': '.wav',
            'audio/mp4': '.m4a',
            'audio/m4a': '.m4a',
            'audio/ogg': '.ogg',
            'audio/webm': '.webm',
            'audio/flac': '.flac',
            'audio/aac': '.aac'
        }
        return mime_to_ext.get(mime_type, '.mp3')

