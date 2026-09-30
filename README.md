# DealHunter

A Telegram-first deal and price-drop alert platform.

---

## Current Status

```
Phase 2 Complete — Database Models, Alembic Migrations & FastAPI Backend Foundation
```

---

## Features (Current)

* **Telegram Bot**: Fully async bot powered by `python-telegram-bot` v22+ with `/start`, `/help`, and graceful fallback handling.
* **Database Layer**: SQLAlchemy 2.0 async ORM models covering Users, Products, Price History, Watchlists, Alerts Sent, Offers, Sources, and Audit Logs.
* **Alembic Migrations**: Fully async, version-controlled schema migrations with support for online/offline execution.
* **Backend API**: FastAPI foundation with `/health` liveness probe and async database ping.
* **System Diagnostics**: Safe CLI diagnostics tool (`scripts/diagnose.py`) with masked credentials.
* **Automated Offline Tests**: Test suite using `pytest`, `pytest-asyncio`, and in-memory SQLite (`aiosqlite`) ensuring 100% offline testability.

---

## Requirements

- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- PostgreSQL (for production/staging) or SQLite (for local development/testing)
- Git

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Nishchay-0/DealHunter.git
cd DealHunter
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env`:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Open `.env` and set your credentials:
```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dealhunter
# or for local SQLite development:
# DATABASE_URL=sqlite+aiosqlite:///dealhunter.db
ENVIRONMENT=development
PORT=8000
```

---

## Running the Components

### Run Diagnostics
```bash
python scripts/diagnose.py
```

### Apply Database Migrations
```bash
alembic upgrade head
```

### Run the FastAPI Backend
```bash
uvicorn backend.main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` for the interactive Swagger API documentation.

### Run the Telegram Bot
```bash
python bot/telegram_bot.py
```

### Run the Test Suite
```bash
pytest
```

---

## Project Structure

```
DealHunter/
├── alembic/                      # Database migration scripts
│   ├── env.py                    # Async migration runner
│   └── versions/                 # Version-controlled migrations
├── backend/                      # FastAPI application
│   └── main.py                   # Health check & API entry point
├── bot/                          # Telegram bot interface
│   └── telegram_bot.py           # Commands (/start, /help)
├── database/                     # Database layer
│   ├── base.py                   # Declarative base
│   ├── models.py                 # SQLAlchemy 2.0 ORM models
│   └── session.py                # Async engine & session factory
├── scripts/                      # Operational utilities
│   └── diagnose.py               # Masked system diagnostics
├── tests/                        # Offline automated test suite
│   ├── api/                      # API contract tests
│   ├── database/                 # ORM & database tests
│   └── conftest.py               # Async fixtures & in-memory DB
├── .env.example                  # Environment configuration template
├── .gitignore                    # Excludes secrets, cache, venv
├── alembic.ini                   # Alembic configuration
├── pytest.ini                    # Test runner configuration
├── requirements.txt              # Project dependencies
└── README.md                     # Documentation
```

---

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Telegram Bot Foundation (`/start`, `/help`) | ✅ Complete |
| 2 | FastAPI + PostgreSQL/SQLite Models + Alembic Migrations | ✅ Complete |
| 3 | Product Tracking (URL → Source Parser → History) | 🔜 Next (Awaiting Approval) |
| 4 | Scheduler + Price-Drop Detection + Notifications | ⏳ Pending |
| 5 | Watchlist + Target Price + `/deals` | ⏳ Pending |
| 6 | Deal Analysis Engine (Deal Score & Breakdown) | ⏳ Pending |
| 7 | Coupons, Effective Price & Offer Stacking | ⏳ Pending |
| 8 | Admin Dashboard & Monitoring | ⏳ Pending |
| 9 | WhatsApp Adapter via Official Business API | ⏳ Pending |

---

## Security & Privacy Compliance

* **No Secrets Committed**: `.env` and sensitive credentials are excluded via `.gitignore`.
* **Zero Secret Leakage in Logs**: All diagnostics and logging utilities mask tokens and connection credentials.
* **Compliance Grounding**: Respects data protection principles (DPDP Act, GDPR) and retailer terms.
