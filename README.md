# Stock Analysis AI - Telegram Bot

AI-powered stock analysis Telegram bot for Indonesian stocks using OHLCV data and technical indicators.

## Tech Stack

### Backend
- **FastAPI** 0.124.0 - Modern Python web framework
- **Python** 3.11+ - Programming language
- **yfinance** 0.2.66 - Yahoo Finance data fetching
- **pandas** 2.3.0 - Data manipulation
- **numpy** 2.3.0 - Numerical computing
- **Google Gemini SDK** 1.54.0 - LLM integration (gemini-2.5-flash)
- **PostgreSQL** - Database (via psycopg2)
- **SQLAlchemy** 2.0.38 - ORM
- **matplotlib** 3.10.0 - Chart generation

### Telegram Bot
- **python-telegram-bot** 21.8 - Telegram bot framework

### Deployment
- **Vercel** - Backend deployment (serverless)
- **Any VPS/Server** - Telegram bot worker

## Project Structure

```
.
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app entry point
│       ├── core/
│       │   └── config.py        # Configuration & settings
│       ├── routers/
│       │   ├── analyze.py       # Analysis API endpoint
│       │   └── quota.py         # Quota management endpoints
│       ├── services/
│       │   ├── fetch_data.py    # OHLCV data fetching
│       │   ├── indicators.py    # Technical indicators
│       │   ├── llm.py           # AI report generation
│       │   ├── quota.py         # User quota management
│       │   └── chart.py         # Chart generation (matplotlib)
│       └── models/
│           └── schema.py        # Pydantic schemas
├── bot/
│   ├── bot.py                   # Telegram bot main entry
│   └── handlers/
│       ├── start.py             # /start command handler
│       ├── analisa.py           # /analisa command handler
│       └── callbacks.py         # Inline button callbacks
├── api/
│   └── index.py                 # Vercel serverless handler
├── requirements.txt             # Python dependencies
├── vercel.json                  # Vercel configuration
└── env.example                  # Environment variables template
```

## Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd analisisaham-ai
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp env.example .env
```

Edit `.env` and fill in:
- `DATABASE_URL` - PostgreSQL connection string
- `GEMINI_API_KEY` - Your Google Gemini API key (get from https://aistudio.google.com/apikey)
- `SECRET_KEY` - Random secret key for app security
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token (get from @BotFather)
- `API_BASE_URL` - Backend API URL (http://localhost:8000 for local)

### 5. Setup Database

Make sure PostgreSQL is running and create the database:

```sql
CREATE DATABASE "analisisaham-db";
```

The quota table will be created automatically on first use. New users get 3 free requests.

### 6. Run Backend API Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at `http://localhost:8000`

### 7. Run Telegram Bot

In a separate terminal:

```bash
source venv/bin/activate
python bot/bot.py
```

The bot will start polling for updates.

### 8. Test the Bot

1. Find your bot on Telegram (via @BotFather)
2. Send `/start` to see welcome message
3. Send `/analisa BBCA` to analyze a stock

## API Endpoints

### POST /api/analyze

Analyze a stock ticker and generate AI report with chart.

**Request:**
```json
{
  "ticker": "BBCA",
  "user_id": "123456"
}
```

**Response:**
```json
{
  "ticker": "BBCA",
  "ohlcv_days": 180,
  "indicators": {
    "ema20": 8250.5,
    "ema50": 8170.0,
    "rsi": 65.2,
    "macd": 15.3,
    "support": 8000.0,
    "resistance": 8500.0,
    "current_price": 8200.0,
    "price_change_percent": 2.5
  },
  "ai_report": "Full AI analysis report...",
  "chart_path": "/tmp/BBCA_chart.png"
}
```

### GET /quota/check

Check user's remaining quota.

**Query Parameters:**
- `user_id` - User ID to check

**Response:**
```json
{
  "ok": true,
  "remaining": 29
}
```

### POST /quota/decrement

Decrement user's quota (called by bot before analysis).

**Request:**
```json
{
  "user_id": "123456"
}
```

## Features

- ✅ OHLCV data fetching from Yahoo Finance (6 months)
- ✅ Technical indicators calculation (EMA20/50, RSI, MACD, Support/Resistance)
- ✅ Chart generation with matplotlib (price + EMA overlays)
- ✅ AI-powered analysis reports using Gemini 2.5 Flash (full reports)
- ✅ User quota system (3 free requests for new users)
- ✅ PostgreSQL database integration
- ✅ Telegram bot with inline buttons
- ✅ Auto-send full report as .txt file if > 4000 chars

## Telegram Bot Commands

- `/start` - Show welcome message and instructions
- `/analisa TICKER` - Analyze stock (e.g., `/analisa BBCA`)

### Inline Buttons

- **Save Watchlist** - Save ticker to watchlist (coming soon)
- **Full Report** - Request full report file
- **Upgrade Plan** - Upgrade quota plan (coming soon)

## Quota System

- New users: 3 free requests
- Plans (coming soon):
  - Rp 50,000 → 30 requests
  - Rp 100,000 → 100 requests
  - Rp 500,000 → 1000 requests

## Deployment

### Backend (Vercel)

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Deploy:
```bash
vercel
```

3. Set environment variables in Vercel dashboard

### Telegram Bot (VPS/Server)

1. Deploy bot worker on any VPS or server
2. Set `API_BASE_URL` to your deployed backend URL
3. Run bot as a service:

```bash
# Using systemd
sudo nano /etc/systemd/system/stockbot.service

[Unit]
Description=Stock Analysis Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/analisisaham-ai
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target

sudo systemctl enable stockbot
sudo systemctl start stockbot
```

## License

MIT
