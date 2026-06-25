import os
import json
import logging
import time
from typing import Dict, Any

import requests
from dotenv import load_dotenv

from database import supabase
from constants import VALID_CATEGORIES, VALID_RISKS, VALID_SENTIMENTS

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Fixed model for consistent results
MODEL = "google/gemini-2.5-flash"

MAX_RETRIES = 3

REQUEST_TIMEOUT = 60

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
SYSTEM_PROMPT = """
You are SentiWatch AI.

You are an expert Brand Reputation Intelligence Analyst specializing in African businesses.

Your job is NOT sentiment analysis.

Your job is Reputation Risk Analysis.

Analyse the reputational impact of the text.

Return ONLY valid JSON.

Never explain.

Never wrap JSON in markdown.

Schema:

{
    "sentiment":"positive|neutral|negative",
    "severity":1-10,
    "confidence":0.0-1.0,
    "category":"fraud|legal|regulatory|customer_service|product_quality|operations|cyber|security|financial|leadership|general",
    "risk":"low|medium|high|critical",
    "reason":"One short sentence explaining the decision."
}

Rules

Positive

Customer praise

Awards

CSR

Growth

Investment

Partnerships

Product success

Satisfied customers

Neutral

Opening hours

Office relocation

Job adverts

Holiday announcements

Educational content

General industry news

Negative

Fraud

EFCC

Police

Court

Corruption

Data breach

Hack

Poor service

Mass complaints

Product recalls

Customer refunds

Regulatory fines

Operational failures

Scam allegations

Business closure

Mass layoffs

Negative viral content

Negative reviews

If objective news reports damage trust,
classify as negative.

If uncertain between neutral and negative,
prefer negative.

If uncertain between positive and neutral,
prefer neutral.

Return JSON only.
"""
def call_openrouter(text: str) -> Dict[str, Any]:

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": text
            }
        ],
        "temperature": 0,
        "response_format": {
            "type": "json_object"
        }
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            body = response.json()

            content = body["choices"][0]["message"]["content"]

            return json.loads(content)

        except Exception as e:

            logging.warning(
                f"OpenRouter attempt {attempt+1} failed: {e}"
            )

            time.sleep(2)

    raise Exception("OpenRouter failed after retries.")
    def call_openrouter(text: str) -> Dict[str, Any]:

     payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": text
            }
        ],
        "temperature": 0,
        "response_format": {
            "type": "json_object"
        }
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            body = response.json()

            content = body["choices"][0]["message"]["content"]

            return json.loads(content)

        except Exception as e:

            logging.warning(
                f"OpenRouter attempt {attempt+1} failed: {e}"
            )

            time.sleep(2)

    raise Exception("OpenRouter failed after retries.")
def get_unprocessed_mentions(limit: int = 10):

    """
    Returns mentions that have not yet been analysed.
    """

    mentions = (
        supabase.table("mentions")
        .select("*")
        .order("created_at", desc=False)
        .limit(100)
        .execute()
    ).data

    sentiment_rows = (
        supabase.table("sentiment_results")
        .select("mention_id")
        .execute()
    ).data

    analysed_ids = {
        row["mention_id"]
        for row in sentiment_rows
    }

    unprocessed = [
        mention
        for mention in mentions
        if mention["id"] not in analysed_ids
    ]

    return unprocessed[:limit]


def save_sentiment(mention_id, result):

    """
    Save AI analysis into sentiment_results table.
    """

    payload = {

        "mention_id": mention_id,

        "label": result["sentiment"],

        "confidence": result["confidence"],

        "severity": result["severity"],

        "category": result["category"],

        "risk_level": result["risk"],

        "reason": result["reason"]

    }

    (
        supabase
        .table("sentiment_results")
        .insert(payload)
        .execute()
    )


def analyze_and_store_sentiment():

    """
    Analyse new mentions using OpenRouter.

    Returns statistics.
    """

    if not OPENROUTER_API_KEY:

        logging.error("Missing OPENROUTER_API_KEY")

        return {

            "processed": 0,

            "failed": 0

        }

    mentions = get_unprocessed_mentions()

    if not mentions:

        logging.info("No new mentions.")

        return {

            "processed": 0,

            "failed": 0

        }

    processed = 0

    failed = 0

    logging.info(

        f"Found {len(mentions)} new mentions."

    )

    for mention in mentions:

        mention_id = mention["id"]

        text = mention.get("content", "")

        if not text.strip():

            logging.warning(

                f"Mention {mention_id} has no content."

            )

            failed += 1

            continue

        try:

            ai_result = call_openrouter(text)

            ai_result = validate_ai_output(ai_result)

            save_sentiment(

                mention_id,

                ai_result

            )

            logging.info(

                f"Mention {mention_id} analysed."

            )

            processed += 1

        except Exception as e:

            logging.exception(

                f"Failed analysing mention {mention_id}: {e}"

            )

            failed += 1

    logging.info(

        f"Finished. Processed={processed}, Failed={failed}"

    )

    return {

        "processed": processed,

        "failed": failed

    }


if __name__ == "__main__":

    stats = analyze_and_store_sentiment()

    print(stats)