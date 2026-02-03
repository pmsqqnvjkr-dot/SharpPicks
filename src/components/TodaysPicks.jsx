import { useState, useEffect } from 'react';

export default function TodaysPicks() {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('strong');

  useEffect(() => {
    fetch('/api/predictions')
      .then(res => res.json())
      .then(data => {
        setPredictions(data.predictions || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const filteredPicks = predictions.filter(p => {
    if (filter === 'all') return true;
    if (filter === 'strong') return p.confidence >= 0.60;
    if (filter === 'medium') return p.confidence >= 0.55 && p.confidence < 0.60;
    return true;
  });

  const formatConfidence = (conf) => `${(conf * 100).toFixed(1)}%`;

  const getConfidenceClass = (conf) => {
    if (conf >= 0.65) return 'very-high';
    if (conf >= 0.60) return 'high';
    if (conf >= 0.55) return 'medium';
    return 'low';
  };

  if (loading) {
    return (
      <div className="picks-section">
        <h2>Today's Picks</h2>
        <div className="loading">Loading predictions...</div>
      </div>
    );
  }

  return (
    <div className="picks-section">
      <div className="picks-header">
        <h2>Today's Picks</h2>
        <div className="filter-buttons">
          <button 
            className={filter === 'strong' ? 'active' : ''} 
            onClick={() => setFilter('strong')}
          >
            Strong (60%+)
          </button>
          <button 
            className={filter === 'medium' ? 'active' : ''} 
            onClick={() => setFilter('medium')}
          >
            Medium (55-60%)
          </button>
          <button 
            className={filter === 'all' ? 'active' : ''} 
            onClick={() => setFilter('all')}
          >
            All
          </button>
        </div>
      </div>

      {filteredPicks.length === 0 ? (
        <div className="no-picks">
          <p>No {filter !== 'all' ? filter : ''} picks available right now.</p>
          <p className="hint">Check back closer to game time for predictions.</p>
        </div>
      ) : (
        <div className="picks-grid">
          {filteredPicks.map((pick, idx) => (
            <div key={idx} className={`pick-card ${getConfidenceClass(pick.confidence)}`}>
              <div className="matchup">
                <span className="away-team">{pick.away_team}</span>
                <span className="at">@</span>
                <span className="home-team">{pick.home_team}</span>
              </div>
              
              <div className="prediction">
                <div className="pick-label">Pick</div>
                <div className="pick-value">{pick.prediction}</div>
                <div className="spread">{pick.spread > 0 ? '+' : ''}{pick.spread}</div>
              </div>

              <div className="confidence-meter">
                <div className="meter-label">Confidence</div>
                <div className="meter-bar">
                  <div 
                    className="meter-fill" 
                    style={{ width: `${pick.confidence * 100}%` }}
                  />
                </div>
                <div className="meter-value">{formatConfidence(pick.confidence)}</div>
              </div>

              {pick.edge && (
                <div className="edge-info">
                  <span className="edge-label">Edge:</span>
                  <span className="edge-value">{pick.edge.toFixed(1)} pts</span>
                </div>
              )}

              {pick.line_movement && pick.line_movement !== 0 && (
                <div className={`line-movement ${pick.line_movement > 0 ? 'up' : 'down'}`}>
                  Line moved {pick.line_movement > 0 ? '+' : ''}{pick.line_movement}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
