import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

_SENTIMENT_COLORS = {
    "positive": "#28a745",
    "negative": "#dc3545",
    "neutral": "#6c757d",
}

_IMPACT_COLORS = {
    "beneficial": "#28a745",
    "detrimental": "#dc3545",
    "unrelated": "#6c757d",
}


def send_report(
    recipient_email: str,
    keywords: list[str],
    articles: list[dict],
    summary: dict,
    positions: list[str] | None = None,
) -> bool:
    """
    Send an HTML sentiment report email via Gmail SMTP.
    Returns True on success, False on failure.
    """
    gmail_user = os.getenv("GMAIL_USER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if not gmail_user or not app_password:
        print("GMAIL_USER or GMAIL_APP_PASSWORD not set.", file=sys.stderr)
        return False

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    keywords_str = ", ".join(keywords)
    subject = f"News Sentiment Report: {keywords_str} — {timestamp}"

    html_body = _build_html(keywords, articles, summary, timestamp, positions=positions)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(gmail_user, app_password)
            smtp.sendmail(gmail_user, recipient_email, msg.as_string())
        return True
    except Exception as exc:
        print(f"Email send failed: {exc}", file=sys.stderr)
        return False


def _build_html(
    keywords: list[str],
    articles: list[dict],
    summary: dict,
    timestamp: str,
    positions: list[str] | None = None,
) -> str:
    keywords_str = ", ".join(keywords)
    pos = summary.get("positive", 0)
    neg = summary.get("negative", 0)
    neu = summary.get("neutral", 0)

    rows = ""
    for a in articles:
        color = _SENTIMENT_COLORS.get(a.get("sentiment", "neutral"), "#6c757d")
        sentiment_label = a.get("sentiment", "neutral").capitalize()
        score_pct = f"{a.get('score', 0.5):.0%}"
        horizon = a.get("impact_horizon", "")
        price_est = a.get("price_impact_estimate", "N/A")
        impact_cells = ""
        if positions:
            impact = a.get("portfolio_impact", "unrelated")
            impact_color = _IMPACT_COLORS.get(impact, "#6c757d")
            impact_label = impact.capitalize()
            impact_reasoning = a.get("impact_reasoning", "")
            impact_cells = f"""
          <td style="padding:8px;border-bottom:1px solid #eee;">
            <span style="background:{impact_color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">
              {impact_label}
            </span>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#555;font-size:13px;">{impact_reasoning}</td>"""
        rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;">
            <a href="{a['url']}" style="color:#0066cc;text-decoration:none;">{a['title']}</a>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#555;">{a['source']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">
            <span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;">
              {sentiment_label}
            </span>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">{score_pct}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#555;text-align:center;">{horizon}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#555;text-align:center;">{price_est}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#555;font-size:13px;">{a.get('reasoning','')}</td>{impact_cells}
        </tr>"""

    positions_block = ""
    if positions:
        positions_str = " &nbsp;|&nbsp; ".join(positions)
        positions_block = f"""
  <div style="background:#f0f4ff;border-left:4px solid #4a6cf7;padding:12px 16px;border-radius:4px;margin-bottom:20px;">
    <strong>Positions analyzed:</strong> {positions_str}
  </div>"""

    impact_headers = ""
    if positions:
        impact_headers = """
        <th style="padding:10px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Portfolio Impact</th>
        <th style="padding:10px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Impact Reasoning</th>"""

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:1000px;margin:0 auto;padding:20px;color:#333;">

  <div style="background:#1a1a2e;color:#fff;padding:24px;border-radius:8px;margin-bottom:24px;">
    <h1 style="margin:0;font-size:22px;">News Sentiment Report</h1>
    <p style="margin:8px 0 0;opacity:0.8;">Keywords: <strong>{keywords_str}</strong> &nbsp;|&nbsp; {timestamp}</p>
  </div>

  <div style="display:flex;gap:16px;margin-bottom:24px;">
    <div style="flex:1;background:#d4edda;border-left:4px solid #28a745;padding:16px;border-radius:4px;">
      <div style="font-size:28px;font-weight:bold;color:#28a745;">{pos}</div>
      <div style="color:#155724;">Positive</div>
    </div>
    <div style="flex:1;background:#f8d7da;border-left:4px solid #dc3545;padding:16px;border-radius:4px;">
      <div style="font-size:28px;font-weight:bold;color:#dc3545;">{neg}</div>
      <div style="color:#721c24;">Negative</div>
    </div>
    <div style="flex:1;background:#e2e3e5;border-left:4px solid #6c757d;padding:16px;border-radius:4px;">
      <div style="font-size:28px;font-weight:bold;color:#6c757d;">{neu}</div>
      <div style="color:#383d41;">Neutral</div>
    </div>
  </div>
{positions_block}
  <h2 style="font-size:16px;margin-bottom:12px;">Article Details ({len(articles)} articles)</h2>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">
    <thead>
      <tr style="background:#f8f9fa;">
        <th style="padding:10px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Title</th>
        <th style="padding:10px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Source</th>
        <th style="padding:10px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Sentiment</th>
        <th style="padding:10px 8px;text-align:center;border-bottom:2px solid #dee2e6;">Confidence</th>
        <th style="padding:10px 8px;text-align:center;border-bottom:2px solid #dee2e6;">Horizon</th>
        <th style="padding:10px 8px;text-align:center;border-bottom:2px solid #dee2e6;">Price Impact</th>
        <th style="padding:10px 8px;text-align:left;border-bottom:2px solid #dee2e6;">Reasoning</th>{impact_headers}
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <p style="margin-top:32px;font-size:12px;color:#999;border-top:1px solid #eee;padding-top:12px;">
    This report is generated automatically and is for informational purposes only.
    It does not constitute financial advice.
  </p>
</body>
</html>"""
