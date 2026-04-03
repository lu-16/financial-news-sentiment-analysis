import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from email_sender import send_report
from news_fetcher import fetch_articles
from sentiment_analyzer import analyze_sentiment

load_dotenv()

_POSITION_KEYWORDS = {"LONG", "SHORT", "BUY", "SELL", "HOLD"}


def _parse_positions(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def _tickers_from_positions(positions: list[str]) -> list[str]:
    tickers = []
    for p in positions:
        tickers.extend(t.upper() for t in re.findall(r'\b[A-Za-z]{2,5}\b', p))
    return [t for t in dict.fromkeys(tickers) if t not in _POSITION_KEYWORDS]

st.set_page_config(
    page_title="News Sentiment Analyzer",
    page_icon="icon.svg",
    layout="wide",
)

st.title(":newspaper: Financial News Sentiment Analyzer")

# ── Password gate ─────────────────────────────────────────────────────────────
_app_password = st.secrets.get("APP_PASSWORD", "")
if _app_password and not st.session_state.get("authenticated"):
    pwd = st.text_input("Password", type="password")
    if st.button("Enter"):
        if pwd == _app_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# ── Positions ────────────────────────────────────────────────────────────────
st.subheader("My Positions")
st.caption("One per line, e.g.: Long AAPL 100 shares")
positions_raw = st.text_area(
    "Positions",
    value=st.session_state.get("positions_raw", ""),
    height=120,
    placeholder="Long AAPL 100 shares\nShort BTC\nLong NVDA 50 shares",
    label_visibility="collapsed",
)
st.session_state["positions_raw"] = positions_raw

# ── Input form ──────────────────────────────────────────────────────────────
_INTERVAL_OPTIONS = {
    "Last 30 min": 0.5,
    "Last 1 hr": 1,
    "Last 2 hr": 2,
    "Last 6 hr": 6,
    "Last 12 hr": 12,
    "Last 24 hr": 24,
}

with st.form("input_form"):
    interval_label = st.selectbox(
        "News time window",
        options=list(_INTERVAL_OPTIONS.keys()),
        index=2,  # default: Last 2 hr
    )
    email_input = st.text_input(
        "Send report to email (optional)",
        value="hauwen95.huang@gmail.com",
        placeholder="you@example.com",
    )
    hide_unrelated = st.checkbox(
        "Hide unrelated articles",
        value=st.session_state.get("hide_unrelated", True),
    )
    st.session_state["hide_unrelated"] = hide_unrelated
    col_left, col_right = st.columns([1, 4])
    with col_left:
        submitted = st.form_submit_button("Analyze", width='stretch', type="primary")

# ── On submit ────────────────────────────────────────────────────────────────
if submitted:
    positions = _parse_positions(st.session_state.get("positions_raw", ""))
    keywords = _tickers_from_positions(positions)

    if not keywords:
        st.warning("Please add at least one position above.")
        st.stop()

    # Clear previous results
    for key in ("results", "summary", "keywords", "email_status", "positions"):
        st.session_state.pop(key, None)

    hours_back = _INTERVAL_OPTIONS[interval_label]
    with st.spinner("Fetching news articles from Google News..."):
        try:
            articles = fetch_articles(keywords, hours_back=hours_back)
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Failed to fetch news: {e}")
            st.stop()

    if not articles:
        st.info(
            f"**No articles found for the {interval_label.lower()}.**\n\n"
            "This is likely because NewsAPI's free developer plan has a **24-hour indexing delay** "
            "— articles published in the last 2 hours are not yet available on the free tier.\n\n"
            "**Options:**\n"
            "- Upgrade to a paid NewsAPI plan for real-time results\n"
            "- Try broader or more popular keywords\n"
            "- The code is correct and will work as expected with a paid plan"
        )
        st.stop()

    with st.spinner(f"Analyzing sentiment of {len(articles)} articles with OpenAI..."):
        try:
            analyzed = analyze_sentiment(articles, positions=positions)
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Sentiment analysis failed: {e}")
            st.stop()

    summary = {
        "positive": sum(1 for a in analyzed if a["sentiment"] == "positive"),
        "negative": sum(1 for a in analyzed if a["sentiment"] == "negative"),
        "neutral": sum(1 for a in analyzed if a["sentiment"] == "neutral"),
    }

    st.session_state["results"] = analyzed
    st.session_state["summary"] = summary
    st.session_state["keywords"] = keywords
    st.session_state["positions"] = positions

    # Send email if address provided
    if email_input.strip():
        with st.spinner("Sending email report..."):
            ok = send_report(email_input.strip(), keywords, analyzed, summary, positions=positions)
        st.session_state["email_status"] = ("success", email_input.strip()) if ok else ("error", email_input.strip())

# ── Results display ──────────────────────────────────────────────────────────
if "results" in st.session_state:
    analyzed = st.session_state["results"]
    summary = st.session_state["summary"]
    keywords = st.session_state["keywords"]
    positions = st.session_state.get("positions", [])

    display_articles = analyzed

    st.divider()

    hide_unrelated = st.session_state.get("hide_unrelated", True)
    if positions:
        display_articles = (
            [a for a in analyzed if a.get("portfolio_impact") != "unrelated"]
            if hide_unrelated
            else analyzed
        )

    hidden_count = len(analyzed) - len(display_articles)
    subtitle = f"Results for: `{', '.join(keywords)}`  ({len(display_articles)} articles"
    if hidden_count:
        subtitle += f", {hidden_count} unrelated hidden"
    subtitle += ")"
    st.subheader(subtitle)

    # Email status banner
    if "email_status" in st.session_state:
        status, addr = st.session_state["email_status"]
        if status == "success":
            st.success(f"Report sent to **{addr}**")
        else:
            st.warning(f"Failed to send email to {addr}. Results are shown below.")

    # Summary metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Positive", summary["positive"])
    c2.metric("Negative", summary["negative"])
    c3.metric("Neutral", summary["neutral"])

    # Portfolio impact metrics (only when positions were provided)
    if positions:
        beneficial = sum(1 for a in analyzed if a.get("portfolio_impact") == "beneficial")
        detrimental = sum(1 for a in analyzed if a.get("portfolio_impact") == "detrimental")
        unrelated = sum(1 for a in analyzed if a.get("portfolio_impact") == "unrelated")
        st.divider()
        st.caption(f"Portfolio Impact — positions: {', '.join(positions)}")
        p1, p2, p3 = st.columns(3)
        p1.metric("Beneficial", beneficial)
        p2.metric("Detrimental", detrimental)
        p3.metric("Unrelated", unrelated)

    # Pie chart + bar chart side by side
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        fig_pie = px.pie(
            values=[summary["positive"], summary["negative"], summary["neutral"]],
            names=["Positive", "Negative", "Neutral"],
            color=["Positive", "Negative", "Neutral"],
            color_discrete_map={
                "Positive": "#28a745",
                "Negative": "#dc3545",
                "Neutral": "#6c757d",
            },
            title="Sentiment Distribution",
        )
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, width='stretch')

    with chart_col2:
        # Confidence score distribution
        df_scores = pd.DataFrame([
            {"Sentiment": a["sentiment"].capitalize(), "Confidence": a["score"]}
            for a in display_articles
        ])
        if df_scores.empty:
            st.info("No articles to display confidence scores for.")
        else:
            fig_box = px.box(
                df_scores,
                x="Sentiment",
                y="Confidence",
                color="Sentiment",
                color_discrete_map={
                    "Positive": "#28a745",
                    "Negative": "#dc3545",
                    "Neutral": "#6c757d",
                },
                title="Confidence Score Distribution",
            )
            st.plotly_chart(fig_box, width='stretch')

    # Article table
    st.subheader("Article Details")

    rows = []
    for a in display_articles:
        row = {
            "Title": a["title"],
            "Source": a["source"],
            "Sentiment": a["sentiment"].capitalize(),
            "Confidence": f"{a['score']:.0%}",
            "Horizon": a.get("impact_horizon", "").replace("-", "\u2011"),  # non-breaking hyphen
            "Price Impact": a.get("price_impact_estimate", "N/A"),
            "Reasoning": a["reasoning"],
            "Published": a["published_at"][:16].replace("T", " ") if a["published_at"] else "",
            "URL": a["url"],
        }
        if positions:
            row["Portfolio Impact"] = a.get("portfolio_impact", "unrelated").capitalize()
            row["Impact Reasoning"] = a.get("impact_reasoning", "")
        rows.append(row)

    df = pd.DataFrame(rows)

    col_config = {
        "URL": st.column_config.LinkColumn("URL", display_text="Open"),
        "Title": st.column_config.TextColumn("Title", width="large"),
        "Reasoning": st.column_config.TextColumn("Reasoning", width="large"),
    }
    if positions:
        col_config["Impact Reasoning"] = st.column_config.TextColumn("Impact Reasoning", width="large")

    st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        column_config=col_config,
    )
