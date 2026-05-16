# IndecisiveFattie 🍔

Stop overthinking your next meal. Pick a city, describe what you're craving, and IndecisiveFattie uses OpenAI to find the best matching restaurant from a curated database of 7,000+ real restaurants across Los Angeles, Chicago, and New York City.

## Setup

1. Clone the repo and enter the directory:
   ```
   git clone <repo-url>
   cd final
   ```

2. Create a virtual environment and install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and add your OpenAI API key:
   ```
   cp .env.example .env
   ```
   Edit `.env` and fill in your OpenAI API key.

## Run

```
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser. (or whatever it says when you run the python app.py command in your terminal)

## Usage

1. Select your city (Los Angeles, Chicago, or New York City)
2. Describe what you're feeling (e.g. "something spicy and cheap" or "fresh sushi")
3. Click **Find my spot** — the app queries the local restaurant database and uses OpenAI to pick the best match for you

## Database

A pre-built `restaurants.db` is included with ~7,000 restaurants sourced from Yelp across all three cities. No additional API keys are needed to run the app.

To re-seed the database (requires a Yelp API key **FREE**):
```
YELP_API_KEY=your_key python seed.py
```

## Eval

```
python eval/eval.py
```

Runs 10 labeled test cases and reports the cuisine match rate. See `eval/test_cases.json` for the test cases.
