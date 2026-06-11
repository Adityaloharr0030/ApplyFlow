# 🤖 Internship Automation Bot

An AI-powered Python bot that **automatically** searches, scores, and applies to internships — so you can focus on building, not job hunting.

---

## 🚀 What It Does

| Step | Action | Details |
|------|--------|---------|
| 1️⃣ | **Search** | Scrapes Internshala, LinkedIn, and LetsInternship for relevant internships |
| 2️⃣ | **AI Filter** | Gemini AI (FREE) scores each listing 1–10 based on your profile match |
| 3️⃣ | **Auto-Apply** | Selenium opens Chrome and fills application forms automatically |
| 4️⃣ | **Cover Notes** | AI writes a unique, personalized cover letter for each company |
| 5️⃣ | **Cold Email** | Sends direct application emails with resume attached |
| 6️⃣ | **Track** | Logs every application to Google Sheets (or local CSV) |
| 7️⃣ | **Alert** | Sends a Telegram summary: "Applied to 7 internships today ✅" |

---

## 📦 Quick Start

### 1. Clone & Install
```bash
cd internship-bot
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy the template
cp .env.example .env

# Edit .env with your actual values:
# - GEMINI_API_KEY (free at https://aistudio.google.com/apikey)
# - GMAIL_ADDRESS + GMAIL_APP_PASSWORD (for cold emails)
# - TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID (for alerts)
# - INTERNSHALA_EMAIL + INTERNSHALA_PASSWORD (for auto-apply)
# - GOOGLE_SHEETS_CREDS_PATH (optional, for Sheets logging)
```

### 3. Update Your Profile
Edit `data/profile.json` with your actual:
- Name, college, degree
- Skills and keywords
- GitHub & LinkedIn URLs
- Resume path

### 4. Run
```bash
# One-shot run (immediate)
python main.py --run-now

# Daily scheduler (runs at 9:00 AM)
python main.py

# Custom schedule time
python main.py --time 10:30
```

---

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ (free) | Google Gemini API key — get free at [aistudio.google.com](https://aistudio.google.com/apikey) |
| `GMAIL_ADDRESS` | Optional | Your Gmail for sending cold emails |
| `GMAIL_APP_PASSWORD` | Optional | Gmail App Password (not regular password) |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot token for daily summaries |
| `TELEGRAM_CHAT_ID` | Optional | Your Telegram chat ID |
| `INTERNSHALA_EMAIL` | Optional | Internshala login email |
| `INTERNSHALA_PASSWORD` | Optional | Internshala login password |
| `LINKEDIN_EMAIL` | Optional | LinkedIn login email |
| `LINKEDIN_PASSWORD` | Optional | LinkedIn login password |
| `GOOGLE_SHEETS_CREDS_PATH` | Optional | Path to Google service account JSON |
| `GOOGLE_SHEET_NAME` | Optional | Name of the Google Sheet (default: "Internship Tracker") |

---

## 📁 Project Structure

```
internship-bot/
├── main.py                    # Pipeline orchestrator + scheduler
├── requirements.txt           # All dependencies
├── .env.example               # Environment template
├── .gitignore
├── data/
│   └── profile.json           # Your candidate profile
├── scraper/
│   ├── internshala.py         # Internshala scraper (requests + BS4)
│   ├── linkedin.py            # LinkedIn scraper (Selenium)
│   └── letsinternship.py      # LetsInternship scraper (requests + BS4)
├── agent/
│   ├── filter.py              # AI listing scorer (Gemini — free)
│   └── cover_note.py          # AI cover note generator (Gemini — free)
├── applicator/
│   ├── selenium_fill.py       # Auto-fill Internshala applications
│   └── email_send.py          # Cold email sender via Gmail
├── tracker/
│   └── sheets.py              # Google Sheets logger + CSV fallback
├── notifier/
│   └── telegram.py            # Telegram daily summary
└── utils/
    └── dedup.py               # Listing deduplication
```

---

## 🛡️ Safety Features

- **Never crashes**: Every function has try/except — one failure won't stop the whole run
- **No hardcoded secrets**: All API keys read from `.env`
- **Deduplication**: Won't apply twice to the same company/role
- **CAPTCHA detection**: Logs and skips gracefully if bot detection triggers
- **Polite scraping**: 2–3 second delays between requests
- **Fallback logging**: If Google Sheets fails, auto-logs to local CSV
- **Screenshot on failure**: Saves debug screenshots to `./logs/screenshots/`

---

## 📬 Getting a Gmail App Password

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Security → 2-Step Verification (enable if not already)
3. Search "App passwords" → Generate one for "Mail"
4. Paste the 16-character password into `.env`

---

## 🤖 Setting Up Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the prompts
3. Copy the bot token → paste in `.env` as `TELEGRAM_BOT_TOKEN`
4. Message your bot, then visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Find your `chat_id` → paste in `.env` as `TELEGRAM_CHAT_ID`

---

## 📊 Google Sheets Setup (Optional)

1. Create a Google Cloud project
2. Enable the Google Sheets API
3. Create a Service Account → download the JSON key
4. Save it as `./data/google_creds.json`
5. Share your Google Sheet with the service account email

If you skip this, the bot automatically logs to `./logs/applications.csv` instead.

---

## License

MIT — built for personal automation use.
