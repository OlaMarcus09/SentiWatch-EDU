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
    Returns formal, contextual university operations recommendations
    based on risk bands and primary campus trigger categories.
    """
    category = category.lower().strip()

    if score <= 25:
        return (
            "ACTION PLAN: Maintaining Campus Stability\n\n"
            "1. CAMPUS STATUS: Sentiment indicators are stable and within safe operating thresholds.\n"
            "2. DEPLOYMENT TIMELINE: No active crisis intervention required.\n"
            "3. RECOMMENDATION: Continue routine monitoring across student channels. Maintain standard "
            "response SLAs for low-risk complaints and publish periodic student guidance updates to preserve trust."
        )

    elif 26 <= score <= 50:
        if category in ["portal_issues"]:
            return (
                "ACTION PLAN: Portal Reliability Triage\n\n"
                "1. CAMPUS STATUS: Early cluster of complaints indicates intermittent portal access or transaction failures.\n"
                "2. DEPLOYMENT TIMELINE: IT/Portal team intervention within 24 Hours.\n"
                "3. RECOMMENDATION: Assign IT operations to validate uptime, login flow, payment/registration endpoints, and "
                "error logs. Publish a student-facing incident notice with expected resolution time and alternate submission routes "
                "where needed."
            )
        elif category in ["fees", "scholarships"]:
            return (
                "ACTION PLAN: Financial Support Clarification\n\n"
                "1. CAMPUS STATUS: Low-to-moderate concern detected around fees, payment windows, or scholarship communication.\n"
                "2. DEPLOYMENT TIMELINE: Bursary response within 24 Hours.\n"
                "3. RECOMMENDATION: Bursary should issue a clear breakdown of payment timelines, penalties, waivers, and scholarship "
                "eligibility criteria. Open an escalation channel for affected students and publish FAQ updates."
            )
        elif category in ["admissions", "exams"]:
            return (
                "ACTION PLAN: Academic Process Alignment\n\n"
                "1. CAMPUS STATUS: Minor but visible dissatisfaction around admissions or exam-related processes.\n"
                "2. DEPLOYMENT TIMELINE: Registrar/Academic Registry review within 24 Hours.\n"
                "3. RECOMMENDATION: Verify published schedules, candidate lists, venue information, and policy notices. "
                "Release a formal clarification bulletin and provide a correction window for documented errors."
            )
        else:
            return (
                "ACTION PLAN: Baseline Campus Monitoring\n\n"
                "1. CAMPUS STATUS: Low-level critical chatter detected outside routine operational themes.\n"
                "2. DEPLOYMENT TIMELINE: Internal assessment within 24 Hours.\n"
                "3. RECOMMENDATION: Route issue to the relevant unit head, gather evidence from student-facing systems, "
                "and issue a concise internal brief before any broad public communication."
            )

    elif 51 <= score <= 75:
        if category in ["portal_issues"]:
            return (
                "ACTION PLAN: Critical Portal Continuity Protocol\n\n"
                "1. CAMPUS STATUS: High-risk disruption signals around portal functionality and student digital access.\n"
                "2. DEPLOYMENT TIMELINE: IT/Portal leadership intervention within 12 Hours.\n"
                "3. RECOMMENDATION: Activate incident-response workflow, assign named technical owners, and provide "
                "time-bound student advisories. Coordinate with Registrar and Bursary to extend affected deadlines where necessary."
            )
        elif category in ["hostels", "campus_life", "lecturers"]:
            return (
                "ACTION PLAN: Student Welfare Safeguard Activation\n\n"
                "1. CAMPUS STATUS: Elevated concerns indicate possible welfare, accommodation, or student-staff tension.\n"
                "2. DEPLOYMENT TIMELINE: Student Affairs intervention within 12 Hours.\n"
                "3. RECOMMENDATION: Student Affairs should deploy welfare officers, open confidential reporting channels, "
                "and publish support contacts. Coordinate with relevant departments for immediate de-escalation and visible follow-up."
            )
        elif category in ["fees", "scholarships"]:
            return (
                "ACTION PLAN: Financial Distress Mitigation\n\n"
                "1. CAMPUS STATUS: High-volume concern around fees burden, payment enforcement, or scholarship delays.\n"
                "2. DEPLOYMENT TIMELINE: Bursary leadership response within 12 Hours.\n"
                "3. RECOMMENDATION: Issue an official fee-relief communication (where policy permits), confirm scholarship "
                "processing status, and provide case-by-case support channels for students at risk of exclusion."
            )
        elif category in ["admissions", "exams"]:
            return (
                "ACTION PLAN: Academic Integrity & Access Escalation\n\n"
                "1. CAMPUS STATUS: Major confidence risk around admissions fairness or examination processes.\n"
                "2. DEPLOYMENT TIMELINE: Registrar-led escalation within 12 Hours.\n"
                "3. RECOMMENDATION: Registrar should publish verified process documentation, assign an appeal desk, "
                "and communicate remediation timelines for affected cohorts."
            )
        else:
            return (
                "ACTION PLAN: Escalated Campus Triage\n\n"
                "1. CAMPUS STATUS: High volume of negative sentiment impacting institutional trust.\n"
                "2. DEPLOYMENT TIMELINE: Leadership review within 12 Hours.\n"
                "3. RECOMMENDATION: Convene cross-unit response meeting (Registrar, Bursary, IT, Student Affairs), "
                "produce a unified action brief, and publish coordinated status updates."
            )

    else:
        return (
            "CRISIS ACTIVATION MANDATE: Campus-wide Escalation\n\n"
            "1. CAMPUS STATUS: Critical threat level with rapidly compounding public concern across student channels.\n"
            "2. DEPLOYMENT TIMELINE: **IMMEDIATE DEPLOYMENT (Under 2 Hours)**\n"
            "3. RECOMMENDATION: Activate the university emergency communications protocol immediately. Establish a joint "
            "incident room across Registrar, Bursary, IT/Portal, and Student Affairs. Release a verified campus-wide advisory, "
            "state immediate protections for students, and publish update intervals until stabilization is confirmed."
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