import os
import json
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB_PATH = os.path.join(os.path.dirname(__file__), "restaurants.db")

# Map common user input to DB city names
CITY_ALIASES = {
    "los angeles": "Los Angeles",
    "la":          "Los Angeles",
    "chicago":     "Chicago",
    "nyc":         "New York City",
    "new york":    "New York City",
    "new york city": "New York City",
    "ny":          "New York City",
}


def resolve_city(location: str) -> str | None:
    return CITY_ALIASES.get(location.lower().strip())


def geocode(location: str) -> tuple[float, float] | None:
    resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": location, "format": "json", "limit": 1},
        headers={"User-Agent": "IndecisiveFattie/1.0"},
        timeout=10,
    )
    results = resp.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


def extract_cuisine(preferences: str) -> str:
    """Use OpenAI to extract a cuisine keyword from free-text preferences."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": (
                "Extract the single most relevant cuisine or food type keyword from the user's preference. "
                "Return only the keyword (e.g. 'pizza', 'tacos', 'sushi', 'burgers', 'thai'). "
                "If no specific cuisine is mentioned, return 'restaurant'."
            )},
            {"role": "user", "content": preferences},
        ],
        max_tokens=10,
        temperature=0,
    )
    return response.choices[0].message.content.strip().lower()


def fetch_places(city: str, cuisine_keyword: str = "") -> tuple[list[dict], int]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = []
    total = 0
    if cuisine_keyword and cuisine_keyword != "restaurant":
        rows = conn.execute(
            "SELECT * FROM restaurants WHERE city = ? AND LOWER(cuisine) LIKE ? ORDER BY RANDOM() LIMIT 20",
            (city, f"%{cuisine_keyword}%")
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM restaurants WHERE city = ? AND LOWER(cuisine) LIKE ?",
            (city, f"%{cuisine_keyword}%")
        ).fetchone()[0]

    if not rows:
        rows = conn.execute(
            "SELECT * FROM restaurants WHERE city = ? ORDER BY RANDOM() LIMIT 20",
            (city,)
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM restaurants WHERE city = ?", (city,)
        ).fetchone()[0]

    conn.close()
    return [dict(r) for r in rows], total


def ask_openai(places: list[dict], preferences: str, mode: str) -> dict:
    place_list = "\n".join(
        f"{i+1}. {r['name']} (cuisine: {r['cuisine'] or 'unknown'}, "
        f"rating: {r['rating']}, price: {r['price'] or 'unknown'})"
        for i, r in enumerate(places)
    )

    kind = "coffee shop, tea bar, or drink spot" if mode == "drinks" else "restaurant"
    system_prompt = (
        f"You are IndecisiveFattie, a friendly and opinionated food and drink assistant. "
        f"Given a list of nearby {kind}s and the user's preferences, pick the single best match.\n"
        "Return a JSON object with:\n"
        "- \"pick\": the name of the single best match\n"
        "- \"reason\": 2-3 sentences explaining why it fits the user's preferences\n"
        "- \"restaurants\": array of ALL places from the list, each with:\n"
        "  - \"name\", \"cuisine\", \"affordability\" ($/$$/$$$/$$$$), \"rating\" (out of 5), \"description\" (one sentence)\n"
        "Return only valid JSON, no markdown."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Nearby places:\n{place_list}\n\nUser preferences: {preferences}"},
        ],
        max_tokens=2500,
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json()
    location = (data.get("location") or "").strip()
    preferences = (data.get("preferences") or "").strip()
    mode = data.get("mode", "food")

    if not location:
        return jsonify({"error": "Please enter a location."}), 400
    if not preferences:
        return jsonify({"error": "Please enter your preferences."}), 400

    city = resolve_city(location)
    if not city:
        return jsonify({"error": "Only Los Angeles, Chicago, and New York City are supported."}), 400

    cuisine_keyword = extract_cuisine(preferences)
    places, total_count = fetch_places(city, cuisine_keyword)
    if not places:
        return jsonify({"error": f"No restaurants found for {city}."}), 404

    # Geocode for map display
    coords = geocode(location)
    lat, lon = coords if coords else (None, None)

    result = ask_openai(places, preferences, mode)
    return jsonify({
        "pick": result.get("pick"),
        "reason": result.get("reason"),
        "restaurants": result.get("restaurants", []),
        "restaurant_count": total_count,
        "location": location,
        "lat": lat,
        "lon": lon,
    })


if __name__ == "__main__":
    app.run(debug=True)
