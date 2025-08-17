import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Volume2, VolumeX, Globe, Radio, Search } from 'lucide-react';
import { Button } from './components/ui/button';
import { Card, CardContent } from './components/ui/card';
import { Input } from './components/ui/input';
import { Badge } from './components/ui/badge';
import './App.css';

const App = () => {
  const [stations, setStations] = useState([]);
  const [allStations, setAllStations] = useState([]);
  const [currentStation, setCurrentStation] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [volume, setVolume] = useState(0.7);
  const [isMuted, setIsMuted] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    fetchStations();
  }, []);

  // Debounced search effect
  useEffect(() => {
    if (searchTerm.trim()) {
      const timeoutId = setTimeout(() => {
        performSearch(searchTerm);
      }, 500); // 500ms delay
      return () => clearTimeout(timeoutId);
    } else {
      // Reset to all stations when search is cleared
      setStations(allStations);
      setIsSearching(false);
    }
  }, [searchTerm, allStations]);

  const fetchStations = async () => {
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
      const response = await fetch(`${backendUrl}/api/stations/clean`);
      const data = await response.json();
      setAllStations(data);
      setStations(data);
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching stations:', error);
      setIsLoading(false);
    }
  };

  const performSearch = async (query) => {
    setIsSearching(true);
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
      const response = await fetch(`${backendUrl}/api/stations/search?query=${encodeURIComponent(query)}`);
      const data = await response.json();
      setStations(data);
    } catch (error) {
      console.error('Error searching stations:', error);
      // Fallback to client-side filtering
      const filtered = allStations.filter(station =>
        station.name.toLowerCase().includes(query.toLowerCase()) ||
        station.country.toLowerCase().includes(query.toLowerCase()) ||
        (station.tags && station.tags.toLowerCase().includes(query.toLowerCase()))
      );
      setStations(filtered);
    }
    setIsSearching(false);
  };

  const playStation = async (station) => {
    if (currentStation?.uuid === station.uuid && isPlaying) {
      // Pause current station
      audioRef.current?.pause();
      setIsPlaying(false);
      return;
    }

    try {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      
      setCurrentStation(station);
      setIsPlaying(true);
      
      // Use backend proxy for CORS handling
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
      const proxyUrl = `${backendUrl}/api/stream/${encodeURIComponent(station.url)}`;
      
      audioRef.current.src = proxyUrl;
      audioRef.current.volume = isMuted ? 0 : volume;
      await audioRef.current.play();
    } catch (error) {
      console.error('Error playing station:', error);
      setIsPlaying(false);
    }
  };

  const toggleMute = () => {
    if (audioRef.current) {
      if (isMuted) {
        audioRef.current.volume = volume;
        setIsMuted(false);
      } else {
        audioRef.current.volume = 0;
        setIsMuted(true);
      }
    }
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current && !isMuted) {
      audioRef.current.volume = newVolume;
    }
  };

  // Enhanced search to include frequency matching
  const filteredStations = stations; // Now using API search instead of client-side filtering

  return (
    <div className="app-container">
      <audio
        ref={audioRef}
        onError={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
      />
      
      {/* Earth Globe Background */}
      <div className="earth-container">
        <div className="earth-globe">
          <div className="earth-sphere">
            <div className="continents">
              <div className="continent north-america"></div>
              <div className="continent south-america"></div>
              <div className="continent europe"></div>
              <div className="continent africa"></div>
              <div className="continent asia"></div>
              <div className="continent australia"></div>
            </div>
            <div className="earth-shine"></div>
            <div className="earth-atmosphere"></div>
          </div>
          <div className="orbit-rings">
            <div className="orbit-ring ring-1"></div>
            <div className="orbit-ring ring-2"></div>
            <div className="orbit-ring ring-3"></div>
          </div>
        </div>
        
        <div className="radio-signals">
          <div className="signal signal-1"></div>
          <div className="signal signal-2"></div>
          <div className="signal signal-3"></div>
          <div className="signal signal-4"></div>
        </div>
      </div>

      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <Globe className="logo-icon" />
            <h1>Global Radio</h1>
            <span className="logo-subtitle">Clean Worldwide Stations</span>
          </div>
        </div>
      </header>

      {/* Radio Stations Panel */}
      <div className="stations-panel">
        <div className="panel-header">
          <h2>
            <Radio className="panel-icon" />
            World Radio Stations
          </h2>
          <div className="search-container">
            <Search className="search-icon" />
            <Input
              type="text"
              placeholder="Search stations, countries, frequencies (92.3 FM), or try 'Bollywood', 'Bhangra'..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>
        </div>

        <div className="stations-list">
          {isLoading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Loading clean radio stations...</p>
            </div>
          ) : (
            <>
              <div className="results-info">
                {searchTerm && (
                  <p className="search-results">
                    Found {filteredStations.length} stations 
                    {searchTerm.match(/\d+\.?\d*/) ? ' matching frequency' : ''}
                  </p>
                )}
              </div>
              {filteredStations.map((station) => (
                <Card key={station.uuid} className="station-card">
                  <CardContent className="station-content">
                    <div className="station-info">
                      <div className="station-main">
                        <h3 className="station-name">{station.name}</h3>
                        <div className="station-meta">
                          <Badge variant="secondary" className="country-badge">
                            {station.country}
                          </Badge>
                          {station.language && station.language !== 'Unknown' && (
                            <Badge variant="outline" className="language-badge">
                              {station.language}
                            </Badge>
                          )}
                          {station.tags && (
                            <span className="station-genre">{station.tags.split(',')[0]}</span>
                          )}
                        </div>
                        {station.bitrate > 0 && (
                          <div className="station-quality">
                            <span className="bitrate">{station.bitrate} kbps</span>
                          </div>
                        )}
                      </div>
                      <Button
                        onClick={() => playStation(station)}
                        className={`play-button ${
                          currentStation?.uuid === station.uuid && isPlaying ? 'playing' : ''
                        }`}
                        size="sm"
                      >
                        {currentStation?.uuid === station.uuid && isPlaying ? (
                          <Pause className="button-icon" />
                        ) : (
                          <Play className="button-icon" />
                        )}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {filteredStations.length === 0 && !isLoading && (
                <div className="no-results">
                  <p>No stations found for "{searchTerm}"</p>
                  <p className="help-text">Try searching for:</p>
                  <div className="suggestions">
                    <span>• Countries: "Germany", "India", "USA"</span>
                    <span>• Genres: "Bollywood", "Bhangra", "Jazz", "News"</span>
                    <span>• Frequencies: "92.3 FM", "101.5"</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Current Playing & Controls */}
        {currentStation && (
          <div className="player-controls">
            <div className="now-playing">
              <div className="playing-info">
                <h4>Now Playing</h4>
                <p>{currentStation.name}</p>
                <div className="playing-meta">
                  <span>{currentStation.country}</span>
                  {currentStation.bitrate > 0 && (
                    <span className="quality-indicator">{currentStation.bitrate} kbps</span>
                  )}
                </div>
              </div>
              <div className="volume-controls">
                <Button
                  onClick={toggleMute}
                  variant="ghost"
                  size="sm"
                  className="volume-button"
                >
                  {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
                </Button>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={volume}
                  onChange={handleVolumeChange}
                  className="volume-slider"
                />
                <span className="volume-percent">{Math.round(volume * 100)}%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;