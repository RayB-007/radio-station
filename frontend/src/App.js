import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Volume2, VolumeX, Globe, Radio } from 'lucide-react';
import { Button } from './components/ui/button';
import { Card, CardContent } from './components/ui/card';
import { Input } from './components/ui/input';
import { Badge } from './components/ui/badge';
import './App.css';

const App = () => {
  const [stations, setStations] = useState([]);
  const [currentStation, setCurrentStation] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [volume, setVolume] = useState(0.7);
  const [isMuted, setIsMuted] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const audioRef = useRef(null);

  useEffect(() => {
    fetchStations();
  }, []);

  const fetchStations = async () => {
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
      const response = await fetch(`${backendUrl}/api/stations`);
      const data = await response.json();
      setStations(data.slice(0, 50)); // Limit to 50 stations for performance
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching stations:', error);
      setIsLoading(false);
    }
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

  const filteredStations = stations.filter(station =>
    station.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    station.country.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="app-container">
      <audio
        ref={audioRef}
        onError={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
      />
      
      {/* Globe Background */}
      <div className="globe-container">
        <div className="globe">
          <div className="globe-sphere">
            <div className="globe-shine"></div>
          </div>
          <div className="globe-rings">
            <div className="ring ring-1"></div>
            <div className="ring ring-2"></div>
            <div className="ring ring-3"></div>
          </div>
        </div>
        
        <div className="floating-elements">
          <div className="radio-wave wave-1"></div>
          <div className="radio-wave wave-2"></div>
          <div className="radio-wave wave-3"></div>
        </div>
      </div>

      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="logo">
            <Globe className="logo-icon" />
            <h1>Global Radio</h1>
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
          <Input
            type="text"
            placeholder="Search stations or countries..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="stations-list">
          {isLoading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Loading radio stations...</p>
            </div>
          ) : (
            filteredStations.map((station) => (
              <Card key={station.uuid} className="station-card">
                <CardContent className="station-content">
                  <div className="station-info">
                    <div className="station-main">
                      <h3 className="station-name">{station.name}</h3>
                      <div className="station-meta">
                        <Badge variant="secondary" className="country-badge">
                          {station.country}
                        </Badge>
                        {station.tags && (
                          <span className="station-genre">{station.tags.split(',')[0]}</span>
                        )}
                      </div>
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
            ))
          )}
        </div>

        {/* Current Playing & Controls */}
        {currentStation && (
          <div className="player-controls">
            <div className="now-playing">
              <div className="playing-info">
                <h4>Now Playing</h4>
                <p>{currentStation.name}</p>
                <span>{currentStation.country}</span>
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
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;