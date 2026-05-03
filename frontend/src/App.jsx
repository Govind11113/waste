import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider } from './context/ThemeContext';
import TopNavBar from './components/TopNavBar';
import Footer from './components/Footer';
import Home from './components/Home';
import Dashboard from './components/Dashboard';
import Scanner from './components/Scanner';
import LifespanPredictor from './components/LifespanPredictor';
import Inventory from './components/Inventory';
import History from './components/History';
import Signup from './components/Signup';
import Login from './components/Login';
import ForgotPassword from './components/ForgotPassword';

function App() {
  return (
    <ThemeProvider>
      <Toaster position="top-right" />
      <Router>
        <div className="min-h-screen bg-surface-container-lowest text-on-surface">
          <TopNavBar />
          <main>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/scanner" element={<Scanner />} />
              <Route path="/lifespan" element={<LifespanPredictor />} />
              <Route path="/inventory" element={<Inventory />} />
              <Route path="/history" element={<History />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/login" element={<Login />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
