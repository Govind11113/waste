import { Link, useLocation } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { supabase } from '../supabaseClient';
import DarkModeToggle from './DarkModeToggle';
import { toast } from 'react-hot-toast';
import { useState, useEffect } from 'react';

function TopNavBar() {
  const location = useLocation();
  const currentPath = location.pathname;
  const { darkMode, toggleDarkMode } = useTheme();
  const [user, setUser] = useState(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => setUser(user));
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => setUser(session?.user ?? null)
    );
    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    toast.success('Logged out');
    window.location.href = '/login';
  };

  const isActive = (path) => currentPath === path;

  return (
    <nav className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-xl shadow-[0_24px_24px_0_rgba(0,98,158,0.06)]">
      <div className="max-w-7xl mx-auto px-8 flex justify-between items-center h-20">
        <Link to="/" className="text-2xl font-black tracking-tighter text-primary">
          E-Waste Management
        </Link>

        <div className="hidden md:flex items-center space-x-8 font-manrope text-sm font-semibold tracking-tight">
          <Link to="/" className={`transition-colors hover:opacity-80 duration-300 pb-1 ${isActive('/') ? 'text-secondary border-b-2 border-secondary' : 'text-on-surface-variant'}`}>Home</Link>
          <Link to="/dashboard" className={`transition-colors hover:opacity-80 duration-300 pb-1 ${isActive('/dashboard') ? 'text-secondary border-b-2 border-secondary' : 'text-on-surface-variant'}`}>Dashboard</Link>
          <Link to="/scanner" className={`transition-colors hover:opacity-80 duration-300 pb-1 ${isActive('/scanner') ? 'text-secondary border-b-2 border-secondary' : 'text-on-surface-variant'}`}>Classifier</Link>
          <Link to="/lifespan" className={`transition-colors hover:opacity-80 duration-300 pb-1 ${isActive('/lifespan') ? 'text-secondary border-b-2 border-secondary' : 'text-on-surface-variant'}`}>Lifespan Predictor</Link>
          <Link to="/inventory" className={`transition-colors hover:opacity-80 duration-300 pb-1 ${isActive('/inventory') ? 'text-secondary border-b-2 border-secondary' : 'text-on-surface-variant'}`}>Carbon Calculator</Link>
          <Link to="/history" className={`transition-colors hover:opacity-80 duration-300 pb-1 ${isActive('/history') ? 'text-secondary border-b-2 border-secondary' : 'text-on-surface-variant'}`}>History</Link>
        </div>

        <div className="flex items-center space-x-4">
          <DarkModeToggle />

          {user ? (
            <button onClick={handleLogout} className="bg-error text-on-error px-6 py-2.5 rounded-full font-semibold hover:opacity-80 transition-all duration-300 active:scale-95">
              Logout
            </button>
          ) : (
            <Link to="/login" className="bg-primary text-on-primary px-6 py-2.5 rounded-full font-semibold hover:opacity-80 transition-all duration-300 active:scale-95">
              Login
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}

export default TopNavBar;
