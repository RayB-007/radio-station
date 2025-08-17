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

@app.get("/")
async def root():
    return {"message": "Global Radio API", "status": "running"}

@app.get("/api/stations", response_model=List[RadioStation])
async def get_radio_stations():
    """Fetch popular radio stations from Radio-Browser API"""
    try:
        # Use Radio-Browser API to get popular stations
        base_url = "https://at1.api.radio-browser.info"
        
        # Get top voted stations with good quality
        url = f"{base_url}/json/stations/topvote/100"
        
        headers = {
            'User-Agent': 'GlobalRadioApp/1.0'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        stations_data = response.json()
        
        # Filter and format stations
        filtered_stations = []
        for station in stations_data:
            # Skip stations without proper URL or name
            if not station.get('url') or not station.get('name'):
                continue
                
            # Skip very low quality stations
            if station.get('bitrate', 0) < 64 and station.get('votes', 0) < 10:
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
        
        # Sort by votes and limit to top stations
        filtered_stations.sort(key=lambda x: x.votes, reverse=True)
        
        logger.info(f"Fetched {len(filtered_stations)} radio stations")
        return filtered_stations[:50]  # Return top 50 stations
        
    except requests.RequestException as e:
        logger.error(f"Error fetching stations: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch radio stations")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

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
async def search_stations(query: str = "", country: str = "", limit: int = 20):
    """Search radio stations by name or country"""
    try:
        base_url = "https://at1.api.radio-browser.info"
        headers = {'User-Agent': 'GlobalRadioApp/1.0'}
        
        if query:
            # Search by name
            url = f"{base_url}/json/stations/byname/{query}"
        elif country:
            # Search by country
            url = f"{base_url}/json/stations/bycountry/{country}"
        else:
            # Get popular stations
            url = f"{base_url}/json/stations/topvote/{limit}"
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        stations_data = response.json()
        
        # Format and filter stations
        filtered_stations = []
        for station in stations_data[:limit]:
            if not station.get('url') or not station.get('name'):
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
        
        return filtered_stations
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "global-radio-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)