# Interview System - Hệ thống Phỏng vấn Tự động

Hệ thống tự động xử lý phỏng vấn với các tính năng:

- **Grading tự động** câu trả lời của ứng viên
- **Vector search** để tìm câu hỏi tương tự
- **Google Drive Webhook** - Tự động nhận file audio từ Google Drive
- **Speech-to-Text** - Chuyển đổi audio sang text
- **Transcript Analysis** - Phân tích, tóm tắt và tách Q&A pairs

---

## 🎯 INSTALLATION CHECKLIST

```bash
# ✅ Step 1: Setup PostgreSQL
docker run --name postgres-dev \
  -e POSTGRES_USER=interview_admin \
  -e POSTGRES_PASSWORD=interview123 \
  -e POSTGRES_DB=interview_system \
  -p 5433:5432 \
  -d postgres:15

# ✅ Step 2: Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# ✅ Step 3: Install dependencies
pip install -r requirements.txt

# ✅ Step 4: Setup .env
cp .env.example .env
# Edit các biến: GOOGLE_API_KEY, GEMINI_MODEL, EMBEDDING_MODEL, DATABASE_URL

# ✅ Step 5: Create database
python -m scripts.create_database

# ✅ Step 6: Load mock data
python -m scripts.setup_database

# ✅ Step 7: Run application
python main.py
```

---

## 🔍 VERIFICATION COMMANDS

```bash
# Check database
psql -h localhost -U interview_admin -d interview_system -c "SELECT COUNT(*) FROM questions;"

# Check Python packages
pip list | grep -E "langchain|sqlalchemy|faiss"

# Check vector store
ls -la data/vectorstore/

# Check logs
tail -f logs/interview_system.log
```

---

## 📡 GOOGLE DRIVE WEBHOOK & SPEECH-TO-TEXT

### Tổng quan

Hệ thống tự động nhận thông báo khi có file mới được tạo trong Google Drive, sau đó:

1. Chuyển đổi audio sang text (Speech-to-Text)
2. Phân tích transcript và tạo summary
3. Tách Q&A pairs từ transcript
4. Trả về kết quả đầy đủ

### Workflow

```
File Audio (Google Drive)
    ↓
Webhook Notification
    ↓
Download File
    ↓
Speech-to-Text → Transcript
    ↓
Transcript Analyzer → Summary + Q&A Pairs
    ↓
Response với đầy đủ thông tin
```

### Yêu cầu

1. **Google Cloud Project** với các API đã enable:

   - Google Drive API
   - Google Cloud Speech-to-Text API

2. **OAuth 2.0 Credentials** cho Google Drive API
3. **Service Account** cho Google Cloud Speech-to-Text
4. **Public URL** để nhận webhook (dùng ngrok cho development)

### Setup Google Cloud Project

#### 1. Tạo Project và Enable APIs

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới hoặc chọn project hiện có
3. Enable các API:
   - **Google Drive API**
   - **Google Cloud Speech-to-Text API**

#### 2. Tạo OAuth 2.0 Credentials (cho Google Drive)

1. Vào **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Chọn **Desktop app** làm application type
4. Download credentials và lưu vào `data/credentials.json`

#### 3. Tạo Service Account (cho Speech-to-Text)

1. Vào **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Cấp quyền **Cloud Speech Client**
4. Tạo key (JSON) và lưu vào `data/gcp-service-account.json`
5. Thêm vào `.env`: `GOOGLE_CLOUD_CREDENTIALS_PATH=data/gcp-service-account.json`

### Cấu hình Environment Variables

Thêm vào file `.env`:

```bash
# Google Drive Webhook - dùng JSON trong .env (không cần file)
GOOGLE_CREDENTIALS_JSON='{"installed": {...}}'                  # OAuth Desktop App (Drive)
GOOGLE_CLOUD_CREDENTIALS_JSON='{"type":"service_account",...}'  # Service Account (Speech-to-Text)
WEBHOOK_PORT=8000
```

### Setup Webhook

#### 1. Chạy server webhook (development với ngrok)

```bash
# Terminal 1: Chạy ngrok để expose local server
ngrok http 8000

# Terminal 2: Chạy webhook server
python -m src.api.webhook_server
```

