from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle
import os
from datetime import datetime, timedelta

from config.settings import settings
from src.utils.logger import logger

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
WEBHOOK_URL = "https://c4a070e06a03.ngrok-free.app/webhook"  # Thay bằng URL public của bạn


def authenticate():
    creds = None
    token_path = 'data/token.pickle'
    credentials_path = settings.google_credentials_path
    credentials_json = getattr(settings, 'google_credentials_json', None)

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Ưu tiên dùng JSON trong .env nếu có
            if credentials_json:
                import json as _json
                try:
                    client_config = _json.loads(credentials_json)
                    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    raise RuntimeError(f"Failed to load OAuth client from GOOGLE_CREDENTIALS_JSON: {e}")
            else:
                if not credentials_path or not os.path.exists(credentials_path):
                    raise FileNotFoundError(
                        "Credentials not provided. Set GOOGLE_CREDENTIALS_JSON in .env "
                        "or provide GOOGLE_CREDENTIALS_PATH to a credentials file."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return creds


def setup_webhook(folder_id: str = None):
    try:
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)

        # Tạo channel để nhận notifications
        channel = {
            'id': f'webhook-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'type': 'web_hook',
            'address': WEBHOOK_URL,
            'expiration': int((datetime.now() + timedelta(days=7)).timestamp() * 1000)
        }

        # Tạo watch request
        request = {
            'kind': 'api#channel',
            'id': channel['id'],
            'type': channel['type'],
            'address': channel['address'],
            'expiration': channel['expiration']
        }

        # Luôn sử dụng Changes API để nhận mọi thay đổi và tự lọc theo folder ở server
        # 1) Lấy startPageToken hợp lệ
        try:
            start_token_resp = service.changes().getStartPageToken().execute()
            start_page_token = start_token_resp.get('startPageToken')
            if not start_page_token:
                raise RuntimeError("Could not obtain startPageToken from Drive API")
        except Exception as e:
            raise RuntimeError(
                "Failed to get startPageToken. Hãy đảm bảo Google Drive API đã được ENABLE cho project. "
                "Mở link: https://console.developers.google.com/apis/api/drive.googleapis.com/overview "
                "→ Chọn đúng project → Enable API. Chi tiết lỗi: {}".format(e)
            )

        # 2) Đăng ký watch với startPageToken
        result = service.changes().watch(
            pageToken=start_page_token,
            body=request
        ).execute()

        print("\n" + "="*70)
        print("WEBHOOK SETUP SUCCESSFUL")
        print("="*70)
        print(f"Channel ID: {result.get('id')}")
        print(f"Resource ID: {result.get('resourceId')}")
        # expiration có thể trả về chuỗi milliseconds
        exp_val = result.get('expiration')
        try:
            exp_ms = int(exp_val) if exp_val is not None else None
            exp_human = datetime.fromtimestamp(exp_ms / 1000).isoformat() if exp_ms else "N/A"
            print(f"Expiration: {exp_human} (ms={exp_ms})")
        except (ValueError, TypeError):
            print(f"Expiration: {exp_val}")
        print(f"Webhook URL: {WEBHOOK_URL}")
        print("\nIMPORTANT: Save the Channel ID and Resource ID!")
        print("You'll need them to stop the webhook later.")
        print("="*70 + "\n")

        # Lưu thông tin webhook
        webhook_info = {
            'channel_id': result.get('id'),
            'resource_id': result.get('resourceId'),
            'expiration': result.get('expiration'),
            'webhook_url': WEBHOOK_URL,
            'folder_id': folder_id,
            'start_page_token': start_page_token
        }

        import json
        with open('data/webhook_info.json', 'w') as f:
            json.dump(webhook_info, f, indent=2)

        logger.info("Webhook setup completed")
        return result

    except Exception as e:
        logger.error(f"Error setting up webhook: {e}", exc_info=True)
        print(f"\nError: {e}\n")
        raise


def stop_webhook(channel_id: str, resource_id: str):
    try:
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)

        stop_request = {
            'id': channel_id,
            'resourceId': resource_id
        }

        service.channels().stop(body=stop_request).execute()

        print("\n" + "="*70)
        print("WEBHOOK STOPPED")
        print("="*70)
        print(f"Channel ID: {channel_id}")
        print("="*70 + "\n")

        logger.info("Webhook stopped successfully")

    except Exception as e:
        logger.error(f"Error stopping webhook: {e}", exc_info=True)
        print(f"\nError: {e}\n")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        # Stop webhook
        import json
        if os.path.exists('data/webhook_info.json'):
            with open('data/webhook_info.json', 'r') as f:
                info = json.load(f)
            stop_webhook(info['channel_id'], info['resource_id'])
        else:
            print("Error: webhook_info.json not found")
            print("Please provide channel_id and resource_id manually")
    else:
        # Setup webhook
        folder_id = sys.argv[1] if len(sys.argv) > 1 else None
        if folder_id:
            print(f"Setting up webhook for folder: {folder_id}")
        else:
            print("Setting up webhook for entire Drive")
            print("(To watch a specific folder, pass folder_id as argument)")

        setup_webhook(folder_id)

