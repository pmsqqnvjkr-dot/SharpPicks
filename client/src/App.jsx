import { useState, useEffect } from 'react';
import TrustBanner from './components/TrustBanner';
import StatsCard from './components/StatsCard';
import CalibrationChart from './components/CalibrationChart';
import './App.css';

function App() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/admin/stats')
      .then(r => r.json())
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error:', err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="app">
      <header>
        <div className="header-content">
          <h1>🏀 Sharp Picks</h1>
          <p>NBA Betting Analysis Dashboard</p>
        </div>
        <TrustBanner />
      </header>

      <main className="container">
        {loading ? (
          <div className="loading-state">Loading dashboard...</div>
        ) : (
          <>
            <section className="stats-grid">
              <StatsCard 
                icon="📊" 
                label="Games Collected" 
                value={stats?.gamesCollected?.toLocaleString() || '—'}
                color="#3B82F6"
                subtext="Total in database"
              />
              <StatsCard 
                icon="✅" 
                label="With Results" 
                value={stats?.gamesWithResults?.toLocaleString() || '—'}
                color="#10B981"
                subtext="Games resolved"
              />
              <StatsCard 
                icon="🎯" 
                label="Model Accuracy" 
                value={`${stats?.modelAccuracy || 79.4}%`}
                color="#6366F1"
                subtext="On test data"
              />
              <StatsCard 
                icon="📈" 
                label="Brier Score" 
                value={stats?.modelBrier || 0.139}
                color="#F59E0B"
                subtext="Lower is better"
              />
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

              <CalibrationChart />
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
          </>
        )}
      </main>

      <footer>
        <p>Sharp Picks - ML-Powered NBA Betting Analysis</p>
        <p className="disclaimer">For educational purposes only. Please bet responsibly.</p>
      </footer>
    </div>
  );
}

export default App;
