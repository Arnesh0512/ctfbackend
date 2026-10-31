# ctfbackend

Backend API for the Mayasabha Indian Monument-Based CTF Platform.  
Built with **FastAPI**, **SQLAlchemy 2.0 (asyncio)**, **PostgreSQL (Supabase)**, and **Alembic**.

---

## Getting Started

### 1. Setup Virtual Environment
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
```

### 3. Database Migrations
```bash
alembic upgrade head
```

### 4. Run Development Server
```bash
uvicorn app.main:app --reload
```

Interactive API documentation (Swagger) will be served at:
- **`http://127.0.0.1:8000/docs`**
