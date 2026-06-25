import os

import resend

from dotenv import load_dotenv

from database import supabase

from scoring import calculate_entity_score

from constants import EMAIL_ALERT_THRESHOLD

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")
def get_entity(entity_id):

    result = (

        supabase

        .table("monitored_entities")

        .select("*")

        .eq("id", entity_id)

        .single()

        .execute()

    )

    return result.data
    def fetch_mentions(entity_id):

     mentions = (

        supabase

        .table("mentions")

        .select("*")

        .eq("entity_id", entity_id)

        .execute()

    ).data

    if not mentions:

        return []

    mention_lookup = {

        m["id"]: m

        for m in mentions

    }

    sentiment = (

        supabase

        .table("sentiment_results")

        .select("*")

        .in_(

            "mention_id",

            list(mention_lookup.keys())

        )

        .execute()

    ).data

    merged = []

    for row in sentiment:

        mention = mention_lookup.get(

            row["mention_id"]

        )

        if not mention:

            continue

        merged.append({

            "label": row["label"],

            "severity": row["severity"],

            "confidence": row["confidence"],

            "category": row["category"],

            "risk_level": row["risk_level"],

            "source": mention.get(

                "source",

                "other"

            ),

            "created_at": mention.get(

                "created_at"

            )

        })

    return merged
def save_risk_score(entity_id, score):

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
        def send_email(entity, score):

         if score["score"] < EMAIL_ALERT_THRESHOLD:

            return False

    resend.Emails.send({

        "from":

        "SentiWatch <onboarding@resend.dev>",

        "to":

        "workspaceafrica.hq@gmail.com",

        "subject":

        f"🚨 Reputation Alert - {entity['name']}",

        "html":

        f"""

        <h2>Risk Alert</h2>

        <p>

        <strong>{entity['name']}</strong>

        now has a reputation score of

        <strong>{score['score']}/100</strong>.

        </p>

        <p>

        Status:

        <strong>{score['status'].upper()}</strong>

        </p>

        <ul>

        <li>Negative: {score['negative_mentions']}</li>

        <li>Positive: {score['positive_mentions']}</li>

        <li>Neutral: {score['neutral_mentions']}</li>

        </ul>

        """

    })

    return True
    def calculate_risk_and_alert(entity_id):

     entity = get_entity(entity_id)

    if not entity:

        return {

            "error":

            "Entity not found"

        }

    mentions = fetch_mentions(entity_id)

    score = calculate_entity_score(

        mentions

    )

    save_risk_score(

        entity_id,

        score

    )

    alert = send_email(

        entity,

        score

    )

    return {

        "entity": entity["name"],

        "risk_score": score["score"],

        "status": score["status"],

        "negative_mentions": score["negative_mentions"],

        "positive_mentions": score["positive_mentions"],

        "neutral_mentions": score["neutral_mentions"],

        "email_sent": alert

    }