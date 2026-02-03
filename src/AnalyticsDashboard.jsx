import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

export default function AnalyticsDashboard() {
  const [stats, setStats] = useState(null);
  const [calibration, setCalibration] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/admin/stats').then(r => r.json()),
      fetch('/api/model/calibration').then(r => r.json()),
      fetch('/api/performance').then(r => r.json())
    ])
    .then(([st, cal, perf]) => {
      setStats(st);
      setCalibration(cal);
      setPerformance(perf);
      setLoading(false);
    })
    .catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="app">
        <div className="loading-state">Loading analytics...</div>
      </div>
    );
  }

  return (
    <div className="app">
      <header>
        <div className="header-content">
          <Link to="/" style={{ textDecoration: 'none' }}>
            <h1>Analytics Dashboard</h1>
          </Link>
          <p>Deep Dive into Model Performance</p>
        </div>
      </header>

      <main className="container">
        <section className="stats-grid">
          <div className="stats-card">
            <div className="stats-icon" style={{ background: 'rgba(59, 130, 246, 0.2)' }}>📊</div>
            <div className="stats-content">
              <span className="stats-label">Games Collected</span>
              <span className="stats-value">{stats?.gamesCollected?.toLocaleString() || '—'}</span>
              <span className="stats-subtext">Total in database</span>
            </div>
          </div>
          <div className="stats-card">
            <div className="stats-icon" style={{ background: 'rgba(16, 185, 129, 0.2)' }}>✅</div>
            <div className="stats-content">
              <span className="stats-label">With Results</span>
              <span className="stats-value">{stats?.gamesWithResults?.toLocaleString() || '—'}</span>
              <span className="stats-subtext">Games resolved</span>
            </div>
          </div>
          <div className="stats-card">
            <div className="stats-icon" style={{ background: 'rgba(99, 102, 241, 0.2)' }}>🎯</div>
            <div className="stats-content">
              <span className="stats-label">Model Accuracy</span>
              <span className="stats-value">{stats?.modelAccuracy || 79.4}%</span>
              <span className="stats-subtext">On test data</span>
            </div>
          </div>
          <div className="stats-card">
            <div className="stats-icon" style={{ background: 'rgba(245, 158, 11, 0.2)' }}>📈</div>
            <div className="stats-content">
              <span className="stats-label">Brier Score</span>
              <span className="stats-value">{stats?.modelBrier || 0.139}</span>
              <span className="stats-subtext">Lower is better</span>
            </div>
          </div>
        </section>

        <section className="charts-grid">
          <div className="card spread-stats">
            <h3>Spread Results Distribution</h3>
            <div className="spread-bars">
              <div className="spread-item">
                <span className="spread-label">Home Cover</span>
                <div className="spread-bar-container">
                  <div 
                    className="spread-bar home"
                    style={{ 
                      width: `${(stats?.homeCover / (stats?.homeCover + stats?.awayCover + stats?.pushes) * 100) || 0}%` 
                    }}
                  />
                </div>
                <span className="spread-value">{stats?.homeCover?.toLocaleString() || 0}</span>
              </div>
              <div className="spread-item">
                <span className="spread-label">Away Cover</span>
                <div className="spread-bar-container">
                  <div 
                    className="spread-bar away"
                    style={{ 
                      width: `${(stats?.awayCover / (stats?.homeCover + stats?.awayCover + stats?.pushes) * 100) || 0}%` 
                    }}
                  />
                </div>
                <span className="spread-value">{stats?.awayCover?.toLocaleString() || 0}</span>
              </div>
              <div className="spread-item">
                <span className="spread-label">Push</span>
                <div className="spread-bar-container">
                  <div 
                    className="spread-bar push"
                    style={{ 
                      width: `${(stats?.pushes / (stats?.homeCover + stats?.awayCover + stats?.pushes) * 100) || 0}%` 
                    }}
                  />
                </div>
                <span className="spread-value">{stats?.pushes?.toLocaleString() || 0}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3>Calibration Summary</h3>
            <div style={{ padding: '16px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                <span style={{ color: '#94A3B8' }}>Status</span>
                <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${
                  calibration?.calibration_status === 'excellent' 
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : calibration?.calibration_status === 'good'
                    ? 'bg-blue-50 border-blue-200 text-blue-900'
                    : calibration?.calibration_status === 'moderate'
                    ? 'bg-amber-50 border-amber-200 text-amber-900'
                    : 'bg-red-50 border-red-200 text-red-900'
                }`}>
                  {calibration?.calibration_status?.toUpperCase()}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                <span style={{ color: '#94A3B8' }}>Mean Absolute Error</span>
                <span style={{ fontWeight: 600 }}>{calibration?.mean_absolute_error}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#94A3B8' }}>Total Predictions Tracked</span>
                <span style={{ fontWeight: 600 }}>{calibration?.total_predictions || 0}</span>
              </div>
            </div>
          </div>
        </section>

        <section className="system-health">
          <h3>System Health</h3>
          <div className="health-grid">
            {stats?.systemHealth?.map((item, i) => (
              <div key={i} className={`health-item ${item.status}`}>
                <span className="health-status-dot"></span>
                <div className="health-content">
                  <span className="health-name">{item.name}</span>
                  <span className="health-message">{item.message}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section style={{ marginTop: '32px', textAlign: 'center' }}>
          <Link 
            to="/app" 
            style={{ 
              background: 'linear-gradient(135deg, #3b82f6, #6366f1)', 
              color: '#fff', 
              padding: '16px 32px', 
              borderRadius: '12px', 
              textDecoration: 'none', 
              fontSize: '16px', 
              fontWeight: 'bold',
              display: 'inline-block'
            }}
          >
            View Today's Picks →
          </Link>
        </section>
      </main>

      <footer>
        <p>Sharp Picks - ML-Powered NBA Betting Analysis</p>
        <p className="disclaimer">For educational purposes only. Please bet responsibly.</p>
      </footer>
    </div>
  );
}
