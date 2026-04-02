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

Rules:
- "positive" means the news is likely bullish for relevant assets or the economy
- "negative" means the news is likely bearish for relevant assets or the economy
- "neutral" means unclear market impact or purely factual reporting
- Base reasoning on the financial implications, not general tone"""


def analyze_sentiment(articles: list[dict]) -> list[dict]:
    """
    Send all articles to OpenAI in a single batch call and return
    articles with sentiment fields (sentiment, score, reasoning) added.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in environment.")

    if not articles:
        return articles

    client = OpenAI(api_key=api_key)
    prompt = _build_prompt(articles)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=6000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )

    raw_text = response.choices[0].message.content
    return _parse_response(raw_text, articles)


def _build_prompt(articles: list[dict]) -> str:
    lines = [f"Analyze the sentiment of these {len(articles)} financial news articles:\n"]
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


def _parse_response(raw_json: str, articles: list[dict]) -> list[dict]:
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
        return results

    for i, article in enumerate(results):
        item = sentiment_map.get(i)
        if item:
            article["sentiment"] = item.get("sentiment", "neutral")
            article["score"] = float(item.get("score", 0.5))
            article["reasoning"] = item.get("reasoning", "")
        else:
            article["sentiment"] = "neutral"
            article["score"] = 0.5
            article["reasoning"] = "Not analyzed"

    return results
