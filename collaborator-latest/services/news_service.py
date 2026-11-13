"""
Upgrade 1: Live News Service
Uses NewsAPI if key is present, otherwise falls back to stub.
"""
from dataclasses import dataclass, asdict
from datetime import datetime
import os, re, sys, requests as _req

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from services.cache_service import cache_get, cache_set

@dataclass
class NewsItem:
    headline: str
    source: str
    category: str
    region: str
    published_at: str
    severity_hint: str
    url: str = ""

def _stub_news():
    return [
        NewsItem("Port of Los Angeles workers threaten strike", "Logistics Weekly", "logistics", "us-west-coast", datetime.utcnow().isoformat(), "HIGH", ""),
        NewsItem("Suez canal partially blocked due to high winds", "Global News", "logistics", "middle-east", datetime.utcnow().isoformat(), "CRITICAL", ""),
        NewsItem("Category 4 hurricane forming in the Atlantic", "Weather Network", "weather", "us-east-coast", datetime.utcnow().isoformat(), "CRITICAL", ""),
        NewsItem("Ransomware attack targets major shipping firm", "CyberTech News", "cyber", "global", datetime.utcnow().isoformat(), "HIGH", ""),
        NewsItem("Tensions rise in South China Sea", "World Politics", "geopolitical", "east-asia", datetime.utcnow().isoformat(), "HIGH", ""),
        NewsItem("Microchip supplier halts production", "Tech Daily", "supplier", "east-asia", datetime.utcnow().isoformat(), "CRITICAL", ""),
        NewsItem("New tariffs imposed on EU imports", "Trade Times", "customs", "europe", datetime.utcnow().isoformat(), "MEDIUM", ""),
        NewsItem("Truck driver shortage worsens in UK", "Transport News", "logistics", "europe", datetime.utcnow().isoformat(), "MEDIUM", ""),
        NewsItem("Saudi Aramco pipeline disruption affects oil supply", "Energy Watch", "logistics", "middle-east", datetime.utcnow().isoformat(), "HIGH", ""),
        NewsItem("Flooding shuts major rail routes across Germany", "Deutsche Press", "weather", "europe", datetime.utcnow().isoformat(), "HIGH", ""),
    ]

def _fetch_live(query: str = "supply chain disruption", max_results: int = 10) -> list[NewsItem]:
    """Fetch from NewsAPI.org if key is available."""
    key = Config.NEWS_API_KEY
    if not key:
        return []
    cache_key = f"news_{query}_{max_results}"
    cached = cache_get(cache_key)
    if cached:
        return [NewsItem(**i) for i in cached]
    try:
        url = "https://newsapi.org/v2/everything"
        params = {"q": query, "apiKey": key, "pageSize": max_results, "language": "en", "sortBy": "publishedAt"}
        resp = _req.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            return []
        articles = resp.json().get("articles", [])
        items = []
        for a in articles:
            items.append(NewsItem(
                headline=a.get("title", "No title"),
                source=a.get("source", {}).get("name", "Unknown"),
                category="logistics",
                region="global",
                published_at=a.get("publishedAt", datetime.utcnow().isoformat()),
                severity_hint="MEDIUM",
                url=a.get("url", "")
            ))
        cache_set(cache_key, [asdict(i) for i in items])
        return items
    except Exception as e:
        print(f"[NewsAPI] Live fetch failed: {e}")
        return []

def fetch_headlines(query: str = "", max_results: int = 10) -> list[NewsItem]:
    live = _fetch_live(query or "supply chain", max_results)
    if live:
        return live
    stub = _stub_news()
    if query:
        terms = [t for t in re.split(r"[\s,-]+", query.lower()) if len(t) > 2]
        matched = [r for r in stub
                   if r.region == query.lower()
                   or any(t in r.headline.lower() or t in r.category for t in terms)]
        # A generic query ("supply chain disruption") should not filter out the whole feed
        stub = matched or stub
    return stub[:max_results]

def fetch_by_region(region: str) -> list[NewsItem]:
    all_items = fetch_headlines(max_results=20)
    if region == "global":
        return all_items[:10]
    return [r for r in all_items if r.region == region] or all_items[:5]

def fetch_by_category(category: str) -> list[NewsItem]:
    return [r for r in _stub_news() if r.category == category]