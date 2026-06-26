import os
import json
import logging
import time
from typing import Dict, Any

from groq import Groq
from dotenv import load_dotenv

from database import supabase
from constants import VALID_CATEGORIES, VALID_RISKS, VALID_SENTIMENTS

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

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


# -----------------------------------------------------
# Validate and sanitise AI output
# FIX: This function was called but never defined,
# causing a NameError that silently failed every
# mention — root cause of the neutral-only bug.
# -----------------------------------------------------

def validate_ai_output(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensures all AI output fields are present, correctly typed,
    and within allowed values. Falls back to safe defaults
    rather than crashing the pipeline.
    """

    # Sentiment
    sentiment = str(result.get("sentiment", "neutral")).lower().strip()
    result["sentiment"] = sentiment if sentiment in VALID_SENTIMENTS else "neutral"

    # Risk
    risk = str(result.get("risk", "low")).lower().strip()
    result["risk"] = risk if risk in VALID_RISKS else "low"

    # Category
    category = str(result.get("category", "general")).lower().strip()
    result["category"] = category if category in VALID_CATEGORIES else "general"

    # Severity — clamp to 1–10
    try:
        severity = int(result.get("severity", 5))
    except (ValueError, TypeError):
        severity = 5
    result["severity"] = max(1, min(10, severity))

    # Confidence — clamp to 0.0–1.0
    try:
        confidence = float(result.get("confidence", 0.75))
    except (ValueError, TypeError):
        confidence = 0.75
    result["confidence"] = max(0.0, min(1.0, confidence))

    # Reason — always a string
    result["reason"] = str(result.get("reason", "")).strip()

    return result


# -----------------------------------------------------
# OpenRouter API call
# FIX: Removed the duplicate definition of this function
# that was previously nested inside the raise statement,
# making it unreachable dead code.
# -----------------------------------------------------

def call_groq(text: str) -> Dict[str, Any]:

    client = Groq(api_key=GROQ_API_KEY)

    for attempt in range(MAX_RETRIES):

        try:

            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content

            return json.loads(content)

        except Exception as e:

            logging.warning(
                f"Groq attempt {attempt + 1} failed: {e}"
            )

            time.sleep(2)

    raise Exception("Groq failed after retries.")

# -----------------------------------------------------
# Fetch unprocessed mentions
# FIX: The original fetched a hard limit of 100 rows
# BEFORE filtering, meaning if 90+ were already
# processed, new mentions would be silently skipped.
# Now paginates properly using range() until exhausted.
# -----------------------------------------------------

def get_unprocessed_mentions(limit: int = 10):
    """
    Returns mentions that have not yet been analysed.
    Paginates through all mentions to avoid the silent
    skip bug where processed mentions filled the page.
    """

    BATCH = 200
    offset = 0
    unprocessed = []

    # Fetch all already-analysed mention IDs upfront
    sentiment_rows = (
        supabase.table("sentiment_results")
        .select("mention_id")
        .execute()
    ).data

    analysed_ids = {row["mention_id"] for row in sentiment_rows}

    # Page through mentions until we have enough unprocessed ones
    while len(unprocessed) < limit:

        batch = (
            supabase.table("mentions")
            .select("*")
            .order("created_at", desc=False)
            .range(offset, offset + BATCH - 1)
            .execute()
        ).data

        if not batch:
            break

        for mention in batch:
            if mention["id"] not in analysed_ids:
                unprocessed.append(mention)
                if len(unprocessed) >= limit:
                    break

        if len(batch) < BATCH:
            # Reached the end of the table
            break

        offset += BATCH

    return unprocessed


# -----------------------------------------------------
# Save sentiment result
# -----------------------------------------------------

def save_sentiment(mention_id: str, result: Dict[str, Any]):
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


# -----------------------------------------------------
# Main analysis pipeline
# -----------------------------------------------------

def analyze_and_store_sentiment():
    """
    Analyse new mentions using OpenRouter.
    Returns statistics dict with processed/failed counts.
    """

    if not GROQ_API_KEY:
        logging.error("Missing GROQ_API_KEY")
        return {"processed": 0, "failed": 0}

    mentions = get_unprocessed_mentions()

    if not mentions:
        logging.info("No new mentions to process.")
        return {"processed": 0, "failed": 0}

    processed = 0
    failed = 0

    logging.info(f"Found {len(mentions)} new mentions to analyse.")

    for mention in mentions:

        mention_id = mention["id"]
        text = mention.get("content", "")

        if not text.strip():
            logging.warning(f"Mention {mention_id} has no content. Skipping.")
            failed += 1
            continue

        try:

            ai_result = call_groq(text)

            # FIX: validate_ai_output now exists and runs correctly
            ai_result = validate_ai_output(ai_result)

            save_sentiment(mention_id, ai_result)

            logging.info(
                f"Mention {mention_id} → "
                f"sentiment={ai_result['sentiment']} | "
                f"risk={ai_result['risk']} | "
                f"severity={ai_result['severity']}"
            )

            processed += 1

        except Exception as e:

            logging.exception(f"Failed analysing mention {mention_id}: {e}")
            failed += 1

    logging.info(f"Done. Processed={processed}, Failed={failed}")

    return {"processed": processed, "failed": failed}


if __name__ == "__main__":
    stats = analyze_and_store_sentiment()
    print(stats)
