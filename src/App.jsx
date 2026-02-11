import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SharpPicksApp from './pages/SharpPicksApp';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/*" element={<SharpPicksApp />} />
      </Routes>
    </Router>
  );
}

export default App;
