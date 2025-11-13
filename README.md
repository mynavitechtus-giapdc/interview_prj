## 🎯 INSTALLATION CHECKLIST
```bash
# ✅ Step 1: Setup PostgreSQL
docker run --name postgres-dev \\n  -e POSTGRES_USER=interview_admin \\n  -e POSTGRES_PASSWORD=interview123 \\n  -e POSTGRES_DB=interview_system \\n  -p 5432:5432 \\n  -d postgres:15\n

# Run SQL commands from README

# ✅ Step 2: Clone/Create project
mkdir interview-system
cd interview-system

# ✅ Step 3: Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# ✅ Step 4: Install dependencies
pip install -r requirements.txt

# ✅ Step 5: Setup .env
cp .env.example .env
# Edit GOOGLE_API_KEY

# ✅ Step 6: Create database
python -m scripts.create_database

# ✅ Step 7: Load mock data
python -m scripts.setup_database

# ✅ Step 9: Run application
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
