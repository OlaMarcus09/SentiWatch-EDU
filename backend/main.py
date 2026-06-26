from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from risk_engine import calculate_risk_and_alert
from fastapi import FastAPI
from database import supabase
from scrapers import scrape_nigerian_news, fetch_google_reviews, scrape_social_media

# This is the line that was missing!
from sentiment import analyze_and_store_sentiment 

app = FastAPI(title="SentiWatch API - MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all frontend domains to connect during development
    allow_credentials=True,
    allow_methods=["*"],  # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "SentiWatch API is live and running."}

@app.get("/health/db")
def check_db_connection():
    try:
        response = supabase.table("monitored_entities").select("id").limit(1).execute()
        return {"database_status": "Connected to Supabase successfully", "error": None}
    except Exception as e:
        return {"database_status": "Connection failed", "error": str(e)}

@app.post("/sync/{entity_id}")
def sync_all_sources(entity_id: str, brand_name: str, place_id: str = "mock_mode"):
    """Triggers all scrapers simultaneously to pull data into Supabase."""
    news_count = scrape_nigerian_news(entity_id, brand_name)
    google_count = fetch_google_reviews(entity_id, place_id)
    social_count = scrape_social_media(entity_id, brand_name)
    
    return {
        "status": "Sync Complete",
        "scraped_items": {
            "news_mentions": news_count,
            "google_reviews": google_count,
            "social_media_mentions": social_count
        }
    }

@app.post("/analyze")
def trigger_analysis(entity_id: str = None, brand_name: str = None):
    result = analyze_and_store_sentiment(entity_id=entity_id, brand_name=brand_name)
    return {"status": "Analysis Complete", "mentions_scored": result}

@app.post("/calculate-risk/{entity_id}")
def trigger_risk_calculation(entity_id: str):
    """Calculates risk score and sends alerts if necessary."""
    result = calculate_risk_and_alert(entity_id)
    return result

    class BrandCreateRequest(BaseModel):
     name: str

# Make sure this class is defined right here!
class BrandCreateRequest(BaseModel):
    name: str

@app.post("/entities")
def create_new_entity(payload: BrandCreateRequest):
    """Creates a new brand and immediately runs the first sync sequence."""
    if not payload.name.strip():
        return {"success": False, "error": "Name cannot be empty"}
        
    try:
        # 1. Insert into Supabase
        res = supabase.table("monitored_entities").insert({"name": payload.name}).execute()
        if not res.data:
            return {"success": False, "error": "Failed to create entity record"}
            
        new_entity = res.data[0]
        entity_id = new_entity["id"]
        
        # 2. Automatically trigger the initial ingestion sync sequence
        # Note: We import it here locally to avoid circular imports if needed, 
        # or just ensure sync_all_sources is imported at the top of main.py
        from scrapers import scrape_nigerian_news, scrape_social_media
        
        scrape_nigerian_news(entity_id, payload.name)
        scrape_social_media(entity_id, payload.name)
        
        return {"success": True, "entity_id": entity_id}
    except Exception as e:
        return {"success": False, "error": str(e)}