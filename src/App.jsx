import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SharpPicksApp from './pages/SharpPicksApp';
import ResetPassword from './pages/ResetPassword';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import Disclaimer from './pages/Disclaimer';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/privacy" element={<PrivacyPolicy />} />
        <Route path="/terms" element={<TermsOfService />} />
        <Route path="/disclaimer" element={<Disclaimer />} />
        <Route path="/*" element={<SharpPicksApp />} />
      </Routes>
    </Router>
  );
}

export default App;
