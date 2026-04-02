# Financial News Sentiment Analyzer

A Streamlit web app that fetches recent financial news from Google News and classifies each article's market sentiment using OpenAI GPT-4o-mini. Results can be emailed as an HTML report.

## Features

- **Password gate** — app is protected by a configurable login password (`APP_PASSWORD`)
- **Keyword search** — enter one or more comma-separated keywords; news is fetched via Google News RSS (no API key required)
- **Configurable time window** — fetch articles from the last 30 min, 1 hr, 2 hr, 6 hr, 12 hr, or 24 hr
- **Portfolio positions** — enter your current positions (e.g. `Long AAPL 100 shares`, `Short BTC`) in the sidebar; tickers are automatically extracted and added to the keyword search
- **Batch sentiment analysis** — all articles are sent to OpenAI in a single call; each article gets:
  - `positive / negative / neutral` label with a confidence score and one-sentence reasoning
  - **Impact horizon** — `short-term`, `long-term`, or `both`
  - **Price impact estimate** — estimated % price move based on historical analogues
- **Portfolio impact analysis** — when positions are provided, each article is classified as `beneficial`, `detrimental`, or `unrelated` to your portfolio, with reasoning
- **Hide unrelated articles** — sidebar checkbox to filter out articles irrelevant to your positions
- **Interactive charts** — sentiment distribution pie chart and confidence score box plot side by side
- **Article table** — sortable table with clickable links; shows portfolio impact columns when positions are set
- **Email report** — optional HTML email sent via Gmail SMTP, including portfolio impact section when positions are provided

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

1. **News fetching** (`news_fetcher.py`) — constructs a Google News RSS query using `feedparser`, filters articles to those published within the selected time window, and returns title, source, URL, description, and publish time.

2. **Keyword enrichment** (`app.py`) — if portfolio positions are entered in the sidebar, ticker symbols are extracted automatically (e.g. `AAPL`, `BTC`) and merged into the keyword list so relevant news is always fetched.

3. **Sentiment analysis** (`sentiment_analyzer.py`) — batches all article titles and summaries into a single prompt sent to `gpt-4o-mini`. Without positions, the model returns `sentiment`, `score`, `reasoning`, `impact_horizon`, and `price_impact_estimate` per article. With positions, it additionally returns `portfolio_impact` (`beneficial` / `detrimental` / `unrelated`) and `impact_reasoning`. Falls back to `neutral / 0.5` if parsing fails.

4. **Email report** (`email_sender.py`) — builds a responsive HTML email with a summary header (positive / negative / neutral counts), a portfolio positions block (when provided), and a per-article table including horizon, price impact, and portfolio impact columns. Sent via Gmail SMTP with STARTTLS on port 587.

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

- Google News RSS is free and requires no API key, but article availability within short time windows depends on Google's indexing speed.
- The OpenAI call is billed per token. A typical batch of 20–30 short articles costs a fraction of a cent with `gpt-4o-mini`.
- The Gmail App Password is separate from your account password and can be revoked independently at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
