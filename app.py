import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from email_sender import send_report
from news_fetcher import fetch_articles
from sentiment_analyzer import analyze_sentiment

load_dotenv()

st.set_page_config(
    page_title="News Sentiment Analyzer",
    page_icon="📰",
    layout="wide",
)

st.title("📰 Financial News Sentiment Analyzer")
st.caption("Enter keywords to fetch recent global news and analyze sentiment with OpenAI.")

# ── Password gate ─────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    pwd = st.text_input("Password", type="password")
    if st.button("Enter"):
        if pwd == st.secrets.get("APP_PASSWORD", ""):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# ── Input form ──────────────────────────────────────────────────────────────
with st.form("input_form"):
    keywords_input = st.text_input(
        "Keywords (comma-separated)",
        value="bitcoin",
        placeholder="e.g. bitcoin, fed rate, apple, nvidia",
    )
    email_input = st.text_input(
        "Send report to email (optional)",
        value="hauwen95.huang@gmail.com",
        placeholder="you@example.com",
    )
    col_left, col_right = st.columns([1, 4])
    with col_left:
        submitted = st.form_submit_button("Analyze", width='stretch', type="primary")

# ── On submit ────────────────────────────────────────────────────────────────
if submitted:
    keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
    if not keywords:
        st.warning("Please enter at least one keyword.")
        st.stop()

    # Clear previous results
    for key in ("results", "summary", "keywords", "email_status"):
        st.session_state.pop(key, None)

    with st.spinner("Fetching news articles from NewsAPI..."):
        try:
            articles = fetch_articles(keywords)
        except ValueError as e:
            st.error(f"Configuration error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Failed to fetch news: {e}")
            st.stop()

    if not articles:
        st.info(
            "**No articles found for the past 2 hours.**\n\n"
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
            analyzed = analyze_sentiment(articles)
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

    # Send email if address provided
    if email_input.strip():
        with st.spinner("Sending email report..."):
            ok = send_report(email_input.strip(), keywords, analyzed, summary)
        st.session_state["email_status"] = ("success", email_input.strip()) if ok else ("error", email_input.strip())

# ── Results display ──────────────────────────────────────────────────────────
if "results" in st.session_state:
    analyzed = st.session_state["results"]
    summary = st.session_state["summary"]
    keywords = st.session_state["keywords"]

    st.divider()
    st.subheader(f"Results for: `{', '.join(keywords)}`  ({len(analyzed)} articles)")

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
        st.plotly_chart(fig_pie, use_container_width=True)

    with chart_col2:
        # Confidence score distribution
        df_scores = pd.DataFrame([
            {"Sentiment": a["sentiment"].capitalize(), "Confidence": a["score"]}
            for a in analyzed
        ])
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
        st.plotly_chart(fig_box, use_container_width=True)

    # Article table
    st.subheader("Article Details")

    df = pd.DataFrame([
        {
            "Title": a["title"],
            "Source": a["source"],
            "Sentiment": a["sentiment"].capitalize(),
            "Confidence": f"{a['score']:.0%}",
            "Reasoning": a["reasoning"],
            "Published": a["published_at"][:16].replace("T", " ") if a["published_at"] else "",
            "URL": a["url"],
        }
        for a in analyzed
    ])

    st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        column_config={
            "URL": st.column_config.LinkColumn("URL", display_text="Open"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Reasoning": st.column_config.TextColumn("Reasoning", width="large"),
        },
    )
