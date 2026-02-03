import TrustBanner from './components/TrustBanner';
import TodaysPicks from './components/TodaysPicks';
import ModelTransparency from './components/ModelTransparency';
import './App.css';

function App() {
  return (
    <div className="app">
      <header>
        <div className="header-content">
          <h1>Sharp Picks</h1>
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

export default App;