#### 2. Cập nhật WEBHOOK_URL trong setup_webhook.py

Lấy URL từ ngrok (ví dụ: `https://abc123.ngrok.io`) và cập nhật:

```python
WEBHOOK_URL = "https://abc123.ngrok.io/webhook"
```

#### 3. Đăng ký webhook với Google Drive

```bash
# Đăng ký webhook cho toàn bộ Drive
python -m scripts.setup_webhook

# Hoặc đăng ký cho một folder cụ thể
python -m scripts.setup_webhook FOLDER_ID
```

Lần đầu chạy sẽ mở browser để xác thực OAuth.

#### 4. Dừng Webhook

```bash
python -m scripts.setup_webhook stop
```

### API Endpoints

#### GET `/`

Health check endpoint

#### GET `/webhook`

Xác thực webhook với Google (Google sẽ gửi challenge)

#### POST `/webhook`

Nhận webhook notifications từ Google Drive

#### POST `/process-file/{file_id}`

Xử lý file thủ công (không qua webhook)

**Example:**

```bash
curl -X POST http://localhost:8000/process-file/FILE_ID
```

### Response Format

```json
{
  "status": "success",
  "file_id": "1a2b3c4d5e6f7g8h",
  "file_name": "interview_recording.mp3",
  "transcript": "Full transcript text here...",
  "summary": "Cuộc phỏng vấn bao gồm các câu hỏi về JavaScript, REST API và kinh nghiệm làm việc nhóm. Ứng viên đã trả lời các câu hỏi kỹ thuật và hành vi một cách chi tiết.",
  "qa_pair": [
    {
      "question": "Bạn có thể giải thích sự khác biệt giữa var, let và const trong JavaScript không?",
      "answer": "Var có function scope và được hoisted hoàn toàn. Let có block scope và được hoisted một phần. Const cũng có block scope và ngăn chặn việc gán lại giá trị."
    },
    {
      "question": "REST API và GraphQL khác nhau như thế nào?",
      "answer": "REST sử dụng nhiều endpoint và thường dẫn đến over-fetching hoặc under-fetching. GraphQL sử dụng một endpoint duy nhất và cho phép client yêu cầu chính xác dữ liệu cần thiết."
    }
  ],
  "processed_at": "2025-11-14T15:30:45.123456"
}
```

---

## 🔧 TROUBLESHOOTING

### Database

**Lỗi kết nối database:**

- Kiểm tra PostgreSQL đang chạy: `docker ps`
- Kiểm tra connection string trong `.env`
- Kiểm tra port 5433 có bị chiếm không

### Vector Store

**Lỗi: "Error loading vector store"**

- Kiểm tra embedding model trong `.env`
- Model mặc định: `sentence-transformers/all-MiniLM-L6-v2`
- Xóa `data/vectorstore/` và chạy lại `setup_database.py`

### Google Drive Webhook

**Lỗi: "Credentials file not found"**

- Đảm bảo đã download OAuth credentials và lưu vào `data/credentials.json`

**Lỗi: "Failed to transcribe audio"**

- Kiểm tra Google Cloud Speech-to-Text API đã được enable
- Kiểm tra service account có quyền truy cập
- Kiểm tra file audio có format hợp lệ

**Webhook không nhận được notifications**

- Kiểm tra ngrok URL còn hoạt động
- Kiểm tra webhook chưa hết hạn (7 ngày)
- Đăng ký lại webhook nếu cần

**Lỗi: "Invalid grant"**

- Token đã hết hạn, xóa `data/token.pickle` và chạy lại để xác thực mới

### Transcript Analysis

**LLM không trả về JSON hợp lệ**

- Hệ thống tự động sử dụng fallback method
- Kiểm tra logs để xem chi tiết lỗi
- Có thể cần điều chỉnh prompt hoặc temperature

**Không tách được Q&A pairs**

- Kiểm tra transcript có format rõ ràng không
- Đảm bảo có dấu câu và câu hỏi rõ ràng
- Fallback method sẽ cố gắng tách dựa trên từ khóa

---
