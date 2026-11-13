import re
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import Config

def clean_text(text: str) -> str:
    """Lowercase, strip URLs, punctuation, stopwords. Never crashes."""
    try:
        if not isinstance(text, str):
            text = str(text)
            
        text = text.lower()
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        text = re.sub(r'[^\w\s]', '', text)
        text = " ".join(text.split())
        return text
    except Exception as e:
        print(f"Error in clean_text: {e}")
        return ""

def combine_inputs(news: str, weather: str, geo: str) -> str:
    try:
        n = clean_text(news)
        w = clean_text(weather)
        g = clean_text(geo)
        return f"[NEWS] {n} [WEATHER] {w} [GEO] {g}"
    except Exception as e:
        print(f"Error in combine_inputs: {e}")
        return "[ERROR_COMBINING_INPUTS]"

def extract_keywords(text: str, top_n: int = 5) -> list:
    try:
        cleaned = clean_text(text)
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are"}
        words = [w for w in cleaned.split() if w not in stopwords and len(w) > 2]
        
        counts = {}
        for w in words:
            counts[w] = counts.get(w, 0) + 1
            
        sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:top_n]]
    except Exception as e:
        return ["UNKNOWN"]

def detect_disruption_type(text: str) -> str:
    """Rule-based classifier: returns one of the Config.DISRUPTION_TYPES."""
    try:
        t = text.lower()
        
        if any(w in t for w in ["strike", "union", "walkout", "labor"]):
            return "port_strike"
        if any(w in t for w in ["hurricane", "typhoon", "flood", "weather", "storm", "cyclone", "snow", "tornado", "wildfire"]):
            return "weather"
        if any(w in t for w in ["war", "conflict", "rebel", "attack", "tension", "military", "piracy"]):
            # attack could be cyber, check context
            if "cyber" not in t and "ransomware" not in t and "ddos" not in t and "hacker" not in t:
                return "war"
        if any(w in t for w in ["cyber", "ransomware", "hack", "ddos", "it glitch", "data breach"]):
            return "cyber"
        if any(w in t for w in ["customs", "border", "tariff", "regulation", "clearance"]):
            return "customs"
        if any(w in t for w in ["supplier", "factory", "bankruptcy", "production", "materials"]):
            return "supplier"
        if any(w in t for w in ["shortage", "congestion", "delay", "truck", "rail", "freight", "logistics", "vessel", "canal", "outage"]):
            return "logistics"
            
        return "normal"
    except Exception as e:
        return "normal"

def estimate_affected_region(text: str) -> list:
    """Scan for known region/country keywords, return list."""
    try:
        t = text.lower()
        found_regions = set()
        
        region_map = {
            "us-west-coast": ["los angeles", "california", "west coast", "long beach", "seattle"],
            "us-east-coast": ["florida", "east coast", "new york", "jfk", "savannah"],
            "north-america": ["usa", "us", "canada", "chicago", "texas", "midwest", "mexico"],
            "latin-america": ["panama", "brazil", "south america", "latin america"],
            "europe": ["europe", "eu", "uk", "germany", "france", "rotterdam", "italy"],
            "middle-east": ["middle east", "suez", "red sea", "yemen", "houthi"],
            "south-asia": ["india", "bangladesh", "south asia"],
            "southeast-asia": ["singapore", "vietnam", "tuas", "southeast asia"],
            "east-asia": ["china", "taiwan", "shanghai", "shenzhen", "east asia"],
            "oceania": ["australia", "melbourne", "oceania"],
            "global": ["global", "world"]
        }
        
        for region, keywords in region_map.items():
            for kw in keywords:
                if kw in t:
                    found_regions.add(region)
                    
        if not found_regions:
            found_regions.add("global")
            
        return list(found_regions)
    except Exception as e:
        return ["global"]