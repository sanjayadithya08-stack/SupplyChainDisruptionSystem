# Coordinate mapping for major supply chain hubs, countries and chokepoints.
HUB_COORDS = {
    # Ports / cities
    "Tokyo": {"lat": 35.6762, "lon": 139.6503},
    "Los Angeles": {"lat": 33.7405, "lon": -118.2775},
    "Long Beach": {"lat": 33.7542, "lon": -118.2165},
    "Shanghai": {"lat": 31.2304, "lon": 121.4737},
    "Shenzhen": {"lat": 22.5431, "lon": 114.0579},
    "Kaohsiung": {"lat": 22.6273, "lon": 120.3014},
    "Seattle": {"lat": 47.6062, "lon": -122.3321},
    "Rotterdam": {"lat": 51.9225, "lon": 4.4792},
    "Hamburg": {"lat": 53.5511, "lon": 9.9937},
    "New York": {"lat": 40.7128, "lon": -74.0060},
    "Veracruz": {"lat": 19.1738, "lon": -96.1342},
    "Houston": {"lat": 29.7604, "lon": -95.3698},
    "Manzanillo": {"lat": 19.0522, "lon": -104.3158},
    "Jakarta": {"lat": -6.2088, "lon": 106.8456},
    "Singapore": {"lat": 1.2903, "lon": 103.8519},
    "Sydney": {"lat": -33.8688, "lon": 151.2093},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777},
    "Busan": {"lat": 35.1796, "lon": 129.0756},
    "Vancouver": {"lat": 49.2827, "lon": -123.1207},
    "Cape Town": {"lat": -33.9249, "lon": 18.4241},
    "Frankfurt Airport": {"lat": 50.0379, "lon": 8.5622},
    "Chicago O'Hare": {"lat": 41.9742, "lon": -87.9073},
    # Countries (centroids)
    "Taiwan": {"lat": 23.6978, "lon": 120.9605},
    "South Korea": {"lat": 36.5, "lon": 127.8},
    "Japan": {"lat": 36.2, "lon": 138.25},
    "Germany": {"lat": 51.1657, "lon": 10.4515},
    "Czech Republic": {"lat": 49.8, "lon": 15.47},
    "Netherlands": {"lat": 52.13, "lon": 5.29},
    "China": {"lat": 35.8617, "lon": 104.1954},
    "Vietnam": {"lat": 14.06, "lon": 108.28},
    "Thailand": {"lat": 15.87, "lon": 100.99},
    "Indonesia": {"lat": -0.79, "lon": 113.92},
    "USA": {"lat": 37.0902, "lon": -95.7129},
    "Canada": {"lat": 56.13, "lon": -106.35},
    "Mexico": {"lat": 23.63, "lon": -102.55},
    "Peru": {"lat": -9.19, "lon": -75.02},
    "India": {"lat": 20.5937, "lon": 78.9629},
    "Brazil": {"lat": -14.2350, "lon": -51.9253},
    "France": {"lat": 46.2276, "lon": 2.2137},
    "UK": {"lat": 54.0, "lon": -2.0},
    "Yemen": {"lat": 15.55, "lon": 48.52},
    "South Africa": {"lat": -30.56, "lon": 22.94},
    "Egypt": {"lat": 26.82, "lon": 30.80},
}

# Chokepoints used to bend route arcs realistically
WAYPOINTS = {
    "Suez Canal": {"lat": 30.0, "lon": 32.55},
    "Red Sea": {"lat": 14.0, "lon": 42.5},
    "Cape of Good Hope": {"lat": -35.5, "lon": 19.0},
    "Bay of Bengal": {"lat": 8.0, "lon": 87.0},
    "Gulf of Mexico": {"lat": 24.5, "lon": -92.0},
}

CITY_REGION = {
    "Los Angeles": "us-west-coast", "Long Beach": "us-west-coast", "Seattle": "us-west-coast",
    "New York": "us-east-coast", "Houston": "north-america", "Chicago O'Hare": "north-america",
    "Vancouver": "north-america", "Rotterdam": "europe", "Hamburg": "europe",
    "Frankfurt Airport": "europe", "Sydney": "oceania", "Mumbai": "south-asia",
    "Singapore": "southeast-asia", "Jakarta": "southeast-asia", "Tokyo": "east-asia",
    "Shanghai": "east-asia", "Shenzhen": "east-asia", "Kaohsiung": "east-asia", "Busan": "east-asia",
    "Veracruz": "latin-america", "Manzanillo": "latin-america", "Cape Town": "global",
    "Dallas": "north-america", "Amsterdam": "europe", "London": "europe",
}


def get_coords(name):
    return HUB_COORDS.get(name) or WAYPOINTS.get(name) or {"lat": 0, "lon": 0}


def route_path(origin: str, destination: str, via: list) -> list:
    """Ordered [lat, lon] points for a route, passing through known chokepoints."""
    pts = [get_coords(origin)]
    order = ["Bay of Bengal", "Red Sea", "Suez Canal", "Cape of Good Hope", "Gulf of Mexico"]
    for wp in sorted([v.strip() for v in via if v.strip() in WAYPOINTS], key=order.index):
        pts.append(WAYPOINTS[wp])
    pts.append(get_coords(destination))
    return [[p["lat"], p["lon"]] for p in pts]
