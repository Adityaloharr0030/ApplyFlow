# ApplyFlow — Multi-Platform Auto-Apply Bot 🤖

An automated bot that scrapes internship/job listings from multiple platforms, scores them with AI, generates personalized cover notes, auto-applies, and sends real-time phone notifications.

## Supported Platforms

| Platform | Search | Auto-Apply | Notes |
|---|---|---|---|
| **Internshala** | ✅ requests/BS4 | ✅ Selenium | One session per run, cover letter auto-fill |
| **LinkedIn** | ✅ Guest API | ✅ Easy Apply only | Non-Easy Apply logged as manual |
| **Indeed** | ✅ python-jobspy | ✅ Indeed Apply | External ATS redirects logged as manual |
| **Unstop** | ✅ JSON API | ✅ Selenium | Direct API scraping, 1-click apply |
| **Generic/Cold Email** | Target company list | ✅ Cold email | Finds ATS links or HR emails, sends via Gmail |

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/Adityaloharr0030/ApplyFlow.git
cd ApplyFlow/internship-bot
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your credentials
# Edit data/profile.json with your info

# 3. Run (dry-run by default — no real applications sent)
python main.py --run-now
```

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `GEMINI_MODEL` | No | Default: `gemini-3.5-flash` |
| `DRY_RUN` | No | Default: `true`. Set `false` for live applications |
| `INTERNSHALA_EMAIL/PASSWORD` | For Internshala | Login credentials |
| `LINKEDIN_EMAIL/PASSWORD` | For LinkedIn | Login credentials |
| `UNSTOP_EMAIL/PASSWORD` | For Unstop | Login credentials |
| `GMAIL_ADDRESS/APP_PASSWORD` | For cold emails | Gmail App Password (not regular password) |
| `TELEGRAM_BOT_TOKEN/CHAT_ID` | For notifications | Create bot via @BotFather |
| `NTFY_TOPIC` | For notifications | Long random string (see below) |
| `*_MAX_APPLIES` | No | Per-platform daily caps (default: 10-15) |
| `HEADLESS` | No | Default: `true`. Set `false` to see browsers |

### Profile (`data/profile.json`)

```json
{
  "name": "Your Name",
  "degree": "B.Tech Computer Engineering",
  "year": "2027",
  "email": "you@gmail.com",
  "skills": ["react", "node.js", "python"],
  "keywords": ["full stack", "frontend", "backend"],
  "exclude_keywords": ["sales", "marketing"],
  "location_preferences": ["remote", "bangalore", "pune"],
  "job_types": ["internship", "full-time"],
  "countries": ["India"],
  "target_companies": ["google.com", "amazon.jobs"],
  "resume_path": "./data/resume.pdf"
}
```

- **`target_companies`**: Domains of companies for the cold email engine
- **`resume_path`**: Path to your resume PDF (validated on startup)

## Notifications

### Telegram
1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get your chat ID
3. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`

### ntfy.sh (zero-signup push notifications)
1. Pick a long random topic string (e.g., `applyflow-a8x9y2q5`)
2. Set `NTFY_TOPIC` in `.env`
3. Install the free [ntfy app](https://ntfy.sh/) on your phone
4. Subscribe to your topic

> ⚠️ **Security note**: Public ntfy.sh topics are not access-controlled. Anyone who guesses the exact topic string can read your notifications. Use a long random string, not something guessable like "applyflow".

### WhatsApp (via CallMeBot)
1. Send a WhatsApp message to the CallMeBot number to get your API key. See: [CallMeBot Free API](https://www.callmebot.com/blog/free-api-whatsapp-messages/)
2. Set `WHATSAPP_PHONE` and `WHATSAPP_API_KEY` in `.env`
3. *Note*: This is an unofficial 3rd-party service, so the bot number occasionally resets. Ntfy is recommended as the primary mobile notification channel.

**Notification types:**
- `✅ Applied — {title} @ {company} via {platform}` — instant, per-application
- `📧 Cold email sent — {company}` — instant
- `⚠️ {platform} blocked after repeated CAPTCHA — pausing for today` — circuit breaker alert
- End-of-run digest summary

## 🚀 Production Deployment (Docker + PostgreSQL)

ApplyFlow is designed to be deployed to a cloud server using Docker.

1. Ensure Docker Desktop is running or you are on a Linux server with Docker installed.
2. Provide a PostgreSQL connection string in `.env` as `DATABASE_URL`, or use the built-in database container by running:
   ```bash
   docker compose up -d
   ```
3. The dashboard will be available on `http://localhost:8000` (API) and the frontend on the configured port.
4. The background `worker` container automatically polls the database for new job requests and runs them headlessly.

---

## 🏗 Architecture & Modules

- **`dashboard.py`**: Unified FastAPI application serving both the React frontend and API routes.
- **`worker.py`**: A background process that safely consumes run-jobs from the database.
- **`core/models.py`**: SQLModel schemas that ensure tight data validation across the system.
- **`agent/filter.py`**: Core LLM scoring logic.
- **`core/logger.py`**: Structured error tracking via the PostgreSQL database.

---

## Safety Features

- **DRY_RUN=true** (default): Scrapes, scores, generates cover letters, sends notifications, but never clicks Submit or sends real emails
- **Circuit Breaker**: 3 CAPTCHA/blocks in one run → platform paused for the rest of the run
- **Daily Caps**: Configurable per-platform limits to avoid account bans
- **Random Delays**: 2-5 second delays between all requests
- **One Session Per Run**: Single browser session reused across all listings per platform
- **Auto-Apply**: Submits applications completely in the background using headless Chrome.
- **Production Ready**: Fully Dockerized with a PostgreSQL database, background job queue (`worker.py`), and a unified FastAPI dashboard.
- **Smart Filtering**: Uses LLMs (Gemini/Groq) to read job descriptions and skip irrelevant listings.

## Architecture

```
platforms/
  base.py            # Platform ABC with circuit breaker logic
  internshala.py      # Internshala search + apply
  linkedin.py         # LinkedIn guest API search + Easy Apply
  indeed.py           # python-jobspy search + Indeed Apply
  unstop.py           # JSON API search + Selenium apply
  generic_web.py      # Target company cold email fallback

agent/
  filter.py           # AI + local keyword scoring
  cover_note.py       # AI + template cover letter generation

notifier/
  telegram.py         # Instant + digest notifications
  push.py             # ntfy.sh instant + digest notifications
  whatsapp.py         # CallMeBot WhatsApp notifications

utils/
  browser.py          # Shared Chrome driver management
  dedup.py            # URL-based deduplication
  email_send.py       # Cold email via Gmail SMTP
```

## Usage

```bash
# One-shot run (respects DRY_RUN from .env)
python main.py --run-now

# Force dry-run via CLI flag
python main.py --run-now --dry-run

# Schedule daily at 9:00 AM
python main.py

# Schedule at custom time
python main.py --time 10:30
```

## Author

Aditya Lohar
