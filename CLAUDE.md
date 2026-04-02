# Financial News Sentiment Analyzer

## Package Management

This project uses **uv**. Do not use pip or manually manage `.venv`.

```bash
# Install / sync dependencies
uv sync

# Add a new dependency
uv add <package>

# Remove a dependency
uv remove <package>
```

Dependencies are declared in `pyproject.toml`. The lockfile is `uv.lock`.

## Running the App

```bash
uv run streamlit run app.py
```

## Environment Variables

Copy `.env.example` to `.env` and fill in all three values before running:

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `GMAIL_USER` | Gmail address used to send reports |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not your regular password) |

News is fetched from Google News RSS — no API key required.

Generate a Gmail App Password at <https://myaccount.google.com/apppasswords> (requires 2FA enabled).
