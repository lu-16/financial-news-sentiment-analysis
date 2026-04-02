# Financial News Sentiment Analyzer

A Streamlit web app that fetches recent financial news from Google News and classifies each article's market sentiment using OpenAI GPT-4o-mini. Results can be emailed as an HTML report.

## Features

- **Keyword search** — enter one or more comma-separated keywords; articles from the past 2 hours are fetched via Google News RSS (no API key required)
- **Batch sentiment analysis** — all articles are sent to OpenAI in a single call; each article gets a `positive / negative / neutral` label, a confidence score, and a one-sentence reasoning
- **Interactive charts** — sentiment distribution pie chart and confidence score box plot side by side
- **Article table** — sortable table with clickable article links
- **Email report** — optional HTML email sent via Gmail SMTP

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- An OpenAI API key
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) (requires 2FA)

## Setup

**1. Clone and install dependencies**

```bash
git clone <repo-url>
cd financial-news-sentiment-analysis
uv sync
```

**2. Configure environment variables**

```bash
cp .env.example .env
```

Edit `.env` and fill in the three values:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `GMAIL_USER` | Gmail address used to send reports |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your regular password) |

**3. Set the app password** (for the login gate)

Create `.streamlit/secrets.toml` if it doesn't exist and add:

```toml
APP_PASSWORD = "your-password-here"
```

**4. Run the app**

```bash
uv run streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Project Structure

```
financial-news-sentiment-analysis/
├── app.py                  # Streamlit UI — layout, form, charts, table
├── news_fetcher.py         # Fetches articles from Google News RSS
├── sentiment_analyzer.py   # Calls OpenAI GPT-4o-mini for batch sentiment
├── email_sender.py         # Builds and sends the HTML email report
├── pyproject.toml          # Project metadata and dependencies (uv)
├── .env.example            # Template for environment variables
└── .streamlit/
    ├── config.toml         # Streamlit theme / server config
    └── secrets.toml        # APP_PASSWORD (not committed)
```

## How It Works

1. **News fetching** (`news_fetcher.py`) — constructs a Google News RSS query using `feedparser`, filters articles to those published within the last 2 hours, and returns title, source, URL, description, and publish time.

2. **Sentiment analysis** (`sentiment_analyzer.py`) — batches all article titles and summaries into a single prompt sent to `gpt-4o-mini`. The model returns a JSON array; each item has `index`, `sentiment`, `score`, and `reasoning`. Falls back to `neutral / 0.5` if parsing fails.

3. **Email report** (`email_sender.py`) — builds a responsive HTML email with a summary header (positive / negative / neutral counts) and a per-article table. Sent via Gmail SMTP with STARTTLS on port 587.

## Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI |
| `openai` | Sentiment analysis via GPT-4o-mini |
| `feedparser` | Parse Google News RSS feeds |
| `plotly` | Pie chart and box plot |
| `pandas` | Article table |
| `python-dotenv` | Load `.env` variables |
| `watchdog` | Streamlit file watcher (dev) |

## Notes

- Google News RSS is free and requires no API key, but article availability within the 2-hour window depends on Google's indexing speed.
- The OpenAI call is billed per token. A typical batch of 20–30 short articles costs a fraction of a cent with `gpt-4o-mini`.
- The Gmail App Password is separate from your account password and can be revoked independently at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
