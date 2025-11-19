from google.cloud import speech
from google.oauth2 import service_account
import io
from typing import Optional, Dict
import os
from typing import Optional as TypingOptional

from config.settings import settings
from src.utils.logger import logger


class SpeechToTextService:

    def __init__(self):
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            # Kiểm tra credentials từ JSON hoặc file
            credentials_path = getattr(settings, 'google_cloud_credentials_path', None)
            credentials_json = getattr(settings, 'google_cloud_credentials_json', None)

            if credentials_json:
                try:
                    import json as _json
                    info = _json.loads(credentials_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        info,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    self.client = speech.SpeechClient(credentials=credentials)
                except Exception as e:
                    logger.error(f"Failed to load service account from GOOGLE_CLOUD_CREDENTIALS_JSON: {e}")
                    raise
            elif credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.client = speech.SpeechClient(credentials=credentials)
            elif hasattr(settings, 'google_api_key') and settings.google_api_key:
                # Sử dụng API key nếu có (cho Speech-to-Text API v1)
                self.client = speech.SpeechClient()
            else:
                # Thử sử dụng default credentials
                self.client = speech.SpeechClient()

            logger.info("Google Speech-to-Text client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Speech-to-Text client: {e}")
            raise

    def transcribe_audio_file(self, audio_file_path: str, language_code: str = "vi-VN") -> Optional[str]:
        try:
            with io.open(audio_file_path, "rb") as audio_file:
                content = audio_file.read()

            return self.transcribe_audio_bytes(content, language_code)
        except Exception as e:
            logger.error(f"Error reading audio file: {e}")
            return None

    def transcribe_audio_bytes(self, audio_bytes: bytes, language_code: str = "vi-VN",
                              encoding: TypingOptional[speech.RecognitionConfig.AudioEncoding] = None) -> Optional[str]:
        try:
            audio = speech.RecognitionAudio(content=audio_bytes)

            # Sử dụng ENCODING_UNSPECIFIED để tự động detect
            if encoding is None:
                encoding = speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED

            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=16000,  # Có thể tự động detect nếu để None
                language_code=language_code,
                enable_automatic_punctuation=True,
                model="latest_long",  # Sử dụng model tốt nhất cho audio dài
            )

            logger.info(f"Transcribing audio (language: {language_code}, encoding: {encoding})...")
            response = self.client.recognize(config=config, audio=audio)

            # Kết hợp tất cả các transcript
            transcript = ""
            for result in response.results:
                if result.alternatives:
                    transcript += result.alternatives[0].transcript + " "

            transcript = transcript.strip()
            logger.info(f"Transcription completed: {len(transcript)} characters")
            return transcript if transcript else None

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
            # Thử lại với encoding khác nếu lỗi
            if encoding != speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED:
                logger.info("Retrying with ENCODING_UNSPECIFIED...")
                return self.transcribe_audio_bytes(audio_bytes, language_code,
                                                   speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED)
            return None

    def transcribe_long_audio(self, audio_uri: str, language_code: str = "vi-VN") -> Optional[str]:
        try:
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model="latest_long",
            )

            audio = speech.RecognitionAudio(uri=audio_uri)

            logger.info(f"Starting long audio transcription (language: {language_code})...")
            operation = self.client.long_running_recognize(config=config, audio=audio)

            logger.info("Waiting for operation to complete...")
            response = operation.result(timeout=300)  # Timeout 5 phút

            transcript = ""
            for result in response.results:
                transcript += result.alternatives[0].transcript + " "

            transcript = transcript.strip()
            logger.info(f"Long transcription completed: {len(transcript)} characters")
            return transcript if transcript else None

        except Exception as e:
            logger.error(f"Error transcribing long audio: {e}")
            return None

