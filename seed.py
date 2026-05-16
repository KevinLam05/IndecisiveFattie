"""
Seed script: fetches restaurants from Yelp Fusion API for LA, Chicago, and NYC
and stores them in restaurants.db (SQLite).

Usage:
    python seed.py
"""

import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()

YELP_API_KEY = os.getenv("YELP_API_KEY")
YELP_SEARCH_URL = "https://api.yelp.com/v3/businesses/search"

CITIES = [
    {"name": "Los Angeles",   "location": "Los Angeles, CA"},
    {"name": "Chicago",       "location": "Chicago, IL"},
    {"name": "New York City", "location": "New York, NY"},
]

# Multiple search terms to maximize coverage and cuisine variety
SEARCH_TERMS = [
    "restaurants",
    "pizza",
    "italian",
    "chinese",
    "mexican",
    "japanese",
    "sushi",
    "burgers",
    "thai",
    "indian",
    "korean",
    "seafood",
    "bbq",
    "vegan",
    "breakfast",
]

LIMIT = 50


def fetch(location: str, term: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {YELP_API_KEY}"}
    places = {}
    for offset in range(0, 200, 50):  # max 200 per term
        params = {
            "location": location,
            "term": term,
            "limit": LIMIT,
            "offset": offset,
        }
        resp = requests.get(YELP_SEARCH_URL, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            break
        businesses = resp.json().get("businesses", [])
        if not businesses:
            break
        for b in businesses:
            places[b["id"]] = b  # deduplicate by Yelp ID
    return list(places.values())


def seed():
    conn = sqlite3.connect("restaurants.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS restaurants (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            city        TEXT NOT NULL,
            cuisine     TEXT,
            rating      REAL,
            price       TEXT,
            address     TEXT,
            latitude    REAL,
            longitude   REAL
        )
    """)
    conn.execute("DELETE FROM restaurants")

    for city in CITIES:
        print(f"Fetching {city['name']}...")
        all_places = {}
        for term in SEARCH_TERMS:
            results = fetch(city["location"], term)
            for b in results:
                all_places[b["id"]] = b
            print(f"  [{term}] +{len(results)} → {len(all_places)} unique so far")

        rows = []
        for b in all_places.values():
            cuisine = ", ".join(c["title"] for c in b.get("categories", []))
            coords = b.get("coordinates", {})
            rows.append((
                b["id"],
                b["name"],
                city["name"],
                cuisine or None,
                b.get("rating"),
                b.get("price"),
                ", ".join(b.get("location", {}).get("display_address", [])) or None,
                coords.get("latitude"),
                coords.get("longitude"),
            ))
        conn.executemany(
            "INSERT OR REPLACE INTO restaurants VALUES (?,?,?,?,?,?,?,?,?)", rows
        )
        conn.commit()
        print(f"  → Inserted {len(rows)} total for {city['name']}\n")

    conn.close()
    print("Done. restaurants.db is ready.")


if __name__ == "__main__":
    if not YELP_API_KEY:
        raise SystemExit("Error: YELP_API_KEY not set in environment or .env")
    seed()
