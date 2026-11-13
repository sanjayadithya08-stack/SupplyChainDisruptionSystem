"""Regional supply-chain intelligence backed by NewsAPI.org.

If NewsAPI is unavailable or not configured, the bundled sample headlines are
kept available but the feed status explicitly identifies them as sample data.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import os
import sys
import threading
import requests as _req

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config
from services.cache_service import cache_get, cache_set
from utils.text_preprocessing import detect_disruption_type, estimate_affected_region


@dataclass
class NewsItem:
    headline: str
    source: str
    category: str
    region: str
    published_at: str
    severity_hint: str
    url: str = ""


_FEED_STATUS = {
    "provider": "NewsAPI.org",
    "mode": "not_checked",
    "configured": bool(Config.NEWS_API_KEY),
    "last_updated": None,
    "message": "The feed has not been refreshed yet.",
}
_FEED_LOCK = threading.RLock()

SAMPLE_NEWS = [
    NewsItem("Port of Los Angeles workers threaten strike", "Sample feed", "logistics", "us-west-coast", "", "HIGH", ""),
    NewsItem("Suez canal partially blocked due to high winds", "Sample feed", "logistics", "middle-east", "", "CRITICAL", ""),
    NewsItem("Category 4 hurricane forming in the Atlantic", "Sample feed", "weather", "us-east-coast", "", "CRITICAL", ""),
    NewsItem("Ransomware attack targets major shipping firm", "Sample feed", "cyber", "global", "", "HIGH", ""),
    NewsItem("Tensions rise in South China Sea", "Sample feed", "geopolitical", "east-asia", "", "HIGH", ""),
    NewsItem("Microchip supplier halts production", "Sample feed", "supplier", "east-asia", "", "CRITICAL", ""),
    NewsItem("New tariffs imposed on EU imports", "Sample feed", "customs", "europe", "", "MEDIUM", ""),
    NewsItem("Truck driver shortage worsens in UK", "Sample feed", "logistics", "europe", "", "MEDIUM", ""),
    NewsItem("Saudi Aramco pipeline disruption affects oil supply", "Sample feed", "logistics", "middle-east", "", "HIGH", ""),
    NewsItem("Flooding shuts major rail routes across Germany", "Sample feed", "weather", "europe", "", "HIGH", ""),
]

REGION_QUERY = {
    "global": "",
    "east-asia": '("East Asia" OR China OR Japan OR Korea OR Taiwan OR "South China Sea")',
    "europe": '(Europe OR European OR Germany OR France OR "United Kingdom" OR UK)',
    "north-america": '("North America" OR US OR USA OR Canada OR Mexico)',
    "southeast-asia": '("Southeast Asia" OR Vietnam OR Indonesia OR Singapore OR Thailand OR Malaysia)',
    "middle-east": '("Middle East" OR Suez OR Red Sea OR Gulf OR Yemen OR Iran OR Israel)',
    "south-asia": '("South Asia" OR India OR Pakistan OR Bangladesh OR Sri Lanka)',
}
BASE_QUERY = '("supply chain" OR shipping OR freight OR port OR logistics) AND (disruption OR delay OR strike OR closure OR shortage OR attack OR tariff OR congestion OR blockade)'
TOPIC_TERMS = (
    "supply chain", "shipping", "freight", "port", "logistics", "cargo", "vessel", "rail", "truck",
    "carrier", "supplier", "manufactur", "customs", "tariff", "trade", "semiconductor", "chip",
    "canal", "chokepoint", "warehouse", "container", "dockworker", "export", "import",
)
EVENT_TERMS = (
    "disrupt", "strike", "delay", "closure", "block", "shortage", "congestion", "outage", "fire",
    "conflict", "tariff", "sanction", "attack", "cyber", "flood", "hurricane", "earthquake", "halt",
    "shutdown", "suspend", "threat", "crisis", "risk", "surge", "dispute", "bottleneck", "disruption",
)


def _infer_severity(headline: str, category: str) -> str:
    h = headline.casefold()
    if any(w in h for w in ("strike", "blocked", "blockade", "hurricane", "typhoon", "earthquake", "fire", "war", "explosion", "ransomware", "closure", "halt", "shut down", "critical", "attack")):
        return "CRITICAL"
    if any(w in h for w in ("delay", "shortage", "tensions", "restriction", "disrupt", "warning", "congestion", "hazard", "tariff", "protest")):
        return "HIGH"
    return "MEDIUM"


def _set_status(mode: str, message: str, updated: str | None = None):
    _FEED_STATUS.update({
        "mode": mode,
        "configured": bool(Config.NEWS_API_KEY),
        "last_updated": updated or datetime.now(timezone.utc).isoformat(),
        "message": message,
    })


def get_feed_status() -> dict:
    return dict(_FEED_STATUS)


def _fetch_live_locked(query: str = BASE_QUERY, max_results: int = 10) -> list[NewsItem]:
    """Fetch fresh English headlines from NewsAPI, or use a short-lived cache."""
    if not Config.NEWS_API_KEY:
        _set_status("sample", "NEWS_API_KEY is not configured; showing clearly labelled sample headlines.")
        return []

    cache_key = f"newsapi_v2_{query}_{max_results}"
    cached = cache_get(cache_key)
    if cached:
        _set_status("live", "Live headlines from NewsAPI.org (cached for up to five minutes).", cached[0].get("_fetched_at"))
        return [NewsItem(**{k: v for k, v in item.items() if not k.startswith("_")}) for item in cached]

    try:
        response = _req.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "apiKey": Config.NEWS_API_KEY,
                # NewsAPI searches article bodies as well as titles. Fetch a
                # wider recent page, then keep only relevant operational hits.
                "pageSize": 100,
                "language": "en",
                "sortBy": "publishedAt",
            },
            timeout=12,
        )
        payload = response.json()
        if response.status_code != 200 or payload.get("status") != "ok":
            reason = payload.get("message") or f"NewsAPI returned HTTP {response.status_code}."
            _set_status("sample", f"NewsAPI unavailable ({reason}); showing clearly labelled sample headlines.")
            return []

        now = datetime.now(timezone.utc).isoformat()
        items = []
        for article in payload.get("articles", []):
            title = (article.get("title") or "").strip()
            if not title or title == "[Removed]":
                continue
            title_search = title.casefold()
            searchable = f"{title} {article.get('description') or ''}".casefold()
            # NewsAPI searches full article text; keep the dashboard focused on
            # supply-chain topics and actual operational events.
            if not any(term in title_search for term in TOPIC_TERMS):
                continue
            if not any(term in searchable for term in EVENT_TERMS):
                continue
            category = detect_disruption_type(title)
            inferred_regions = estimate_affected_region(title)
            inferred_region = inferred_regions[0] if isinstance(inferred_regions, list) and inferred_regions else "global"
            items.append(NewsItem(
                headline=title,
                source=(article.get("source") or {}).get("name") or "NewsAPI source",
                category=category,
                region=inferred_region,
                published_at=article.get("publishedAt") or now,
                severity_hint=_infer_severity(title, category),
                url=article.get("url") or "",
            ))
            if len(items) >= max_results:
                break
        serializable = [{**asdict(item), "_fetched_at": now} for item in items]
        if serializable:
            cache_set(cache_key, serializable, ttl_seconds=300)
        _set_status("live", f"{len(items)} current headlines retrieved from NewsAPI.org.", now)
        return items
    except Exception as exc:
        # Keep logs useful without logging request URLs (which contain the key).
        _set_status("sample", f"NewsAPI request failed ({type(exc).__name__}); showing clearly labelled sample headlines.")
        print(f"[NewsAPI] Live fetch failed: {type(exc).__name__} (request details omitted).")
        return []


def _fetch_live(query: str = BASE_QUERY, max_results: int = 10) -> list[NewsItem]:
    with _FEED_LOCK:
        return _fetch_live_locked(query, max_results)


def _sample_for_region(region: str, max_results: int = 10) -> list[NewsItem]:
    if region == "global":
        return SAMPLE_NEWS[:max_results]
    matched = [item for item in SAMPLE_NEWS if item.region == region or item.region == "global"]
    return (matched or SAMPLE_NEWS)[:max_results]


def fetch_headlines(query: str = "", max_results: int = 10) -> list[NewsItem]:
    live = _fetch_live(query or BASE_QUERY, max_results)
    if live:
        return live
    if not Config.NEWS_API_KEY:
        return SAMPLE_NEWS[:max_results]
    # Keep sample entries out of the result if the live API succeeded but found
    # no matching articles. That is distinct from a failed/unconfigured feed.
    if _FEED_STATUS["mode"] == "live":
        return []
    return SAMPLE_NEWS[:max_results]


def fetch_by_region(region: str) -> list[NewsItem]:
    region = region if region in REGION_QUERY else "global"
    region_terms = REGION_QUERY[region]
    query = f"{BASE_QUERY} AND {region_terms}" if region_terms else BASE_QUERY
    live = _fetch_live(query, 20)
    if live:
        return live
    if _FEED_STATUS["mode"] == "live":
        return []
    return _sample_for_region(region, 10)


def fetch_by_region_with_status(region: str) -> tuple[list[NewsItem], dict]:
    # Return a matched snapshot so background scans cannot pair one request's
    # headlines with another concurrent request's status.
    with _FEED_LOCK:
        items = fetch_by_region(region)
        return items, get_feed_status()


def fetch_by_category(category: str) -> list[NewsItem]:
    all_items = fetch_headlines(max_results=20)
    return [item for item in all_items if item.category.casefold() == category.casefold()]
