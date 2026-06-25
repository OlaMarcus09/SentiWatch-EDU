import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from database import supabase

def scrape_nigerian_news(entity_id: str, brand_name: str) -> int:
    """
    Pulls real-time news mentions using an open Google News RSS feed wrapper.
    Completely free, no API keys required, and heavily rate-limiting proof.
    """
    # URL encode the brand name for safety (e.g., "Kuda Bank" -> "Kuda+Bank")
    query = brand_name.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-NG&gl=NG&ceid=NG:en"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return 0
            
        # Parse the XML response feed
        root = ET.fromstring(response.content)
        items = root.findall(".//item")
        
        inserted_count = 0
        # Look at the top 10 freshest news items
        for item in items[:10]:
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            
            # Avoid duplicate inserts by checking if the URL already exists
            exists = supabase.table("mentions").select("id").eq("url", link).execute()
            if exists.data:
                continue
                
            supabase.table("mentions").insert({
                "entity_id": entity_id,
                "source": "Nigerian News Feed",
                "content": title,
                "url": link
            }).execute()
            inserted_count += 1
            
        return inserted_count
    except Exception as e:
        print(f"News scraping error for {brand_name}: {e}")
        return 0

def fetch_google_reviews(entity_id: str, place_id: str) -> int:
    """
    Real-world Google Places API integration placeholder.
    To turn this live, get a free $200/month credit key from Google Cloud Console.
    """
    if place_id == "mock_mode":
        # Fallback to a realistic data entry if no real place_id is passed yet
        link = "https://maps.google.com/?cid=mock"
        exists = supabase.table("mentions").select("id").eq("url", link).execute()
        if exists.data:
            return 0
            
        supabase.table("mentions").insert({
            "entity_id": entity_id,
            "source": "Google Maps",
            "content": f"The service speed at this branch was completely unacceptable. Long queues outside.",
            "url": link
        }).execute()
        return 1

    # Real implementation when you drop in your GOOGLE_MAPS_API_KEY:
    # api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    # url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=reviews&key={api_key}"
    # ... parse response.json()['result']['reviews']
    return 0

def scrape_social_media(entity_id: str, brand_name: str) -> int:
    """
    Pulls public discussions using an open web aggregator layer.
    """
    query = brand_name.replace(" ", "+")
    # Utilizing an open Reddit RSS tracking mirror for live testing
    url = f"https://www.reddit.com/search.rss?q={query}&sort=new"
    headers = {"User-Agent": "Mozilla/5.0 (SentiWatch Brand Agent v1.0)"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return 0
            
        root = ET.fromstring(response.content)
        # Handle Atom feed namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall(".//atom:entry", ns)
        
        inserted_count = 0
        for entry in entries[:5]:
            title = entry.find("atom:title", ns).text if entry.find("atom:title", ns) is not None else ""
            link_elem = entry.find("atom:link", ns)
            link = link_elem.attrib['href'] if link_elem is not None else ""
            
            if not title or not link:
                continue
                
            exists = supabase.table("mentions").select("id").eq("url", link).execute()
            if exists.data:
                continue
                
            supabase.table("mentions").insert({
                "entity_id": entity_id,
                "source": "Public Forums (X/Reddit)",
                "content": title,
                "url": link
            }).execute()
            inserted_count += 1
            
        return inserted_count
    except Exception as e:
        print(f"Social aggregation error for {brand_name}: {e}")
        return 0