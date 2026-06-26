# backend/cron_sync.py
import time
import requests
from database import supabase
import os
# This will look for the variable you just added in Railway
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def run_automated_pipeline():
    print(f"⏰ Background sync initialized at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Fetch every monitored brand from the database
    entities_res = supabase.table("monitored_entities").select("id, name").execute()
    entities = entities_res.data or []
    
    for entity in entities:
        entity_id = entity["id"]
        name = entity["name"]
        print(f"🔄 Syncing tracks for: {name}")
        
        # 2. Trigger Scrapers
        requests.post(f"{BACKEND_URL}/sync/{entity_id}?brand_name={name}")
        
    # 3. Process Sentiments via OpenRouter AI
    print("🧠 Running sentiment scoring engines...")
    requests.post(f"{BACKEND_URL}/analyze")
    
    # 4. Evaluate Risk Calculations and Fire Resend Alerts
    print("🚨 Recalculating alert thresholds...")
    for entity in entities:
        requests.post(f"{BACKEND_URL}/calculate-risk/{entity['id']}")
        
    print("✅ System sync cycle complete. Sleeping...")

if __name__ == "__main__":
    # For local MVP testing, a simple loop that runs once every 4 hours
    while True:
        run_automated_pipeline()
        time.sleep(4 * 60 * 60)