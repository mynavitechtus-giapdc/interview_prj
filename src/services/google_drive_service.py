from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
import io
import os
from typing import Optional, Dict, List
import pickle

from config.settings import settings
from src.utils.logger import logger


class GoogleDriveService:

    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticate()

    def _authenticate(self):
        creds = None
        token_path = 'data/token.pickle'
        credentials_path = getattr(settings, 'google_credentials_path', 'data/credentials.json')
        credentials_json = getattr(settings, 'google_credentials_json', None)

        # Kiểm tra token đã lưu
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        # Nếu không có credentials hợp lệ, yêu cầu đăng nhập
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Ưu tiên JSON trong biến môi trường nếu có
                if credentials_json:
                    try:
                        import json as _json
                        client_config = _json.loads(credentials_json)
                        flow = InstalledAppFlow.from_client_config(client_config, self.SCOPES)
                        creds = flow.run_local_server(port=0)
                    except Exception as e:
                        logger.error(f"Failed to load OAuth client from GOOGLE_CREDENTIALS_JSON: {e}")
                        raise
                else:
                    if not os.path.exists(credentials_path):
                        raise FileNotFoundError(
                            f"Credentials file not found at {credentials_path}. "
                            "Please set GOOGLE_CREDENTIALS_JSON in .env or provide credentials file."
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)

            # Lưu credentials cho lần sau
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.credentials = creds
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive service authenticated successfully")

    def get_file_info(self, file_id: str) -> Optional[Dict]:
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id,name,mimeType,createdTime,modifiedTime,size'
            ).execute()
            return file
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None

    def download_file(self, file_id: str, save_path: Optional[str] = None) -> Optional[bytes]:
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while done is False:
                status, done = downloader.next_chunk()
                logger.info(f"Download progress: {int(status.progress() * 100)}%")

            file_content.seek(0)
            content = file_content.read()

            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(content)
                logger.info(f"File saved to {save_path}")

            return content
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None

    def list_files(self, folder_id: Optional[str] = None, mime_type: Optional[str] = None) -> List[Dict]:
        try:
            query = "trashed=false"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            if mime_type:
                query += f" and mimeType='{mime_type}'"

            results = self.service.files().list(
                q=query,
                fields="files(id,name,mimeType,createdTime,modifiedTime)"
            ).execute()

            return results.get('files', [])
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    def is_audio_file(self, file_id: str) -> bool:
        file_info = self.get_file_info(file_id)
        if not file_info:
            return False

        mime_type = file_info.get('mimeType', '')
        audio_types = [
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/wave',
            'audio/x-wav', 'audio/mp4', 'audio/m4a', 'audio/ogg',
            'audio/webm', 'audio/flac', 'audio/aac'
        ]
        return mime_type in audio_types

    def is_video_file(self, file_id: str) -> bool:
        file_info = self.get_file_info(file_id)
        if not file_info:
            return False
        mime_type = file_info.get('mimeType', '')
        video_types = [
            'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska',
            'video/webm', 'video/3gpp', 'video/3gpp2'
        ]
        return mime_type in video_types or mime_type.startswith('video/')

    def is_media_file(self, file_id: str) -> bool:
        return self.is_audio_file(file_id) or self.is_video_file(file_id)

