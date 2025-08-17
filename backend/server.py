import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import logging
from urllib.parse import unquote
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Global Radio API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class RadioStation(BaseModel):
    uuid: str
    name: str
    url: str
    country: str
    language: str
    tags: Optional[str] = ""
    bitrate: Optional[int] = 0
    votes: Optional[int] = 0

# Content filtering lists
INAPPROPRIATE_KEYWORDS = [
    'adult', 'xxx', 'sex', 'porn', 'erotic', 'explicit', 'mature', 
    'nsfw', 'strip', 'nude', 'fetish', 'kinky', 'dirty', 'hardcore',
    'uncensored', 'raw', 'underground', 'gangsta', 'violence', 'hate'
]

CLEAN_GENRES = [
    'news', 'talk', 'music', 'pop', 'rock', 'jazz', 'classical', 'country',
    'folk', 'world', 'ambient', 'chill', 'lounge', 'electronic', 'dance',
    'hip hop', 'r&b', 'soul', 'blues', 'gospel', 'christian', 'spiritual',
    'educational', 'sports', 'business', 'culture', 'community', 'public',
    'information', 'entertainment', 'family', 'kids', 'children'
]

def is_station_clean(station):
    """Filter out inappropriate content stations"""
    name = station.get('name', '').lower()
    tags = station.get('tags', '').lower()
    
    # Check for inappropriate keywords
    for keyword in INAPPROPRIATE_KEYWORDS:
        if keyword in name or keyword in tags:
            return False
    
    # Prefer stations with clean genres
    if tags:
        for clean_genre in CLEAN_GENRES:
            if clean_genre in tags:
                return True
    
    # Check for common clean indicators
    clean_indicators = ['fm', 'am', 'radio', 'station', 'news', 'music', 'public']
    for indicator in clean_indicators:
        if indicator in name:
            return True
    
    # Default: allow if no red flags found
    return True

def has_frequency_in_name(station_name):
    """Check if station name contains frequency information"""
    frequency_pattern = r'\b\d{2,3}\.?\d*\s*(fm|am|khz|mhz)?\b'
    return bool(re.search(frequency_pattern, station_name.lower()))

@app.get("/")
async def root():
    return {"message": "Global Radio API - Clean Family-Friendly Stations", "status": "running"}

