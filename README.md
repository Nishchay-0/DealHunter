# DealHunter

A Telegram-first deal and price-drop alert platform.

---

## Current Status

```
Phase 6 Complete — Isolated Deal Analysis Engine (Deal Score 0–100, Fake-Discount Detection & Metrics)
```

---

## Features (Current)

* **Telegram Bot**: Fully async bot powered by `python-telegram-bot` v22+ with `/start`, `/help`, `/track`, `/watchlist`, `/target`, `/deals`, and `/remove` commands.
* **Deal Analysis Engine (`pricing/`)**:
  * **Isolated Architecture**: Zero Telegram or FastAPI dependencies.
  * **Weighted Deal Score (0–100)**: Transparent weighted breakdown across 5 factors:
    * *Historical Position* (40 pts)
    * *Drop Magnitude* (25 pts)
    * *Drop Velocity* (10 pts)
    * *Effective Price Savings* (15 pts)
    * *Seller Trust & Rating* (10 pts)
  * **Deal Labels**: 🔥 Excellent deal (85–100), 🟢 Strong deal (70–84), 🟡 Fair deal (55–69), ⚪ Average (40–54), 🔴 Skip (0–39).
  * **Fake-Discount Detection**: Flags artificially inflated list prices (>25% above 30-day median) and 14-day price spikes.
  * **Historical Metrics**: Tracks 30d/90d/all-time lows, medians, 30d volatility, and confidence ratings.
* **Retailer Price Sources**:
  * **Amazon India** (`amazon.in`): ASIN, title, list price, coupon discounts, seller info, and stock.
  * **Flipkart** (`flipkart.com`): PID, item metadata, list price, bank offers, and stock.
  * **Croma** (`croma.com`): Product code, catalog metadata, price, and availability.
  * **Myntra** (`myntra.com`): Style ID, product name, price, and availability.
* **Scheduler & Reliability**:
  * **Dynamic Check Intervals**: 30 min post-drop monitoring, 1h for popular products (>2 watchers), 6h standard.
  * **Circuit Breakers**: Per-source rolling window failure counters protecting against bans and rate-limits.
  * **Observation Idempotency**: Suppresses duplicate price records when prices and offers remain unchanged.
* **Multi-Channel Notification Layer**:
  * **Channel Adapters**: Telegram and official Meta WhatsApp Business Cloud API.
  * **Single Message Renderer**: Universal explainability block, price change diff, stackable offers, and mandatory disclaimer caveat.
  * **Guardrails**: Cooldowns (6h default), quiet hours, daily rate caps, and deduplication.
* **Automated Offline Tests**: 42 unit and integration tests passing 100% offline using `pytest` and in-memory SQLite.

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

```bash
cp .env.example .env
```

Set your credentials in `.env`:
```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dealhunter
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
├── backend/                      # FastAPI application
├── bot/                          # Telegram bot interface
├── database/                     # Database models & session factory
├── deals/                        # Price drop discovery & ranking
├── notifications/                # Multi-channel notification layer & guardrails
├── pricing/                      # Isolated Deal Analysis Engine
│   ├── analyzer.py               # Fake-discount & manipulation detection
│   ├── config.py                 # Weights, penalties, and label thresholds
│   ├── detector.py               # Drop detection, dedup & cooldown evaluation
│   ├── effective_price.py        # Offer stacking & condition notes
│   ├── history.py                # Historical metrics & drop velocity algorithms
│   ├── models.py                 # Core domain models (PriceObservation, DealVerdict)
│   ├── rules.py                  # Alert rule evaluation
│   └── scorer.py                 # Weighted 0-100 deal score calculator
├── products/                     # Product catalog & price tracking
├── scheduler/                    # Periodic price checks & circuit breakers
├── scripts/                      # Operational utilities
├── tests/                        # Offline automated test suite (42 tests)
├── watchlist/                    # User watchlist & category inference
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
| 4 | Scheduler + Price-Drop Detection + Notifications | ✅ Complete |
| 5 | Watchlist + Target Price + `/deals` + Categories | ✅ Complete |
| 6 | **Deal Analysis Engine** (Score 0–100, Fake-Discount Detection & Metrics) | ✅ Complete |
| 7 | Coupons, Effective Price & Offer Stacking | 🔜 Next (Awaiting Approval) |
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
