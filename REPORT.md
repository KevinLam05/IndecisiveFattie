# REPORT.md

## 1. What & Why

IndecisiveFattie is a restaurant recommendation web app for people who can't decide what to eat. The user picks a city (Los Angeles, Chicago, or New York City), describes what they're craving in plain English, and the app returns a single best-match restaurant along with a list of other relevant options.

The target user is anyone who has ever spent 20 minutes scrolling Yelp without making a decision — which is most people. The app removes that friction by making the decision for you.

What makes the AI behavior hard to get right is the gap between natural language preferences and structured restaurant data. A user might say "something spicy and cheap" or "I'm in the mood for comfort food" — neither of which maps cleanly to a cuisine category. The app has to interpret vague, subjective language and match it against a database of restaurants that are tagged with Yelp categories like "Thai", "Pizza", or "Korean, Barbeque". Getting that translation right — without being too narrow (missing good options) or too broad (returning irrelevant results) — is the core challenge.

A secondary challenge is that the pick has to feel justified. OpenAI doesn't just return a name; it returns a reason. That reason needs to actually connect the user's preference to the restaurant's attributes, not just be generic filler.

---

## 2. Iterations

### V1 — OpenStreetMap with basic filtering

**Change:** The initial version used the Overpass API (OpenStreetMap) to fetch nearby restaurants based on the inputted location/city, then passed them to OpenAI to filter and pick the best match.

**Motivating example:** Searching for "pizza" in New York City returned only 1 restaurant in the filtered list, even though the raw query returned 15 results. The other 14 were filtered out by OpenAI because their OSM cuisine tags didn't say "pizza."

**Eval Metric:** Cuisine match rate: 3/10 (30%). Most searches returned irrelevant results or fell back to a single match.

**Conclusion:** OSM cuisine tags are sparse and inconsistent — many pizza places are tagged as "italian" or have no cuisine tag at all. OpenAI's filtering was correct given the data, but the data itself was the problem. Switching to a richer data source was necessary.

---

### V2 — Yelp-backed SQLite database

**Change:** Replaced the live OSM call with a preset seed.py database using SQLite which sources up to 7000 restaurants using yelp api key

**Motivating example:** The same "pizza in NYC" search that returned 1 result in V1 now had 84 restaurants tagged with "Pizza" in the DB, giving OpenAI a much better pool to pick from.

**Eval Metric:** Cuisine match rate: 8/10 (80%). Significant improvement, but some vague preferences like "something spicy" still failed because the DB query used only the first word of the preference as a keyword.

**Conclusion:** Better data quality directly improved results. The remaining failures were caused by poor keyword extraction — "something" matched nothing in the cuisine column, triggering a random fallback.w

---

### V3 — OpenAI-powered cuisine extraction

**Change:** Added a lightweight OpenAI call before the DB query to extract a cuisine keyword from the user's free-text preference. For example, "something spicy and cheap" → "thai". The extracted keyword is then used to filter the DB, and the matched restaurants are sent to the main recommendation call.

**Motivating example:** "Something spicy and cheap" previously triggered the random fallback (first word "something" matched nothing), returning unrelated restaurants. After adding extraction, it correctly identified "thai" and returned Thai restaurants.

**Eval Metric:** Cuisine match rate: 10/10 (100%) on the labeled eval set.

**Conclusion:** The two-step approach — extract intent first, then retrieve — is more robust than trying to match raw preference text against structured data. The extraction step acts as a translation layer between natural language and database categories. A potential next step would be handling multi-cuisine preferences (e.g. "pizza or sushi") by extracting multiple keywords.

---
### Conclusion
There were a couple flaws within the v1 of the project since OpenStreetMap overpass api doesn't have access to things such as menus or to look through a specific dish, it was all based off of cuisines and the restaurant names which deemed to be inaccurate at times(more than half the time)

v2 is better but at the same time, we narrowed down the scope of restaurant and the range (search wise) in order to provide more accurate informations such as restaurants, cuisines, menus and drinks
## 3. Code Walkthrough

When a user enter a city/location onto the indicated box, as well as their craving then click "find my spot"

First, the JavaScript in `templates/index.html` grabs the selected city and the typed preference, then sends them to the server as a POST request to `/recommend`.

The server receives it in the `recommend()` function in `app.py` (line 128). It checks that both the city and preference were provided, then passes the preference to `extract_cuisine()` at `app.py` line 45. That function makes a quick OpenAI call asking "what cuisine is this person looking for?" — for "I want pizza" it comes back with `"pizza"`. The reason this is its own separate call instead of being part of the main prompt is to keep things clean: one call figures out what the user wants, and a separate call picks the best restaurant. Mixing both into one prompt made the results less consistent in earlier versions.

Next, `fetch_places()` at `app.py` line 63 takes that keyword and searches the local `restaurants.db` database for up to 20 restaurants in New York City where the cuisine column contains "pizza". It also counts how many total pizza places exist in the DB so the UI can show "84 pizza places found."

Finally, `ask_openai()` at `app.py` line 92 sends those 20 restaurants to OpenAI along with the original preference. OpenAI reads through the list and picks the single best match, writes a short reason why, and returns details for all 20 restaurants. The result is sent back to the browser, which shows the pick at the top and the full list below it.

---

## 4. AI Disclosure & Safety

I used Kiro (an AI coding assistant) throughout this project. It was helpful for scaffolding the Flask routes, writing the Overpass API query, and generating the seed script. Three specific moments where it failed:

1. *OSM cuisine filtering* — Kiro initially suggested making the OpenAI prompt less aggressive to fix the "only 1 pizza result" problem. This didn't work because the root cause was data quality, not the prompt. I had to diagnose this myself by running a direct SQL query on the DB to confirm only 3 pizza places existed in the OSM-sourced data.

2. *`priceOrder` undefined* — Kiro wrote the price sorting UI but never defined the `priceOrder` lookup object in JavaScript, causing a silent runtime error. I caught this by testing the sort buttons and noticing they didn't work.

3. *Fallback threshold* — Kiro set the cuisine fallback threshold at 5 (fall back to random if fewer than 5 matches), which caused the 3 pizza places in the early DB to be ignored entirely. I had to identify this by reading the code and tracing why pizza searches returned unrelated restaurants.

*Safety risks:* The main safety risk in this app is hallucination in the restaurant descriptions and ratings. OpenAI generates one-sentence descriptions and estimated ratings for each restaurant — these are not sourced from real reviews and could be inaccurate or misleading. A user acting on a fabricated "4.8 stars, best ramen in the city" description could have a bad experience. The mitigation chosen is to use Yelp's real ratings and price tiers from the DB as the primary data, and to label OpenAI-generated descriptions visually as summaries rather than verified reviews. A future mitigation would be to display the real Yelp rating from the DB directly on each card instead of relying on OpenAI's estimate.
