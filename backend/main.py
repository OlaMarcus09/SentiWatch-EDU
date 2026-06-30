from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from supabase import create_client, Client

from database import supabase, supabase_admin
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
# REQUEST MODELS
# =========================================================

class BrandCreateRequest(BaseModel):
    name: str
    # Removed user_id: The backend now extracts it securely from the Auth token!

# =========================================================
# HEALTH CHECKS
# =========================================================

@app.get("/")
def read_root():
    return {"status": "SentiWatch API is live and running."}

@app.get("/health/db")
def check_db_connection():
    try:
        supabase.table("monitored_entities").select("id").limit(1).execute()
        return {"database_status": "Connected to Supabase successfully", "error": None}
    except Exception as e:
        return {"database_status": "Connection failed", "error": str(e)}

# =========================================================
# MANUAL ENDPOINTS
# =========================================================

@app.post("/sync/{entity_id}")
def sync_all_sources(entity_id: str, brand_name: str, place_id: str = "mock_mode"):
    news_count = scrape_nigerian_news(entity_id, brand_name)
    google_count = fetch_google_reviews(entity_id, place_id)
    social_count = scrape_social_media(entity_id, brand_name)
    
    return {
        "status": "Sync Complete",
        "scraped_items": {
            "news_mentions": news_count,
            "google_reviews": google_count,
            "social_media_mentions": social_count,
        },
    }

@app.post("/analyze")
def trigger_analysis(entity_id: str = None, brand_name: str = None):
    result = analyze_and_store_sentiment(entity_id=entity_id, brand_name=brand_name)
    return {"status": "Analysis Complete", "mentions_scored": result}

@app.post("/calculate-risk/{entity_id}")
def trigger_risk_calculation(entity_id: str):
    result = calculate_risk_and_alert(entity_id)
    return result

# =========================================================
# CREATE ENTITY (SECURE AUTHENTICATED HANDLER)
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
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    # Require authorization header
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    # Verify user token
    try:
        auth_response = supabase_admin.auth.get_user(token)
        user = getattr(auth_response, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = user.id
        user_email = user.email

    except HTTPException:
        raise
    except Exception as e:
        print("AUTH ERROR:", str(e))
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

    # Ensure profile exists in your users table
    try:
        supabase_admin.table("users").upsert({
            "id": user_id,
            "email": user_email,
        }).execute()
    except Exception as e:
        print("Profile upsert warning:", e)

    # Insert monitored entity
    try:
        insert_response = supabase_admin.table("monitored_entities").insert({
            "name": payload.name,
            "user_id": user_id,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB insert failed: {str(e)}")

    # Safely handle the response format based on Supabase-py version
    if hasattr(insert_response, "error") and insert_response.error:
        raise HTTPException(status_code=400, detail=str(insert_response.error))

    new_entity = getattr(insert_response, "data", [None])[0]
    if not new_entity:
        raise HTTPException(status_code=500, detail="Failed to create entity record")

    entity_id = new_entity["id"]

    # Trigger pipeline
    try:
        scrape_nigerian_news(entity_id, payload.name)
        scrape_social_media(entity_id, payload.name)
        analyze_and_store_sentiment(entity_id=entity_id, brand_name=payload.name)
        calculate_risk_and_alert(entity_id)
    except Exception as e:
        print("Pipeline error:", e)

    return {"success": True, "entity_id": entity_id}