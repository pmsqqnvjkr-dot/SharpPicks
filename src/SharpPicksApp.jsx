import TrustBanner from './components/TrustBanner';
import TodaysPicks from './components/TodaysPicks';
import ModelTransparency from './components/ModelTransparency';
import { Link } from 'react-router-dom';

export default function SharpPicksApp() {
  return (
    <div className="app">
      <header>
        <div className="header-content">
          <Link to="/" style={{ textDecoration: 'none' }}>
            <h1>Sharp Picks</h1>
          </Link>
          <p>NBA Betting Analysis Dashboard</p>
        </div>
      </header>

      <TrustBanner />

      <main className="container">
        <TodaysPicks />
        <ModelTransparency />
      </main>

      <footer>
        <p>Sharp Picks - ML-Powered NBA Betting Analysis</p>
        <p className="disclaimer">For educational purposes only. Please bet responsibly.</p>
      </footer>
    </div>
  );
}
