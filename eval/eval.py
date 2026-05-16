"""
Eval script for IndecisiveFattie.

Metric: cuisine match rate — does the picked restaurant's cuisine contain
at least one of the expected keywords?

Usage:
    python eval/eval.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import extract_cuisine, fetch_places, ask_openai

CASES_PATH = os.path.join(os.path.dirname(__file__), "test_cases.json")


def score(pick_cuisine: str, expected_keywords: list[str]) -> bool:
    cuisine_lower = (pick_cuisine or "").lower()
    return any(kw in cuisine_lower for kw in expected_keywords)


def run_eval():
    with open(CASES_PATH) as f:
        cases = json.load(f)

    passed = 0
    results = []

    for case in cases:
        city = case["city"]
        preference = case["preference"]
        expected = case["expected_cuisine_keywords"]

        cuisine_keyword = extract_cuisine(preference)
        places, _ = fetch_places(city, cuisine_keyword)
        result = ask_openai(places, preference, mode="food")

        pick = result.get("pick", "")
        # Find the picked restaurant's cuisine from the returned list
        pick_cuisine = ""
        for r in result.get("restaurants", []):
            if r.get("name") == pick:
                pick_cuisine = r.get("cuisine", "")
                break

        passed_case = score(pick_cuisine, expected)
        passed += passed_case

        results.append({
            "id": case["id"],
            "city": city,
            "preference": preference,
            "extracted_keyword": cuisine_keyword,
            "pick": pick,
            "pick_cuisine": pick_cuisine,
            "expected_keywords": expected,
            "pass": passed_case,
        })

        status = "✅ PASS" if passed_case else "❌ FAIL"
        print(f"[{status}] #{case['id']} {city} | \"{preference}\"")
        print(f"         Pick: {pick} ({pick_cuisine})")
        print(f"         Expected keywords: {expected}\n")

    total = len(cases)
    print(f"Result: {passed}/{total} passed ({100*passed//total}%)")
    return results


if __name__ == "__main__":
    run_eval()
