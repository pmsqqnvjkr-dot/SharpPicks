import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import SharpPicksApp from './SharpPicksApp';
import AnalyticsDashboard from './AnalyticsDashboard';
import SharpPicksBestOfBoth from './SharpPicksBestOfBoth';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/app" element={<SharpPicksApp />} />
        <Route path="/analytics" element={<AnalyticsDashboard />} />
        <Route path="/premium" element={<SharpPicksBestOfBoth />} />
      </Routes>
    </Router>
  );
}

function HomePage() {
  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center', 
      fontFamily: 'system-ui' 
    }}>
      <div style={{ textAlign: 'center' }}>
        <h1 style={{ 
          color: '#fff', 
          fontSize: '48px', 
          marginBottom: '16px', 
          fontWeight: '900',
          background: 'linear-gradient(135deg, #3B82F6, #6366F1)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>
          Sharp Picks
        </h1>
        <p style={{ color: '#94A3B8', marginBottom: '48px', fontSize: '18px' }}>
          ML-Powered NBA Betting Analysis
        </p>
        <div style={{ display: 'flex', gap: '24px', flexDirection: 'column', maxWidth: '400px', margin: '0 auto' }}>
          <Link 
            to="/app" 
            style={{ 
              background: 'linear-gradient(135deg, #3b82f6, #6366f1)', 
              color: '#fff', 
              padding: '24px 48px', 
              borderRadius: '16px', 
              textDecoration: 'none', 
              fontSize: '20px', 
              fontWeight: 'bold',
              transition: 'transform 0.2s',
              display: 'block'
            }}
          >
            🎯 Today's Picks
          </Link>
          <Link 
            to="/analytics" 
            style={{ 
              background: 'linear-gradient(135deg, #10b981, #059669)', 
              color: '#fff', 
              padding: '24px 48px', 
              borderRadius: '16px', 
              textDecoration: 'none', 
              fontSize: '20px', 
              fontWeight: 'bold',
              transition: 'transform 0.2s',
              display: 'block'
            }}
          >
            📊 Analytics Dashboard
          </Link>
          <Link 
            to="/premium" 
            style={{ 
              background: 'linear-gradient(135deg, #f59e0b, #d97706)', 
              color: '#fff', 
              padding: '24px 48px', 
              borderRadius: '16px', 
              textDecoration: 'none', 
              fontSize: '20px', 
              fontWeight: 'bold',
              transition: 'transform 0.2s',
              display: 'block'
            }}
          >
            👑 Premium Experience
          </Link>
        </div>
        <div style={{ marginTop: '64px', color: '#64748B', fontSize: '14px' }}>
          <p>79.5% Model Accuracy • 15,000+ Games Analyzed • Calibrated Predictions</p>
        </div>
      </div>
    </div>
  );
}

export default App;
