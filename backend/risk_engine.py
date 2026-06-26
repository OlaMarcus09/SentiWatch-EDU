import os

import resend

from dotenv import load_dotenv

from database import supabase

from scoring import calculate_entity_score

from constants import EMAIL_ALERT_THRESHOLD

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")


# -----------------------------------------------------
# Get entity
# -----------------------------------------------------

def get_entity(entity_id: str):
    """
    Fetch a single monitored entity by ID.
    """

    result = (
        supabase
        .table("monitored_entities")
        .select("*")
        .eq("id", entity_id)
        .single()
        .execute()
    )

    return result.data


# -----------------------------------------------------
# Fetch mentions
# FIX: This function was previously indented inside
# get_entity(), making it a local function that was
# never callable from outside. Now correctly at
# module level.
# -----------------------------------------------------

def fetch_mentions(entity_id: str):
    """
    Fetch all mentions for an entity and join them
    with their sentiment results.
    Returns a flat list ready for calculate_entity_score().
    """

    mentions = (
        supabase
        .table("mentions")
        .select("*")
        .eq("entity_id", entity_id)
        .execute()
    ).data

    if not mentions:
        return []

    mention_lookup = {m["id"]: m for m in mentions}

    sentiment_rows = (
        supabase
        .table("sentiment_results")
        .select("*")
        .in_("mention_id", list(mention_lookup.keys()))
        .execute()
    ).data

    merged = []

    for row in sentiment_rows:

        mention = mention_lookup.get(row["mention_id"])

        if not mention:
            continue

        merged.append({
            "label": row["label"],
            "severity": row["severity"],
            "confidence": row["confidence"],
            "category": row["category"],
            "risk_level": row["risk_level"],
            # FIX: normalise source string to match SOURCE_WEIGHTS keys
            # Scrapers saved "Google Maps", "Nigerian News Feed",
            # "Public Forums (X/Reddit)" — none of which matched
            # the lowercase underscore keys in constants.py,
            # so every mention fell through to weight 1.0 ("other").
            "source": _normalise_source(mention.get("source", "other")),
            "created_at": mention.get("created_at")
        })

    return merged


def _normalise_source(raw: str) -> str:
    """
    Maps the human-readable source strings saved by scrapers.py
    to the lowercase keys defined in SOURCE_WEIGHTS.
    Add new mappings here as new scrapers are added.
    """

    mapping = {
        "google maps": "google_maps",
        "google reviews": "google_reviews",
        "nigerian news feed": "nigerian_news",
        "public forums (x/reddit)": "reddit",
        "twitter": "twitter",
        "facebook": "facebook",
        "linkedin": "linkedin",
        "nairaland": "nairaland",
        "vanguard": "vanguard",
        "guardian": "guardian",
        "thecable": "thecable",
        "punch": "punch",
        "premium times": "premium_times",
        "blog": "blog",
    }

    return mapping.get(raw.strip().lower(), "other")


# -----------------------------------------------------
# Save risk score
# -----------------------------------------------------

def save_risk_score(entity_id: str, score: dict):
    """
    Upsert the risk score for an entity.
    Updates if a record exists, inserts if not.
    """

    existing = (
        supabase
        .table("risk_scores")
        .select("id")
        .eq("entity_id", entity_id)
        .execute()
    ).data

    payload = {
        "entity_id": entity_id,
        "score": score["score"],
        "status": score["status"],
        "negative_mentions": score["negative_mentions"],
        "positive_mentions": score["positive_mentions"],
        "neutral_mentions": score["neutral_mentions"]
    }

    if existing:

        (
            supabase
            .table("risk_scores")
            .update(payload)
            .eq("entity_id", entity_id)
            .execute()
        )

    else:

        (
            supabase
            .table("risk_scores")
            .insert(payload)
            .execute()
        )


# -----------------------------------------------------
# Send email alert
# FIX: Was previously indented inside save_risk_score(),
# making it a local, unreachable function. Now at
# module level.
# FIX: Email recipient now pulled from the entity record
# (entity["email"]) with a fallback env variable rather
# than being hardcoded to a personal Gmail address.
# -----------------------------------------------------

def send_email(entity: dict, score: dict) -> bool:
    """
    Send a reputation alert email if score exceeds threshold.
    Returns True if email was sent, False otherwise.
    """

    if score["score"] < EMAIL_ALERT_THRESHOLD:
        return False

    # Prefer the entity's own email; fall back to env override
    recipient = (
        entity.get("email")
        or os.getenv("ALERT_EMAIL_FALLBACK", "onboarding@resend.dev")
    )

    status_emoji = {
        "healthy": "✅",
        "watch": "👀",
        "elevated": "⚠️",
        "high": "🔶",
        "critical": "🚨",
    }.get(score["status"], "🔔")

    resend.Emails.send({
        "from": "SentiWatch <onboarding@resend.dev>",
        "to": recipient,
        "subject": (
            f"{status_emoji} Reputation Alert — "
            f"{entity['name']} scored {score['score']}/100"
        ),
        "html": f"""
        <div style="font-family:sans-serif;max-width:560px;margin:0 auto;">
          <h2 style="color:#1A56DB;">SentiWatch Reputation Alert</h2>
          <p>
            <strong>{entity['name']}</strong> now has a reputation risk score of
            <strong style="font-size:1.2em;">{score['score']}/100</strong>.
          </p>
          <p>
            Status: <strong>{score['status'].upper()}</strong>
          </p>
          <table style="border-collapse:collapse;width:100%;">
            <tr>
              <td style="padding:8px;border:1px solid #e5e7eb;">Negative mentions</td>
              <td style="padding:8px;border:1px solid #e5e7eb;color:#E02424;">
                {score['negative_mentions']}
              </td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #e5e7eb;">Positive mentions</td>
              <td style="padding:8px;border:1px solid #e5e7eb;color:#0E9F6E;">
                {score['positive_mentions']}
              </td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #e5e7eb;">Neutral mentions</td>
              <td style="padding:8px;border:1px solid #e5e7eb;color:#6B7280;">
                {score['neutral_mentions']}
              </td>
            </tr>
          </table>
          <p style="margin-top:24px;color:#6B7280;font-size:0.85em;">
            Log in to your SentiWatch dashboard for full analysis and recommendations.
          </p>
        </div>
        """
    })

    return True


# -----------------------------------------------------
# Main orchestrator
# FIX: Was previously indented inside send_email(),
# making it completely unreachable. Now at module level.
# -----------------------------------------------------

def calculate_risk_and_alert(entity_id: str) -> dict:
    """
    Full pipeline:
    1. Fetch entity
    2. Fetch and join mentions + sentiment results
    3. Calculate risk score
    4. Save score to DB
    5. Send alert if threshold exceeded
    """

    entity = get_entity(entity_id)

    if not entity:
        return {"error": "Entity not found"}

    mentions = fetch_mentions(entity_id)

    score = calculate_entity_score(mentions)

    save_risk_score(entity_id, score)

    alert = send_email(entity, score)

    return {
        "entity": entity["name"],
        "risk_score": score["score"],
        "status": score["status"],
        "negative_mentions": score["negative_mentions"],
        "positive_mentions": score["positive_mentions"],
        "neutral_mentions": score["neutral_mentions"],
        "email_sent": alert
    }