@app.get("/api/stations", response_model=List[RadioStation])
async def get_radio_stations():
    """Fetch popular radio stations from Radio-Browser API"""
    try:
        # Use Radio-Browser API to get popular stations
        base_url = "https://de1.api.radio-browser.info"
        
        # Get top voted stations with good quality
        url = f"{base_url}/json/stations/topvote?limit=200"
        
        headers = {
            'User-Agent': 'GlobalRadioApp/1.0'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        stations_data = response.json()
        
        # Filter and format stations
        filtered_stations = []
        for station in stations_data:
            # Skip stations without proper URL or name
            if not station.get('url') or not station.get('name'):
                continue
                
            # Skip very low quality stations
            if station.get('bitrate', 0) < 32 and station.get('votes', 0) < 5:
                continue
            
            # Apply content filtering
            if not is_station_clean(station):
                continue
            
            filtered_station = RadioStation(
                uuid=station.get('stationuuid', ''),
                name=station.get('name', 'Unknown Station'),
                url=station.get('url', ''),
                country=station.get('country', 'Unknown'),
                language=station.get('language', 'Unknown'),
                tags=station.get('tags', ''),
                bitrate=station.get('bitrate', 0),
                votes=station.get('votes', 0)
            )
            filtered_stations.append(filtered_station)
        
        # Sort by votes and bitrate quality
        filtered_stations.sort(key=lambda x: (x.votes, x.bitrate), reverse=True)
        
        logger.info(f"Fetched {len(filtered_stations)} clean radio stations")
        return filtered_stations[:80]  # Return top 80 clean stations
        
    except requests.RequestException as e:
        logger.error(f"Error fetching stations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch radio stations")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/stations/clean", response_model=List[RadioStation])
async def get_clean_stations():
    """Get specifically filtered clean stations"""
    try:
        # Use multiple approaches to get diverse clean stations
        base_url = "https://de1.api.radio-browser.info"
        headers = {'User-Agent': 'GlobalRadioApp/1.0'}
        
        all_stations = []
        
        # Get top voted stations
        url1 = f"{base_url}/json/stations/topvote?limit=100"
        response1 = requests.get(url1, headers=headers, timeout=10)
        if response1.status_code == 200:
            all_stations.extend(response1.json())
        
        # Get stations with high bitrate
        url2 = f"{base_url}/json/stations/search?bitratemin=128&limit=50"
        response2 = requests.get(url2, headers=headers, timeout=10)
        if response2.status_code == 200:
            all_stations.extend(response2.json())
        
        # Get news and talk stations
        url3 = f"{base_url}/json/stations/bytag/news?limit=30"
        response3 = requests.get(url3, headers=headers, timeout=10)
        if response3.status_code == 200:
            all_stations.extend(response3.json())
        
        # Remove duplicates by UUID
        unique_stations = {}
        for station in all_stations:
            uuid = station.get('stationuuid')
            if uuid and uuid not in unique_stations:
                unique_stations[uuid] = station
        
        # Filter and format stations
        filtered_stations = []
        for station in unique_stations.values():
            # Skip stations without proper URL or name
            if not station.get('url') or not station.get('name'):
                continue
                
            # Skip very low quality stations
            if station.get('bitrate', 0) < 64 and station.get('votes', 0) < 10:
                continue
            
            # Apply strict content filtering
            if not is_station_clean(station):
                continue
            
            # Prefer stations with frequency in name or clean genres
            priority_score = 0
            if has_frequency_in_name(station.get('name', '')):
                priority_score += 10
            if any(genre in station.get('tags', '').lower() for genre in ['news', 'music', 'talk', 'public']):
                priority_score += 5
            
            filtered_station = RadioStation(
                uuid=station.get('stationuuid', ''),
                name=station.get('name', 'Unknown Station'),
                url=station.get('url', ''),
                country=station.get('country', 'Unknown'),
                language=station.get('language', 'Unknown'),
                tags=station.get('tags', ''),
                bitrate=station.get('bitrate', 0),
                votes=station.get('votes', 0) + priority_score
            )
            filtered_stations.append(filtered_station)
        
        # Sort by enhanced votes (includes priority score)
        filtered_stations.sort(key=lambda x: x.votes, reverse=True)
        
        logger.info(f"Fetched {len(filtered_stations)} clean filtered stations")
        return filtered_stations[:60]  # Return top 60 clean stations
        
    except Exception as e:
        logger.error(f"Error fetching clean stations: {e}")
        # Fallback to regular stations endpoint
        return await get_radio_stations()

@app.get("/api/stream/{station_url:path}")
async def stream_radio(station_url: str):
    """Proxy radio stream to handle CORS issues"""
    try:
        # Decode the URL
        decoded_url = unquote(station_url)
        logger.info(f"Streaming from: {decoded_url}")
        
        # Set up headers for the stream request
        headers = {
            'User-Agent': 'GlobalRadioApp/1.0',
            'Accept': 'audio/*,*/*;q=0.1',
            'Connection': 'keep-alive',
            'Range': 'bytes=0-'
        }
        
        # Make request to the radio station
        response = requests.get(decoded_url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Get content type from response
        content_type = response.headers.get('Content-Type', 'audio/mpeg')
        
        # Create streaming response
        def generate():
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except Exception as e:
                logger.error(f"Error during streaming: {e}")
        
        return StreamingResponse(
            generate(),
            media_type=content_type,
            headers={
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive'
            }
        )
        
    except requests.RequestException as e:
        logger.error(f"Error streaming from {decoded_url}: {e}")
        raise HTTPException(status_code=404, detail="Radio station not available")
    except Exception as e:
        logger.error(f"Unexpected streaming error: {e}")
        raise HTTPException(status_code=500, detail="Streaming error")

@app.get("/api/stations/search")
async def search_stations(query: str = "", country: str = "", limit: int = 30):
    """Search radio stations by name, country, or frequency"""
    try:
        base_url = "https://de1.api.radio-browser.info"
        headers = {'User-Agent': 'GlobalRadioApp/1.0'}
        
        # Check if query contains frequency pattern
        frequency_pattern = r'(\d{2,3}\.?\d*)\s*(fm|am|khz|mhz)?'
        is_frequency_search = bool(re.search(frequency_pattern, query.lower())) if query else False
        
        if is_frequency_search:
            # For frequency searches, get more stations and filter locally
            url = f"{base_url}/json/stations/topvote?limit=200"
        elif query:
            # Search by name
            url = f"{base_url}/json/stations/byname/{query}?limit={limit*2}"
        elif country:
            # Search by country
            url = f"{base_url}/json/stations/bycountry/{country}?limit={limit*2}"
        else:
            # Get popular clean stations
            return await get_clean_stations()
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        stations_data = response.json()
        
        # Format and filter stations
        filtered_stations = []
        for station in stations_data:
            if not station.get('url') or not station.get('name'):
                continue
            
            # Apply content filtering
            if not is_station_clean(station):
                continue
            
            # For frequency searches, filter by frequency in name
            if is_frequency_search:
                station_name = station.get('name', '').lower()
                query_freq = re.search(frequency_pattern, query.lower())
                if query_freq:
                    freq_number = query_freq.group(1)
                    if freq_number not in station_name:
                        continue
                
            filtered_station = RadioStation(
                uuid=station.get('stationuuid', ''),
                name=station.get('name', 'Unknown Station'),
                url=station.get('url', ''),
                country=station.get('country', 'Unknown'),
                language=station.get('language', 'Unknown'),
                tags=station.get('tags', ''),
                bitrate=station.get('bitrate', 0),
                votes=station.get('votes', 0)
            )
            filtered_stations.append(filtered_station)
        
        # Sort by votes and limit results
        filtered_stations.sort(key=lambda x: x.votes, reverse=True)
        result = filtered_stations[:limit]
        
        logger.info(f"Search '{query}' returned {len(result)} clean stations")
        return result
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "global-radio-clean-api", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)