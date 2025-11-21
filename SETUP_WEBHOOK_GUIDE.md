# 🚀 Hướng dẫn Setup Google Drive Webhook - Chi tiết từng bước

Hướng dẫn này sẽ giúp bạn setup Google Drive Webhook từ đầu đến khi hoạt động hoàn chỉnh.

---

## 📋 Mục lục

1. [Chuẩn bị](#1-chuẩn-bị)
2. [Setup Google Cloud Project](#2-setup-google-cloud-project)
3. [Cài đặt Dependencies](#3-cài-đặt-dependencies)
4. [Cấu hình Environment Variables](#4-cấu-hình-environment-variables)
5. [Setup ngrok (cho development)](#5-setup-ngrok-cho-development)
6. [Cấu hình Webhook URL](#6-cấu-hình-webhook-url)
7. [Chạy Webhook Server](#7-chạy-webhook-server)
8. [Đăng ký Webhook với Google Drive](#8-đăng-ký-webhook-với-google-drive)
9. [Test Webhook](#9-test-webhook)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Chuẩn bị

### Yêu cầu hệ thống:

- ✅ Python 3.10+
- ✅ Google account
- ✅ Internet connection
- ✅ ngrok account (miễn phí) - https://ngrok.com

### Kiểm tra Python:

```bash
python3 --version
# Kết quả mong đợi: Python 3.10.x hoặc cao hơn
```

### Kiểm tra pip:

```bash
pip3 --version
```

---

## 2. Setup Google Cloud Project

### Bước 2.1: Tạo Google Cloud Project

1. **Truy cập Google Cloud Console**

   - Vào: https://console.cloud.google.com/
   - Đăng nhập bằng Google account

2. **Tạo Project mới**

   - Click vào dropdown "Select a project" ở trên cùng
   - Click "NEW PROJECT"
   - Điền tên project (ví dụ: "interview-system")
   - Click "CREATE"
   - Đợi project được tạo (vài giây)

3. **Chọn Project vừa tạo**
   - Click vào dropdown "Select a project"
   - Chọn project vừa tạo

### Bước 2.2: Enable Google Drive API

1. **Vào API Library**

   - Menu bên trái > **APIs & Services** > **Library**
   - Hoặc truy cập: https://console.cloud.google.com/apis/library

2. **Tìm và Enable Google Drive API**
   - Tìm "Google Drive API"
   - Click vào "Google Drive API"
   - Click nút **ENABLE**
   - Đợi API được enable (vài giây)

### Bước 2.3: Enable Google Cloud Speech-to-Text API

1. **Tìm Speech-to-Text API**
   - Trong API Library, tìm "Cloud Speech-to-Text API"
   - Click vào "Cloud Speech-to-Text API"
   - Click nút **ENABLE**
   - Đợi API được enable

### Bước 2.4: Tạo OAuth 2.0 Credentials (cho Google Drive)

1. **Vào Credentials**

   - Menu bên trái > **APIs & Services** > **Credentials**
   - Hoặc truy cập: https://console.cloud.google.com/apis/credentials

2. **Configure OAuth Consent Screen**

   - Click **CONFIGURE CONSENT SCREEN** (nếu chưa có)
   - Chọn **External** (cho development) > Click **CREATE**
   - Điền thông tin:
     - **App name**: Interview System (hoặc tên bạn muốn)
     - **User support email**: Email của bạn
     - **Developer contact information**: Email của bạn
   - Click **SAVE AND CONTINUE**
   - Bước Scopes: Click **SAVE AND CONTINUE** (bỏ qua)
   - Bước Test users: Click **SAVE AND CONTINUE** (bỏ qua)
   - Bước Summary: Click **BACK TO DASHBOARD**

3. **Tạo OAuth 2.0 Client ID**

   - Trong trang Credentials, click **+ CREATE CREDENTIALS**
   - Chọn **OAuth client ID**
   - Nếu chưa configure consent screen, sẽ được yêu cầu configure (làm bước trên)
   - **Application type**: Chọn **Desktop app**
   - **Name**: Interview System Client (hoặc tên bạn muốn)
   - Click **CREATE**

4. **Download Credentials**
   - Một popup sẽ hiện ra với Client ID và Client Secret
   - Click **DOWNLOAD JSON**
   - Lưu file về máy, mở file bằng editor và **copy toàn bộ nội dung JSON**
   - Bạn sẽ dán nội dung này vào biến môi trường `GOOGLE_CREDENTIALS_JSON` trong `.env` (không cần giữ file trên server)

### Bước 2.5: Tạo Service Account (cho Speech-to-Text)

1. **Vào Service Accounts**

   - Menu bên trái > **IAM & Admin** > **Service Accounts**
   - Hoặc truy cập: https://console.cloud.google.com/iam-admin/serviceaccounts

2. **Tạo Service Account**

   - Click **+ CREATE SERVICE ACCOUNT**
   - **Service account name**: speech-to-text-service
   - **Service account ID**: speech-to-text-service (tự động điền)
   - Click **CREATE AND CONTINUE**

3. **Cấp quyền**

   - **Grant this service account access to project**: Chọn role **Cloud Speech Client**
   - Click **CONTINUE**
   - Bước Grant users access: Click **DONE** (bỏ qua)

4. **Tạo Key**

   - Click vào service account vừa tạo
   - Tab **KEYS** > Click **ADD KEY** > **Create new key**
   - Chọn **JSON** > Click **CREATE**
   - File JSON sẽ tự động download về máy

5. **Lưu Service Account Key**
   - Mở file JSON vừa tải và **copy toàn bộ nội dung**
   - Paste nội dung này vào biến `GOOGLE_CLOUD_CREDENTIALS_JSON` trong `.env`
   - Có thể xóa file cục bộ sau khi đã copy (giúp tránh phải deploy file kèm theo)

---

## 3. Cài đặt Dependencies

### Bước 3.1: Activate Virtual Environment

```bash
# Di chuyển vào thư mục project
cd /Users/nals_macbook_289/Projects/interview_prj

# Activate virtual environment
source venv/bin/activate

# Kiểm tra đã activate (sẽ thấy (venv) ở đầu dòng)
```

### Bước 3.2: Cài đặt Packages

```bash
# Cài đặt các packages cần thiết
pip install -r requirements.txt

# Hoặc cài đặt từng package nếu cần
pip install google-api-python-client
pip install google-auth-httplib2
pip install google-auth-oauthlib
pip install google-cloud-speech
pip install fastapi
pip install "uvicorn[standard]"
```

### Bước 3.3: Kiểm tra Installation

```bash
# Kiểm tra các package đã được cài đặt
pip list | grep -E "google|fastapi|uvicorn"

# Kết quả mong đợi:
# fastapi
# google-api-python-client
# google-auth-httplib2
# google-auth-oauthlib
# google-cloud-speech
# uvicorn
```

---

## 4. Cấu hình Environment Variables

### Bước 4.1: Kiểm tra file .env

```bash
# Kiểm tra file .env có tồn tại không
ls -la .env

# Nếu chưa có, copy từ .env.example
cp .env.example .env
```

### Bước 4.2: Cập nhật file .env

Mở file `.env` và thêm các biến sau:

```bash
# Google Drive Webhook
GOOGLE_CREDENTIALS_JSON='{"installed": {...}}'
GOOGLE_CLOUD_CREDENTIALS_JSON='{"type":"service_account","private_key":"-----BEGIN PRIVATE KEY-----\n..."}'
WEBHOOK_PORT=8000
TARGET_FOLDER_ID=1g50YK184Y5Dt3l1l-UM-0KOumWt_29fX

# (Các biến khác đã có sẵn từ trước)
```

**Lưu ý**: Đảm bảo các biến khác như `GOOGLE_API_KEY`, `GEMINI_MODEL`, `EMBEDDING_MODEL`, `DATABASE_URL` đã được cấu hình.

### Bước 4.3: Kiểm tra Credentials Files

- Không cần kiểm tra file vật lý nữa. Thay vào đó:
  1. Chạy `python -m scripts.check_webhook_setup` để xác minh biến JSON đã được đọc thành công.
  2. Nếu báo lỗi, mở `.env` và kiểm tra dấu `'` bao quanh JSON, cũng như ký tự xuống dòng trong private key.

---

## 5. Setup ngrok (cho development)

### Bước 5.1: Đăng ký ngrok

1. **Truy cập ngrok**

   - Vào: https://ngrok.com/
   - Click **Sign up** (miễn phí)
   - Đăng ký bằng email hoặc Google account

2. **Download ngrok**
   - Vào: https://ngrok.com/download
   - Download cho macOS (nếu bạn dùng Mac)
   - Giải nén file

### Bước 5.2: Cài đặt ngrok

```bash
# Di chuyển ngrok vào thư mục /usr/local/bin (hoặc thư mục trong PATH)
sudo mv ~/Downloads/ngrok /usr/local/bin/

# Hoặc giải nén và di chuyển
unzip ~/Downloads/ngrok.zip
sudo mv ngrok /usr/local/bin/

# Kiểm tra ngrok đã được cài đặt
ngrok version
```

### Bước 5.3: Cấu hình ngrok

1. **Lấy Authtoken**

   - Đăng nhập vào ngrok dashboard: https://dashboard.ngrok.com/get-started/your-authtoken
   - Copy authtoken

2. **Cấu hình ngrok**

   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN
   ```

3. **Kiểm tra cấu hình**
   ```bash
   ngrok config check
   ```

---

## 6. Cấu hình Webhook URL

### Bước 6.1: Chạy ngrok

Mở một terminal mới và chạy:ngrok

```bash
# Chạy ngrok để expose port 8000
ngrok http 8000
```

**Kết quả sẽ hiển thị:**

```
Session Status                online
Account                       Your Name (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000
```

**QUAN TRỌNG**: Copy URL `https://abc123.ngrok.io` (URL của bạn sẽ khác)

### Bước 6.2: Cập nhật Webhook URL trong setup_webhook.py

1. **Mở file setup_webhook.py**

   ```bash
   # Mở file trong editor
   code scripts/setup_webhook.py
   # Hoặc
   nano scripts/setup_webhook.py
   ```

2. **Tìm dòng WEBHOOK_URL và cập nhật**

   ```python
   # Dòng 17, thay đổi từ:
   WEBHOOK_URL = "https://your-domain.com/webhook"

   # Thành URL ngrok của bạn:
   WEBHOOK_URL = "https://abc123.ngrok.io/webhook"  # Thay abc123.ngrok.io bằng URL thực của bạn
   ```

3. **Lưu file**

**Lưu ý**:

- URL ngrok sẽ thay đổi mỗi khi bạn restart ngrok (trừ khi dùng plan trả phí)
- Webhook URL phải là HTTPS (ngrok tự động cung cấp HTTPS)

---

## 7. Chạy Webhook Server

### Bước 7.1: Chạy Webhook Server

Mở một terminal mới (giữ ngrok đang chạy) và chạy:

```bash
# Di chuyển vào thư mục project
cd /Users/nals_macbook_289/Projects/interview_prj

# Activate virtual environment
source venv/bin/activate

# Chạy webhook server
python -m src.api.webhook_server
```

**Kết quả mong đợi:**

```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Bước 7.2: Kiểm tra Server hoạt động

Mở browser và truy cập:

- http://localhost:8000/ - Sẽ thấy `{"status":"ok","service":"Interview System Webhook Server"}`

Hoặc test bằng curl:

```bash
curl http://localhost:8000/
```

### Bước 7.3: Kiểm tra ngrok đang forward đúng

Truy cập ngrok web interface:

- http://127.0.0.1:4040

Bạn sẽ thấy các request đến server trong ngrok dashboard.

---

## 8. Đăng ký Webhook với Google Drive

### Bước 8.1: Chạy Setup Webhook Script

Mở một terminal mới (giữ ngrok và webhook server đang chạy) và chạy:

```bash
# Di chuyển vào thư mục project
cd /Users/nals_macbook_289/Projects/interview_prj

# Activate virtual environment
source venv/bin/activate

# Chạy script setup webhook
python -m scripts.setup_webhook
```

### Bước 8.2: Xác thực OAuth (lần đầu)

1. **Browser sẽ tự động mở**

   - Nếu không, copy URL từ terminal và mở trong browser
   - URL sẽ có dạng: `http://localhost:xxxxx/`

2. **Đăng nhập Google**

   - Chọn Google account bạn muốn sử dụng
   - Click **Continue**

3. **Cấp quyền**

   - Google sẽ yêu cầu cấp quyền truy cập Google Drive
   - Click **Allow** (Cho phép)

4. **Hoàn tất xác thực**
   - Browser sẽ hiển thị "The authentication flow has completed"
   - Đóng browser tab
   - Quay lại terminal, script sẽ tiếp tục chạy

### Bước 8.3: Kiểm tra kết quả

Terminal sẽ hiển thị:

```
======================================================================
WEBHOOK SETUP SUCCESSFUL
======================================================================
Channel ID: webhook-20251114153045
Resource ID: xxxxx
Expiration: 2025-11-21 15:30:45
Webhook URL: https://abc123.ngrok.io/webhook

IMPORTANT: Save the Channel ID and Resource ID!
You'll need them to stop the webhook later.
======================================================================
```

**QUAN TRỌNG**:

- Lưu lại Channel ID và Resource ID
- Thông tin này đã được lưu tự động vào `data/webhook_info.json`

### Bước 8.4: Đăng ký cho Folder cụ thể (Optional)

Nếu bạn muốn chỉ theo dõi một folder cụ thể trong Google Drive:

```bash
# Lấy Folder ID từ URL Google Drive
# Ví dụ: https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h
# Folder ID là: 1a2b3c4d5e6f7g8h

# Đăng ký webhook cho folder
python -m scripts.setup_webhook 1a2b3c4d5e6f7g8h
```

---

## 9. Test Webhook

### Bước 9.1: Upload File Audio vào Google Drive

1. **Chuẩn bị file audio**

   - File audio định dạng: MP3, WAV, M4A, etc.
   - Đảm bảo file có nội dung (không rỗng)

2. **Upload vào Google Drive**
   - Truy cập: https://drive.google.com/
   - Upload file audio vào Drive
   - Lưu lại File ID (có thể lấy từ URL: `https://drive.google.com/file/d/FILE_ID/view`)

### Bước 9.2: Kiểm tra Webhook nhận được Notification

1. **Kiểm tra Logs của Webhook Server**

   - Terminal chạy webhook server sẽ hiển thị:

   ```
   INFO:     Received webhook notification
   INFO:     Channel ID: webhook-20251114153045
   INFO:     Resource State: exists
   INFO:     Processing file ID: xxxxx
   ```

2. **Kiểm tra ngrok Dashboard**
   - Truy cập: http://127.0.0.1:4040
   - Xem request POST đến `/webhook`

### Bước 9.3: Test thủ công với File ID

Nếu webhook không tự động trigger, bạn có thể test thủ công:

```bash
# Thay FILE_ID bằng ID file thực tế
curl -X POST http://localhost:8000/process-file/FILE_ID
```

**Kết quả mong đợi:**

```json
{
  "status": "success",
  "interviewer_name": "Unknown",
  "candidate_name": "Danh",
  "summary": "Summary tập trung 2-3 câu về các câu hỏi kỹ thuật.",
  "qa_pairs": [
    {
      "question": "REST và GraphQL khác nhau như thế nào?",
      "answer": "REST dùng nhiều endpoint nên dễ over/under-fetching; GraphQL dùng 1 endpoint và cho phép request chính xác dữ liệu."
    },
    {
      "question": "Bạn xử lý xung đột nhóm ra sao?",
      "answer": "Lắng nghe hai bên, xác định nguyên nhân và ưu tiên giải pháp khách quan dựa trên dữ liệu."
    }
  ],
  "processed_at": "2025-11-19T14:57:39.340411"
}
```

**Ghi chú quan trọng**

- Hệ thống hỗ trợ cả audio và video (mp3, wav, m4a, mp4/mov...). Video sẽ được convert sang WAV 16kHz mono bằng `ffmpeg`.
- Nếu audio dài hơn ~60 giây, server sẽ tự động segment thành các đoạn 55 giây để tránh giới hạn của Google Speech-to-Text.
- `qa_pairs` đã được lọc để chỉ giữ lại câu hỏi/chủ đề liên quan chuyên môn, loại bỏ chào hỏi hoặc small talk.

### Bước 9.4: Kiểm tra Logs

```bash
# Xem logs của hệ thống
tail -f logs/interview_system.log

# Hoặc xem logs trực tiếp từ terminal chạy webhook server
```

---

## 10. Troubleshooting

### Lỗi: "Credentials file not found"

**Nguyên nhân**: Biến `GOOGLE_CREDENTIALS_JSON` hoặc `GOOGLE_CLOUD_CREDENTIALS_JSON` chưa được set đúng.

**Giải pháp**:

1. Mở `.env`, đảm bảo hai biến JSON được bao bởi `'...'`.
2. Kiểm tra private key có ký tự `\n` thay cho xuống dòng.
3. Chạy lại `python -m scripts.check_webhook_setup` để xác nhận hệ thống đọc được credentials.

### Lỗi: "Invalid grant" hoặc "Token expired"

**Nguyên nhân**: OAuth token đã hết hạn

**Giải pháp**:

```bash
# Xóa token cũ
rm data/token.pickle

# Chạy lại setup webhook để xác thực lại
python -m scripts.setup_webhook
```

### Lỗi: "Failed to transcribe audio"

**Nguyên nhân**:

- Service account không có quyền
- File audio không hợp lệ
- Speech-to-Text API chưa được enable

**Giải pháp**:

1. Kiểm tra Service Account có quyền **Cloud Speech Client**
2. Kiểm tra file audio có định dạng hợp lệ (MP3, WAV, M4A, etc.)
3. Kiểm tra Speech-to-Text API đã được enable trong Google Cloud Console

### Webhook không nhận được notifications

**Nguyên nhân**:

- ngrok URL đã thay đổi
- Webhook đã hết hạn (7 ngày)
- Webhook URL không đúng

**Giải pháp**:

1. Kiểm tra ngrok URL còn hoạt động: http://127.0.0.1:4040
2. Cập nhật WEBHOOK_URL trong `setup_webhook.py` nếu ngrok URL đã thay đổi
3. Đăng ký lại webhook: `python -m scripts.setup_webhook`

### Lỗi: "Address already in use" (Port 8000 đã được sử dụng)

**Nguyên nhân**: Port 8000 đã được sử dụng bởi process khác

**Giải pháp**:

```bash
# Tìm process đang sử dụng port 8000
lsof -i :8000

# Kill process
kill -9 PID

# Hoặc thay đổi port trong .env
WEBHOOK_PORT=8001
```

### Lỗi: "Module not found"

**Nguyên nhân**: Dependencies chưa được cài đặt

**Giải pháp**:

```bash
# Cài đặt lại dependencies
pip install -r requirements.txt
```

---

## ✅ Checklist hoàn thành

- [ ] Google Cloud Project đã được tạo
- [ ] Google Drive API đã được enable
- [ ] Speech-to-Text API đã được enable
- [ ] OAuth 2.0 Credentials đã được tạo (JSON đã copy vào `.env`)
- [ ] Service Account đã được tạo (JSON đã copy vào `.env`)
- [ ] Dependencies đã được cài đặt
- [ ] File `.env` đã được cấu hình (bao gồm GOOGLE_CREDENTIALS_JSON / GOOGLE_CLOUD_CREDENTIALS_JSON)
- [ ] ngrok đã được cài đặt và cấu hình
- [ ] ngrok đang chạy và expose port 8000
- [ ] WEBHOOK_URL đã được cập nhật trong `setup_webhook.py`
- [ ] Webhook server đang chạy
- [ ] Webhook đã được đăng ký với Google Drive
- [ ] Đã test upload file và nhận được notification
- [ ] Transcript đã được tạo thành công
- [ ] Summary và Q&A pairs đã được tạo

---

## 🎉 Hoàn thành!

Bây giờ hệ thống đã sẵn sàng:

- ✅ Tự động nhận thông báo khi có file mới trong Google Drive
- ✅ Tự động chuyển đổi audio sang text
- ✅ Tự động phân tích và tách Q&A pairs
- ✅ Trả về kết quả đầy đủ qua webhook

**Lưu ý**:

- Webhook sẽ hết hạn sau 7 ngày, cần đăng ký lại
- ngrok URL sẽ thay đổi mỗi khi restart (trừ khi dùng plan trả phí)
- Để sử dụng production, cần setup domain thật và HTTPS

---

## 📞 Hỗ trợ

Nếu gặp vấn đề, kiểm tra:

1. Logs trong terminal chạy webhook server
2. Logs trong file `logs/interview_system.log`
3. ngrok dashboard: http://127.0.0.1:4040
4. Google Cloud Console để kiểm tra API và credentials
