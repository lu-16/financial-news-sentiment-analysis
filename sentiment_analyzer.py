import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """You are a financial news sentiment analyst. You will receive a list of news articles and must classify each one's sentiment regarding financial markets, assets, or economic conditions.

Return ONLY a valid JSON array with no other text, markdown, or explanation.
Each element must have exactly these fields:
- "index": integer (matching the article number in the input, 0-based)
- "sentiment": exactly one of "positive", "negative", or "neutral"
- "score": float between 0.0 and 1.0 representing confidence
- "reasoning": string, one sentence explaining your classification
- "impact_horizon": exactly one of "short-term", "long-term", or "both" — the time horizon over which this news is likely to affect prices (short-term = hours to weeks, long-term = months to years)
- "price_impact_estimate": estimated percentage price move for the primary asset or sector mentioned, e.g. "+1% to +3%", "-0.5% to -2%", "minimal (<0.5%)" — base this on historical analogues for similar news events

Rules:
- "positive" means the news is likely bullish for relevant assets or the economy
- "negative" means the news is likely bearish for relevant assets or the economy
- "neutral" means unclear market impact or purely factual reporting
- Base reasoning on the financial implications, not general tone"""

SYSTEM_PROMPT_WITH_POSITIONS = """You are a financial news sentiment analyst with knowledge of a specific investor's portfolio positions.

For each article you must:
1. Classify the article's general market sentiment (positive/negative/neutral).
2. Determine whether the article is BENEFICIAL, DETRIMENTAL, or UNRELATED to the investor's specific portfolio.
3. Assess the time horizon of the impact and estimate the price move for the relevant asset.

Apply this logic strictly for portfolio_impact:
- Positive news + Long position in the affected asset = beneficial
- Positive news + Short position in the affected asset = detrimental
- Negative news + Long position in the affected asset = detrimental
- Negative news + Short position in the affected asset = beneficial
- News unrelated to any held position = unrelated

Return ONLY a valid JSON array with no other text, markdown, or explanation.
Each element must have exactly these fields:
- "index": integer (0-based, matching the article number in the input)
- "sentiment": exactly one of "positive", "negative", or "neutral"
- "score": float between 0.0 and 1.0 representing confidence
- "reasoning": string, one sentence explaining the sentiment classification
- "portfolio_impact": exactly one of "beneficial", "detrimental", or "unrelated"
- "impact_reasoning": string, one sentence explaining how this article affects the portfolio
- "impact_horizon": exactly one of "short-term", "long-term", or "both" — the time horizon over which this news is likely to affect prices (short-term = hours to weeks, long-term = months to years)
- "price_impact_estimate": estimated percentage price move for the primary affected asset, e.g. "+1% to +3%", "-0.5% to -2%", "minimal (<0.5%)" — base this on historical analogues for similar news events; use "N/A" if unrelated to any priced asset

Rules:
- "positive" means the news is likely bullish for relevant assets or the economy
- "negative" means the news is likely bearish for relevant assets or the economy
- "neutral" means unclear market impact or purely factual reporting
- If an article does not clearly relate to any held position, set portfolio_impact to "unrelated" and impact_reasoning to "Not related to any held position."
- Base reasoning on the financial implications, not general tone"""


def analyze_sentiment(articles: list[dict], positions: list[str] | None = None) -> list[dict]:
    """
    Send all articles to OpenAI in a single batch call and return
    articles with sentiment fields (sentiment, score, reasoning) added.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment.")

    if not articles:
        return articles

    has_positions = bool(positions)
    client = OpenAI(api_key=api_key)
    system_prompt = SYSTEM_PROMPT_WITH_POSITIONS if has_positions else SYSTEM_PROMPT
    prompt = _build_prompt(articles, positions=positions)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=8000,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )

    raw_text = response.choices[0].message.content
    return _parse_response(raw_text, articles, has_positions=has_positions)


def _build_prompt(articles: list[dict], positions: list[str] | None = None) -> str:
    lines = []
    if positions:
        lines.append("INVESTOR POSITIONS:")
        for p in positions:
            lines.append(f"  - {p}")
        lines.append("")
    lines.append(f"Analyze the sentiment of these {len(articles)} financial news articles:\n")
    for i, a in enumerate(articles):
        desc = a["description"][:150] if a["description"] else "(no description)"
        lines.append(f"[{i}] Title: {a['title']}")
        lines.append(f"    Source: {a['source']}")
        lines.append(f"    Summary: {desc}\n")
    lines.append(
        f"Return a JSON array with {len(articles)} objects, "
        "one per article, using the 0-based index shown in brackets."
    )
    return "\n".join(lines)


def _parse_response(raw_json: str, articles: list[dict], has_positions: bool = False) -> list[dict]:
    results = list(articles)

    try:
        text = raw_json.strip()
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0]

        parsed = json.loads(text)
        sentiment_map = {item["index"]: item for item in parsed}
    except (json.JSONDecodeError, KeyError, TypeError):
        for article in results:
            article["sentiment"] = "neutral"
            article["score"] = 0.5
            article["reasoning"] = "Analysis unavailable (parse error)"
            article["impact_horizon"] = "short-term"
            article["price_impact_estimate"] = "N/A"
            if has_positions:
                article["portfolio_impact"] = "unrelated"
                article["impact_reasoning"] = ""
        return results

    for i, article in enumerate(results):
        item = sentiment_map.get(i)
        if item:
            article["sentiment"] = item.get("sentiment", "neutral")
            article["score"] = float(item.get("score", 0.5))
            article["reasoning"] = item.get("reasoning", "")
            article["impact_horizon"] = item.get("impact_horizon", "short-term")
            article["price_impact_estimate"] = item.get("price_impact_estimate", "N/A")
            if has_positions:
                article["portfolio_impact"] = item.get("portfolio_impact", "unrelated")
                article["impact_reasoning"] = item.get("impact_reasoning", "")
        else:
            article["sentiment"] = "neutral"
            article["score"] = 0.5
            article["reasoning"] = "Not analyzed"
            article["impact_horizon"] = "short-term"
            article["price_impact_estimate"] = "N/A"
            if has_positions:
                article["portfolio_impact"] = "unrelated"
                article["impact_reasoning"] = ""

    return results
