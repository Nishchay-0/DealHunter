# DealHunter

A Telegram-first deal and price-drop alert platform.

---

## Current Status

```
Phase 3 Complete — Product Tracking Engine (Amazon, Flipkart, Croma, Myntra) & Live Telegram Integration
```

---

## Features (Current)

* **Telegram Bot**: Fully async bot powered by `python-telegram-bot` v22+ with `/start`, `/help`, and `/track <url>` commands.
* **Direct URL Tracking**: Send or paste any product link from Amazon, Flipkart, Croma, or Myntra directly into the chat.
* **Retailer Price Sources**:
  * **Amazon India** (`amazon.in`): Extracts ASIN, title, listed price, coupon discounts, seller info, and stock status.
  * **Flipkart** (`flipkart.com`): Extracts PID, item metadata, listed price, bank offers, and stock status.
  * **Croma** (`croma.com`): Extracts product code, catalog metadata, price, and availability.
  * **Myntra** (`myntra.com`): Extracts style ID, product name, price, and availability.
* **Database & Price History**: SQLAlchemy 2.0 async ORM tracking products, historical price observations, effective prices, and user watchlists.
* **Alembic Migrations**: Fully async schema migrations.
* **Backend API**: FastAPI foundation with `/health` liveness probe.
* **System Diagnostics**: Safe CLI diagnostics tool (`scripts/diagnose.py`) with masked credentials.
* **Automated Offline Tests**: 21 unit and integration tests passing 100% offline using `pytest` and in-memory SQLite.

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
│   └── telegram_bot.py           # Commands (/start, /help, /track, direct URL handling)
├── database/                     # Database layer
│   ├── base.py                   # Declarative base
│   ├── models.py                 # SQLAlchemy 2.0 ORM models
│   └── session.py                # Async engine & session factory
├── products/                     # Product catalog & price tracking
│   ├── models.py                 # ProductData & PriceObservation dataclasses
│   ├── service.py                # ProductTrackingService (catalog + history)
│   └── sources/                  # Retailer adapters
│       ├── base.py               # PriceSource ABC
│       ├── amazon.py             # Amazon India adapter
│       ├── flipkart.py           # Flipkart adapter
│       ├── croma.py              # Croma adapter
│       ├── myntra.py             # Myntra adapter
│       └── registry.py           # URL → Source resolution
├── scripts/                      # Operational utilities
│   └── diagnose.py               # Masked system diagnostics
├── tests/                        # Offline automated test suite
│   ├── api/                      # API contract tests
│   ├── database/                 # ORM & database tests
│   ├── fixtures/                 # Offline HTML retailer fixtures
│   ├── products/                 # Parser, registry & service tests
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
| 3 | Product Tracking (URL → Source Parser → Product Catalog → Current Price & History) | ✅ Complete |
| 4 | Scheduler + Price-Drop Detection + Notifications | 🔜 Next (Awaiting Approval) |
| 5 | Watchlist + Target Price + `/deals` | ⏳ Pending |
| 6 | Deal Analysis Engine (Deal Score & Breakdown) | ⏳ Pending |
| 7 | Coupons, Effective Price & Offer Stacking | ⏳ Pending |
| 8 | Admin Dashboard & Monitoring | ⏳ Pending |
| 9 | WhatsApp Adapter via Official Business API | ⏳ Pending |

---

## Security & Compliance Declarations

| Retailer | Access Method | Permission Rationale | Status |
|----------|---------------|----------------------|--------|
| **Amazon India** | `public_page_read` | Publicly readable Open Graph & JSON-LD microdata; throttled & rate-limited | Enabled |
| **Flipkart** | `public_page_read` | Publicly readable schema & Open Graph tags; throttled & rate-limited | Enabled |
| **Croma** | `public_page_read` | Public catalog metadata & JSON-LD; polite rate limit | Enabled |
| **Myntra** | `public_page_read` | Public catalog metadata & Open Graph; polite rate limit | Enabled |

* **Zero Secret Leakage**: All credentials masked in logs and diagnostics.
* **Zero Live CI Calls**: 100% of test fixtures run offline.
