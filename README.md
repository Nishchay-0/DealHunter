# DealHunter

A Telegram-first deal and price-drop alert platform.

---

## Current Status

```
Step 1 — Telegram bot foundation
```

---

## Requirements

- Python 3.10+
- VS Code (recommended)
- A Telegram account
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Git

---

## Installation

### 1. Clone or open the project

```bash
git clone <your-repo-url>
cd DealHunter
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Create the `.env` file

```bash
cp .env .env.example   # optional backup
```

Open `.env` and replace the placeholder with your real bot token:

```env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
```

> Get your token by messaging [@BotFather](https://t.me/BotFather) on Telegram.

### 6. Run the bot

```bash
python bot/telegram_bot.py
```

You should see:

```
DealHunter is running...
```

Open Telegram, find your bot, and send `/start`.

---

## Security

- **Never commit `.env`** — it is listed in `.gitignore` to prevent accidental exposure.
- **Never hardcode tokens** in Python source files.
- The bot token grants full control of your bot. Treat it like a password.

---

## Project Structure

```
DealHunter/
|
+-- bot/
|   +-- telegram_bot.py    # Telegram bot entry point
|
+-- .env                   # Secret config (never commit)
+-- .gitignore             # Excludes secrets and cache
+-- requirements.txt       # Python dependencies
+-- README.md              # This file
```

---

## Roadmap

| Step | Description                  | Status        |
|------|------------------------------|---------------|
| 1    | Telegram bot foundation      | ✅ Complete    |
| 2    | Database + data models       | 🔜 Planned     |
| 3    | Product tracking             | 🔜 Planned     |
| 4    | Price history                | 🔜 Planned     |
| 5    | Price-drop detection         | 🔜 Planned     |
| 6    | Notifications                | 🔜 Planned     |
| 7    | Watchlist                    | 🔜 Planned     |
| 8    | Target prices                | 🔜 Planned     |
| 9    | Deal discovery               | 🔜 Planned     |
| 10   | Admin dashboard              | 🔜 Planned     |
| 11   | WhatsApp support             | 🔜 Planned     |
| 12   | Deployment                   | 🔜 Planned     |

---

## Contributing

This is a step-by-step learning and production project.
Each step builds cleanly on the previous one.
