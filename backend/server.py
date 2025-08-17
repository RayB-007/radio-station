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
    'information', 'entertainment', 'family', 'kids', 'children',
    'bollywood', 'bhangra', 'indian', 'hindi', 'punjabi', 'desi', 'filmi',
    'asian', 'international', 'ethnic', 'multicultural'
]

# Priority genres that should be boosted in search results
PRIORITY_GENRES = [
    'bollywood', 'bhangra', 'indian', 'hindi', 'punjabi', 'news', 'music', 'talk'
]

def is_station_clean(station):
    """Filter out inappropriate content stations"""
    name = station.get('name', '').lower()
    tags = station.get('tags', '').lower()
    country = station.get('country', '').lower()
    
    # Check for inappropriate keywords
    for keyword in INAPPROPRIATE_KEYWORDS:
        if keyword in name or keyword in tags:
            return False
    
    # Prefer stations with clean genres
    if tags:
        for clean_genre in CLEAN_GENRES:
            if clean_genre in tags:
                return True
    
    # Special priority for Bollywood/Indian content
    bollywood_keywords = ['bollywood', 'bhangra', 'hindi', 'punjabi', 'indian', 'desi', 'filmi']
    for keyword in bollywood_keywords:
        if keyword in name or keyword in tags or keyword in country:
            return True
    
    # Check for common clean indicators
    clean_indicators = ['fm', 'am', 'radio', 'station', 'news', 'music', 'public']
    for indicator in clean_indicators:
        if indicator in name:
            return True
    
    # Default: allow if no red flags found
    return True

def get_station_priority_score(station):
    """Calculate priority score for station ranking"""
    name = station.get('name', '').lower()
    tags = station.get('tags', '').lower()
    country = station.get('country', '').lower()
    
    score = station.get('votes', 0)
    
    # Boost Bollywood and Bhangra stations significantly
    bollywood_boost = ['bollywood', 'bhangra', 'hindi', 'punjabi', 'indian', 'desi']
    for keyword in bollywood_boost:
        if keyword in name or keyword in tags:
            score += 100  # Major boost for Bollywood/Bhangra
    
    # Boost Indian stations
    if 'india' in country or 'indian' in country:
        score += 50
    
    # Boost priority genres
    for genre in PRIORITY_GENRES:
        if genre in tags:
            score += 25
    
    # Quality boost
    if station.get('bitrate', 0) > 128:
        score += 10
    
    return score

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
    """Get specifically filtered clean stations with Bollywood and Bhangra priority"""
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
        
        # Get Indian stations specifically
        url3 = f"{base_url}/json/stations/bycountry/India?limit=40"
        response3 = requests.get(url3, headers=headers, timeout=10)
        if response3.status_code == 200:
            all_stations.extend(response3.json())
        
        # Search for Bollywood stations
        url4 = f"{base_url}/json/stations/search?name=bollywood&limit=30"
        response4 = requests.get(url4, headers=headers, timeout=10)
        if response4.status_code == 200:
            all_stations.extend(response4.json())
        
        # Search for Bhangra and Hindi stations
        url5 = f"{base_url}/json/stations/search?name=bhangra&limit=20"
        response5 = requests.get(url5, headers=headers, timeout=10)
        if response5.status_code == 200:
            all_stations.extend(response5.json())
        
        # Search for Hindi stations
        url6 = f"{base_url}/json/stations/search?name=hindi&limit=25"
        response6 = requests.get(url6, headers=headers, timeout=10)
        if response6.status_code == 200:
            all_stations.extend(response6.json())
        
        # Get news and talk stations
        url7 = f"{base_url}/json/stations/bytag/news?limit=30"
        response7 = requests.get(url7, headers=headers, timeout=10)
        if response7.status_code == 200:
            all_stations.extend(response7.json())
        
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
                
            # Skip very low quality stations (unless they're Bollywood/Indian)
            is_indian_content = any(keyword in station.get('name', '').lower() + station.get('tags', '').lower() 
                                  for keyword in ['bollywood', 'bhangra', 'hindi', 'punjabi', 'indian'])
            
            if not is_indian_content and station.get('bitrate', 0) < 64 and station.get('votes', 0) < 10:
                continue
            
            # Apply content filtering
            if not is_station_clean(station):
                continue
            
            # Calculate priority score
            priority_score = get_station_priority_score(station)
            
            filtered_station = RadioStation(
                uuid=station.get('stationuuid', ''),
                name=station.get('name', 'Unknown Station'),
                url=station.get('url', ''),
                country=station.get('country', 'Unknown'),
                language=station.get('language', 'Unknown'),
                tags=station.get('tags', ''),
                bitrate=station.get('bitrate', 0),
                votes=priority_score  # Use priority score instead of original votes
            )
            filtered_stations.append(filtered_station)
        
        # Sort by priority score (includes Bollywood/Bhangra boost)
        filtered_stations.sort(key=lambda x: x.votes, reverse=True)
        
        logger.info(f"Fetched {len(filtered_stations)} clean stations with Bollywood/Bhangra priority")
        return filtered_stations[:70]  # Return top 70 stations including Bollywood/Bhangra
        
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

