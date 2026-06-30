import os

import resend

from dotenv import load_dotenv

from database import supabase, supabase_admin

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
        supabase_admin
        .table("monitored_entities")
        .select("*")
        .eq("id", entity_id)
        .single()
        .execute()
    )

    return result.data


# -----------------------------------------------------
# Fetch mentions
# Joins mentions + sentiment_results into the flat
# structure calculate_entity_score() actually expects.
# Uses supabase_admin to bypass RLS for backend reads.
# -----------------------------------------------------

def fetch_mentions(entity_id: str):
    """
    Fetch all mentions for an entity and join them
    with their sentiment results.
    Returns a flat list ready for calculate_entity_score().
    """

    mentions = (
        supabase_admin
        .table("mentions")
        .select("*")
        .eq("entity_id", entity_id)
        .execute()
    ).data

    if not mentions:
        return []

    mention_lookup = {m["id"]: m for m in mentions}

    sentiment_rows = (
        supabase_admin
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
            "source": _normalise_source(mention.get("source", "other")),
            "created_at": mention.get("created_at")
        })

    return merged


def _normalise_source(raw: str) -> str:
    """
    Maps the human-readable source strings saved by scrapers.py
    to the lowercase keys defined in SOURCE_WEIGHTS.
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
# Upserts into risk_scores with the full metric set,
# including negative/positive/neutral counts the
# dashboard depends on.
# -----------------------------------------------------

def save_risk_score(entity_id: str, score: dict):
    """
    Upsert the risk score for an entity.
    Updates if a record exists, inserts if not.
    """

    existing = (
        supabase_admin
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
            supabase_admin
            .table("risk_scores")
            .update(payload)
            .eq("entity_id", entity_id)
            .execute()
        )

    else:

        (
            supabase_admin
            .table("risk_scores")
            .insert(payload)
            .execute()
        )


# -----------------------------------------------------
# Send email alert
# Now actually called from the orchestrator below.
# -----------------------------------------------------

def send_email(entity: dict, score: dict) -> bool:
    """
    Send a reputation alert email if score exceeds threshold.
    Returns True if email was sent, False otherwise.
    """

    if score["score"] < EMAIL_ALERT_THRESHOLD:
        return False

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
# Recommendation Engine
# Kept exactly as Gemini wrote it — this part was fine.
# -----------------------------------------------------

def generate_recommendation_matrix(score: int, category: str) -> str:
    """
    Returns highly formal, contextual enterprise recommendations for the Nigerian market
    based on risk bands and primary trigger categories.
    """
    category = category.lower().strip()

    if score <= 25:
        return (
            "ACTION PLAN: Maintaining Brand Equilibrium\n\n"
            "1. REPUTATION STATUS: Brand sentiment is stable and within nominal safe operating parameters.\n"
            "2. DEPLOYMENT TIMELINE: No active crisis intervention required.\n"
            "3. RECOMMENDATION: Continue standard automated monitoring. Ensure customer service lines "
            "respond to routine social media inquiries within 4 hours to maintain this baseline. Utilize "
            "positive feedback trends captured by SentiWatch for organic marketing assets on LinkedIn."
        )

    elif 26 <= score <= 50:
        if category in ["customer_service", "operations", "product_quality"]:
            return (
                "ACTION PLAN: Operational Friction Triage\n\n"
                "1. REPUTATION STATUS: Minor cluster of public dissatisfaction identified regarding transaction/delivery delays.\n"
                "2. DEPLOYMENT TIMELINE: Address via customer success pathways within 24 Hours.\n"
                "3. RECOMMENDATION: Instruct your digital media team to actively respond to the identified negative "
                "threads. Use a formal boilerplate acknowledging the glitch without admitting structural fault (e.g., 'We "
                "are aware some users are experiencing delays and our engineering team is resolving it'). Avoid automated "
                "bots; deploy human customer support agents to resolve issues publicly. To suppress negative search signals, "
                "trigger a WhatsApp Business campaign requesting positive reviews from your top 10% loyal active clients."
            )
        else:
            return (
                "ACTION PLAN: Reputational Baseline Monitoring\n\n"
                "1. REPUTATION STATUS: Low-level critical chatter detected outside standard customer service issues.\n"
                "2. DEPLOYMENT TIMELINE: Internal assessment within 24 Hours.\n"
                "3. RECOMMENDATION: Brief internal communications teams to trace the root source of the negative mentions. "
                "Do not issue a public statement yet, as this may inadvertently amplify a minor issue. Audit internal access "
                "logs if the chatter involves operational integrity or data systems."
            )

    elif 51 <= score <= 75:
        if category in ["fraud", "financial", "cyber", "security"]:
            return (
                "ACTION PLAN: Immediate Trust Protection Protocol\n\n"
                "1. REPUTATION STATUS: High-risk allegations involving financial irregularities, asset safety, or system security breach.\n"
                "2. DEPLOYMENT TIMELINE: Executive leadership intervention within 12 Hours.\n"
                "3. RECOMMENDATION: Immediately draft a formal corporate clarification signed by executive management or the "
                "Legal Department. Publish this across your verified corporate handles (X, LinkedIn) and pin it. Explicitly state "
                "that user funds/data remain entirely secure. **Strict Warning:** Do not speculate on regulatory outcomes or make "
                "defensive emotional claims. Instruct all staff members to refer external press inquiries exclusively to the "
                "designated media liaison."
            )
        elif category in ["regulatory", "legal"]:
            return (
                "ACTION PLAN: Regulatory Alignment Strategy\n\n"
                "1. REPUTATION STATUS: Public chatter regarding regulatory fines, audit investigations, or legal actions.\n"
                "2. DEPLOYMENT TIMELINE: Legal compliance review within 12 Hours.\n"
                "3. RECOMMENDATION: Prepare a factual statement verifying your regulatory standing or compliance status. If an "
                "investigation is ongoing, issue a conservative holding statement: 'We are cooperating fully with the relevant "
                "authorities to address this administrative inquiry.' Do not debate or antagonize institutional regulators "
                "(CBN, EFCC, FCCPC, NITDA) in the public domain under any circumstances."
            )
        else:
            return (
                "ACTION PLAN: Escalated Corporate Triage\n\n"
                "1. REPUTATION STATUS: High volume of negative public sentiment affecting general brand positioning.\n"
                "2. DEPLOYMENT TIMELINE: Communications review within 12 Hours.\n"
                "3. RECOMMENDATION: Convene an emergency meeting of the corporate communications team. Draft an objective "
                "internal brief explaining the issue, current impacts, and mitigation steps. Pause any active programmatic "
                "ad campaigns or sponsored content to avoid running paid promotions over live negative commentary."
            )

    else:
        return (
            "CRISIS ACTIVATION MANDATE: Institutional Escalation\n\n"
            "1. REPUTATION STATUS: Critical threat level. Reputational damage is actively compounding across high-credibility media "
            "channels (Mainstream Press/Nairaland Frontpage).\n"
            "2. DEPLOYMENT TIMELINE: **IMMEDIATE DEPLOYMENT (Under 2 Hours)**\n"
            "3. RECOMMENDATION: Retain a professional, specialized Nigerian PR crisis management firm immediately. SentiWatch "
            "recommends immediate outreach to verified local partners to handle narrative containment. The CEO or designated "
            "executive spokesperson must prepare to issue a video address or comprehensive press release addressing the core "
            "issue transparently. Establish a 24/7 internal war-room to monitor real-time updates via SentiWatch every hour."
        )


# -----------------------------------------------------
# Main orchestrator
# FIX: Now calls fetch_mentions() to get the properly
# joined mention+sentiment data, calls save_risk_score()
# instead of a raw insert (preserving mention counts),
# and actually calls send_email().
# -----------------------------------------------------

def calculate_risk_and_alert(entity_id: str) -> dict:
    """
    Full pipeline:
    1. Fetch entity
    2. Fetch and join mentions + sentiment results
    3. Calculate risk score
    4. Save score to DB (with full metric set)
    5. Generate and save recommendation
    6. Send alert if threshold exceeded
    """

    entity = get_entity(entity_id)

    if not entity:
        return {"error": "Entity not found"}

    mentions = fetch_mentions(entity_id)

    metrics = calculate_entity_score(mentions)

    save_risk_score(entity_id, metrics)

    final_score = metrics["score"]
    trigger_cat = metrics["primary_trigger_category"]

    action_text = generate_recommendation_matrix(final_score, trigger_cat)

    supabase_admin.table("recommendations").insert({
        "entity_id": entity_id,
        "risk_score": final_score,
        "trigger_category": trigger_cat,
        "action_plan": action_text
    }).execute()

    alert_sent = send_email(entity, metrics)

    return {
        "entity": entity["name"],
        "risk_score": final_score,
        "status": metrics["status"],
        "negative_mentions": metrics["negative_mentions"],
        "positive_mentions": metrics["positive_mentions"],
        "neutral_mentions": metrics["neutral_mentions"],
        "primary_trigger_category": trigger_cat,
        "recommendation_generated": True,
        "email_sent": alert_sent
    }