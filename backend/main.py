from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from supabase import create_client, Client

from database import supabase
from scrapers import (
    scrape_nigerian_news,
    fetch_google_reviews,
    scrape_social_media,
)
from sentiment import analyze_and_store_sentiment
from risk_engine import calculate_risk_and_alert

# =========================================================
# APP INITIALIZATION
# =========================================================

app = FastAPI(title="SentiWatch API - SaaS Version")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://senti-watch.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# SUPABASE ADMIN CLIENT
# =========================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
    raise ValueError(
        "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE environment variables."
    )

supabase_admin: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE,
)

# =========================================================
# REQUEST MODELS
# =========================================================

class BrandCreateRequest(BaseModel):
    name: str

# =========================================================
# HEALTH CHECKS
# =========================================================

@app.get("/")
def read_root():
    return {
        "status": "SentiWatch API is live and running."
    }


@app.get("/health/db")
def check_db_connection():
    try:
        supabase.table("monitored_entities") \
            .select("id") \
            .limit(1) \
            .execute()

        return {
            "database_status": "Connected to Supabase successfully",
            "error": None,
        }

    except Exception as e:
        return {
            "database_status": "Connection failed",
            "error": str(e),
        }

# =========================================================
# MANUAL SYNC
# =========================================================

@app.post("/sync/{entity_id}")
def sync_all_sources(
    entity_id: str,
    brand_name: str,
    place_id: str = "mock_mode",
):
    """
    Triggers all scrapers simultaneously to pull data into Supabase.
    """

    news_count = scrape_nigerian_news(
        entity_id,
        brand_name,
    )

    google_count = fetch_google_reviews(
        entity_id,
        place_id,
    )

    social_count = scrape_social_media(
        entity_id,
        brand_name,
    )

    return {
        "status": "Sync Complete",
        "scraped_items": {
            "news_mentions": news_count,
            "google_reviews": google_count,
            "social_media_mentions": social_count,
        },
    }

# =========================================================
# MANUAL ANALYSIS
# =========================================================

@app.post("/analyze")
def trigger_analysis(
    entity_id: str = None,
    brand_name: str = None,
):
    result = analyze_and_store_sentiment(
        entity_id=entity_id,
        brand_name=brand_name,
    )

    return {
        "status": "Analysis Complete",
        "mentions_scored": result,
    }

# =========================================================
# MANUAL RISK CALCULATION
# =========================================================

@app.post("/calculate-risk/{entity_id}")
def trigger_risk_calculation(entity_id: str):
    """
    Calculates risk score and sends alerts if necessary.
    """
    result = calculate_risk_and_alert(entity_id)
    return result

# =========================================================
# CREATE ENTITY (AUTHENTICATED USER)
# =========================================================

@app.post("/entities")
async def create_new_entity(
    payload: BrandCreateRequest,
    authorization: str | None = Header(None),
):
    """
    Creates a new monitored entity tied to the authenticated user.
    """

    # Validate name
    if not payload.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty",
        )

    # Require authorization header
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header",
        )

    token = authorization.replace(
        "Bearer ",
        "",
    ).strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header",
        )

    # Verify user token
    try:
        auth_response = supabase_admin.auth.get_user(token)
        user = auth_response.user
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}",
        )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Unable to authenticate user",
        )

    user_id = user.id
    user_email = user.email

    # Ensure profile exists
    try:
        supabase_admin.table("users").upsert({
            "id": user_id,
            "email": user_email,
        }).execute()
    except Exception:
        # Ignore failures here; insert below will reveal FK issues
        pass

    # Create monitored entity
    try:
        insert_response = (
            supabase_admin
            .table("monitored_entities")
            .insert({
                "name": payload.name,
                "user_id": user_id,
            })
            .execute()
        )

        if not insert_response.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to create entity record",
            )

        new_entity = insert_response.data[0]
        entity_id = new_entity["id"]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database insert failed: {str(e)}",
        )

    # Run pipeline
    try:
        scrape_nigerian_news(
            entity_id,
            payload.name,
        )

        scrape_social_media(
            entity_id,
            payload.name,
        )

        analyze_and_store_sentiment(
            entity_id=entity_id,
            brand_name=payload.name,
        )

        calculate_risk_and_alert(
            entity_id,
        )

    except Exception as e:
        print(f"Pipeline error: {e}")

    return {
        "success": True,
        "entity_id": entity_id,
    }