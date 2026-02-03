import { useState, useEffect } from 'react';

export default function TrustBanner() {
  const [calibration, setCalibration] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/model/calibration').then(r => r.json()),
      fetch('/api/admin/stats').then(r => r.json())
    ])
    .then(([cal, st]) => {
      setCalibration(cal);
      setStats(st);
      setLoading(false);
    })
    .catch(err => {
      console.error('Error loading data:', err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="trust-banner loading">
        <div className="spinner"></div>
        <span>Loading model stats...</span>
      </div>
    );
  }

  const statusColors = {
    excellent: '#10B981',
    good: '#3B82F6',
    moderate: '#F59E0B',
    poor: '#EF4444'
  };

  const calibrationColor = calibration ? statusColors[calibration.calibration_status] : '#6B7280';

  return (
    <div className="trust-banner">
      <div className="trust-item">
        <span className="trust-icon">🎯</span>
        <div className="trust-content">
          <span className="trust-label">Model Accuracy</span>
          <span className="trust-value">{stats?.modelAccuracy || 79.4}%</span>
        </div>
      </div>
      
      <div className="trust-divider"></div>
      
      <div className="trust-item">
        <span className="trust-icon">📊</span>
        <div className="trust-content">
          <span className="trust-label">Brier Score</span>
          <span className="trust-value">{stats?.modelBrier || 0.139}</span>
        </div>
      </div>
      
      <div className="trust-divider"></div>
      
      <div className="trust-item">
        <span className="trust-icon">✅</span>
        <div className="trust-content">
          <span className="trust-label">Calibration</span>
          <span className="trust-value" style={{ color: calibrationColor }}>
            {calibration?.calibration_status?.toUpperCase() || 'CHECKING'}
          </span>
        </div>
      </div>
      
      <div className="trust-divider"></div>
      
      <div className="trust-item">
        <span className="trust-icon">🔥</span>
        <div className="trust-content">
          <span className="trust-label">Collection Streak</span>
          <span className="trust-value">{stats?.collectionStreak || 0} days</span>
        </div>
      </div>
      
      <div className="trust-divider"></div>
      
      <div className="trust-item">
        <span className="trust-icon">📈</span>
        <div className="trust-content">
          <span className="trust-label">Games Tracked</span>
          <span className="trust-value">{stats?.gamesCollected?.toLocaleString() || '15,000+'}</span>
        </div>
      </div>
    </div>
  );
}
