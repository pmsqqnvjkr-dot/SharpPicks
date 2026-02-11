import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SharpPicksApp from './pages/SharpPicksApp';
import ResetPassword from './pages/ResetPassword';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/*" element={<SharpPicksApp />} />
      </Routes>
    </Router>
  );
}

export default App;
