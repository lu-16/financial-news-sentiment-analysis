import random
import urllib.parse
from datetime import datetime, timezone, timedelta

import feedparser


def fetch_articles(keywords: list[str], hours_back: int = 2) -> list[dict]:
    """
    Fetch articles from Google News RSS matching any of the given keywords
    published within the last `hours_back` hours.

    Returns a list of article dicts with keys:
        title, source, url, description, published_at
    """
    # `when:Xh` tells Google News to limit results to the last X hours
    query = " OR ".join(keywords) + f" when:{hours_back}h"
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    articles = []

    for entry in feed.entries:
        # feedparser gives published_parsed as a time.struct_time in UTC
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if pub_dt < cutoff:
                continue
        else:
            continue

        # Google News RSS source is in entry.source.title
        source = ""
        if hasattr(entry, "source") and hasattr(entry.source, "title"):
            source = entry.source.title

        articles.append({
            "title": entry.get("title", ""),
            "source": source or "Unknown",
            "url": entry.get("link", ""),
            "description": entry.get("summary", "")[:300],
            "published_at": entry.get("published", ""),
        })

    if len(articles) > 10:
        articles = random.sample(articles, 10)

    return articles