@app.get("/api/stations/bollywood", response_model=List[RadioStation])
async def get_bollywood_stations():
    """Get Bollywood and Bhangra music stations specifically"""
    try:
        base_url = "https://de1.api.radio-browser.info"
        headers = {'User-Agent': 'GlobalRadioApp/1.0'}
        
        all_stations = []
        
        # Search for Bollywood stations
        bollywood_searches = ['bollywood', 'hindi', 'bhangra', 'punjabi', 'indian', 'desi']
        
        for search_term in bollywood_searches:
            url = f"{base_url}/json/stations/search?name={search_term}&limit=20"
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    all_stations.extend(response.json())
            except:
                continue
        
        # Get Indian stations
        try:
            url = f"{base_url}/json/stations/bycountry/India?limit=50"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                all_stations.extend(response.json())
        except:
            pass
        
        # Remove duplicates
        unique_stations = {}
        for station in all_stations:
            uuid = station.get('stationuuid')
            if uuid and uuid not in unique_stations:
                unique_stations[uuid] = station
        
        # Filter and format
        filtered_stations = []
        for station in unique_stations.values():
            if not station.get('url') or not station.get('name'):
                continue
            
            if not is_station_clean(station):
                continue
            
            # Check if it's actually Bollywood/Indian content
            name = station.get('name', '').lower()
            tags = station.get('tags', '').lower()
            country = station.get('country', '').lower()
            
            is_bollywood = any(keyword in name + tags + country 
                             for keyword in ['bollywood', 'bhangra', 'hindi', 'punjabi', 'indian', 'desi', 'filmi'])
            
            if is_bollywood or 'india' in country:
                priority_score = get_station_priority_score(station)
                
                filtered_station = RadioStation(
                    uuid=station.get('stationuuid', ''),
                    name=station.get('name', 'Unknown Station'),
                    url=station.get('url', ''),
                    country=station.get('country', 'Unknown'),
                    language=station.get('language', 'Unknown'),
                    tags=station.get('tags', ''),
                    bitrate=station.get('bitrate', 0),
                    votes=priority_score
                )
                filtered_stations.append(filtered_station)
        
        # Sort by priority score
        filtered_stations.sort(key=lambda x: x.votes, reverse=True)
        
        logger.info(f"Found {len(filtered_stations)} Bollywood/Bhangra stations")
        return filtered_stations[:30]
        
    except Exception as e:
        logger.error(f"Error fetching Bollywood stations: {e}")
        return []

@app.get("/api/stations/search")
async def search_stations(query: str = "", country: str = "", limit: int = 30):
    """Search radio stations by name, country, or frequency"""
    try:
        base_url = "https://de1.api.radio-browser.info"
        headers = {'User-Agent': 'GlobalRadioApp/1.0'}
        
        # Check if query contains frequency pattern
        frequency_pattern = r'(\d{2,3}\.?\d*)\s*(fm|am|khz|mhz)?'
        is_frequency_search = bool(re.search(frequency_pattern, query.lower())) if query else False
        
        # Check for Bollywood/Bhangra search terms
        bollywood_terms = ['bollywood', 'bhangra', 'hindi', 'punjabi', 'indian', 'desi']
        is_bollywood_search = any(term in query.lower() for term in bollywood_terms) if query else False
        
        # Check for Beatles/Classic Rock search terms
        beatles_terms = ['beatles', 'classic rock', '60s', '70s', 'rock']
        is_beatles_search = any(term in query.lower() for term in beatles_terms) if query else False
        
        if is_bollywood_search:
            # Redirect to Bollywood endpoint for better results
            return await get_bollywood_stations()
        elif is_beatles_search:
            # Special handling for Beatles and classic rock
            all_stations = []
            
            # Search for Beatles specifically
            if 'beatles' in query.lower():
                url = f"{base_url}/json/stations/search?name=beatles&limit=20"
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        all_stations.extend(response.json())
                except:
                    pass
            
            # Search for classic rock
            classic_rock_terms = ['classic rock', 'oldies', '60s', '70s', 'rock']
            for term in classic_rock_terms:
                if term in query.lower():
                    url = f"{base_url}/json/stations/search?tag={term.replace(' ', '%20')}&limit=15"
                    try:
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            all_stations.extend(response.json())
                    except:
                        continue
            
            # Also search by name for better coverage
            url = f"{base_url}/json/stations/search?name={query}&limit=20"
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    all_stations.extend(response.json())
            except:
                pass
            
            # Remove duplicates
            unique_stations = {}
            for station in all_stations:
                uuid = station.get('stationuuid')
                if uuid and uuid not in unique_stations:
                    unique_stations[uuid] = station
            
            stations_data = list(unique_stations.values())
            
        elif is_frequency_search:
            # For frequency searches, get more stations and filter locally
            url = f"{base_url}/json/stations/topvote?limit=200"
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            stations_data = response.json()
        elif query:
            # Search by name
            url = f"{base_url}/json/stations/byname/{query}?limit={limit*2}"
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            stations_data = response.json()
        elif country:
            # Search by country
            url = f"{base_url}/json/stations/bycountry/{country}?limit={limit*2}"
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            stations_data = response.json()
        else:
            # Get popular clean stations
            return await get_clean_stations()
        
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
            
            priority_score = get_station_priority_score(station)
                
            filtered_station = RadioStation(
                uuid=station.get('stationuuid', ''),
                name=station.get('name', 'Unknown Station'),
                url=station.get('url', ''),
                country=station.get('country', 'Unknown'),
                language=station.get('language', 'Unknown'),
                tags=station.get('tags', ''),
                bitrate=station.get('bitrate', 0),
                votes=priority_score
            )
            filtered_stations.append(filtered_station)
        
        # Sort by priority score and limit results
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