import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const { error, data } = await supabase.auth.signInWithPassword({
        email: email,
        password: password
      });

      if (error) {
        setMessage({ type: 'error', text: error.message || 'Login failed' });
      } else {
        setMessage({ type: 'success', text: 'Logged in successfully! Redirecting to dashboard...' });
        setTimeout(() => navigate('/dashboard'), 2000);
      }
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Invalid email or password' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex">
      {/* Left Side - Visual Narrative */}
      <div className="hidden lg:flex lg:w-7/12 relative bg-surface-dim items-center justify-center p-12">
        <div className="absolute inset-0 z-0">
          <img
            alt="Digital Conservatory"
            className="w-full h-full object-cover"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuB1nueEgLJHI53uu4fn4UOMb1oVewG9JXKAtPSbUy9lyiQWH8reKlGbwEdmirf3XfDGDMs4HPofxhGUMkh2A-7MuLEjsemE_1D9odxh-pylGS3PtZIg8uNe4kGW8-HTN6JQA1tqJ4mBly3-wJJfbqBwdD2Dgyi_ejEV30U7AmvudxsI4jcMozs101rLIEHyQ93xnQAftPluq67qUXIOs2ElDDFCp_5Rho8socwcneXpBxbB0IXN4QUeU-J9uDuzAghLrszGNOZFhJw"
          />
          <div className="absolute inset-0 bg-gradient-to-tr from-surface/40 to-transparent"></div>
        </div>
        <div className="relative z-10 max-w-xl">
          <div className="mb-8 inline-flex items-center px-4 py-2 rounded-full glass-panel border border-outline-variant/20 shadow-sm">
            <span className="material-symbols-outlined text-primary mr-2" style="fontVariationSettings: 'FILL' 1;">spa</span>
            <span className="text-xs font-bold tracking-widest uppercase font-headline text-primary">Sustainability First</span>
          </div>
          <h1 className="font-display text-5xl md:text-6xl font-extrabold text-on-surface leading-tight mb-6">
            Preserving the <span className="text-primary">Ecosystem</span> through Digital Intelligence.
          </h1>
          <p className="text-on-surface-variant text-lg leading-relaxed max-w-lg">
            Join E‑Waste Management in redefining electronic lifecycles. Our conservatory approach treats every component with clinical precision and ecological care.
          </p>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-5/12 bg-surface-container-lowest flex flex-col justify-center px-8 md:px-16 lg:px-24">
        <div className="max-w-md w-full mx-auto">
          {/* Branding Header */}
          <div className="mb-12">
            <div className="flex items-center space-x-3 mb-10">
              <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                <span className="material-symbols-outlined text-on-primary text-2xl" style="fontVariationSettings: 'FILL' 1;">spa</span>
              </div>
              <span className="text-2xl font-bold font-headline tracking-tight text-on-surface">E‑Waste Management</span>
            </div>
            <h2 className="font-display text-3xl font-bold text-on-surface mb-2">
              Login
            </h2>
            <p className="text-on-surface-variant font-body">Access your Digital Conservatory dashboard.</p>
          </div>

          {/* Message Display */}
          {message.text && (
            <div className={`mb-6 p-4 rounded-lg ${message.type === 'error' ? 'bg-error-container text-on-error-container' : 'bg-primary-container text-on-primary-container'}`}>
              {message.text}
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-on-surface-variant mb-2 font-label" htmlFor="email">
                Email address
              </label>
              <input
                className="w-full bg-surface-container-low border-b-2 border-transparent border-b-outline-variant focus:border-b-primary focus:ring-0 transition-all px-0 py-3 text-on-surface placeholder:text-outline/50 font-body"
                id="email"
                name="email"
                type="email"
                placeholder="name@institution.org"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-on-surface-variant mb-2 font-label" htmlFor="password">
                Password
              </label>
              <input
                className="w-full bg-surface-container-low border-b-2 border-transparent border-b-outline-variant focus:border-b-primary focus:ring-0 transition-all px-0 py-3 text-on-surface placeholder:text-outline/50 font-body"
                id="password"
                name="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength="6"
              />
            </div>

            <div className="pt-4">
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary hover:bg-primary-container text-on-primary font-bold py-4 rounded-xl shadow-lg shadow-primary/10 transition-all duration-200 flex items-center justify-center group disabled:opacity-50"
              >
                <span>{loading ? 'Logging in...' : 'Sign In'}</span>
                {!loading && <span className="material-symbols-outlined ml-2 text-xl group-hover:translate-x-1 transition-transform">arrow_forward</span>}
              </button>
            </div>
          </form>

          {/* Footer Actions */}
          <footer className="mt-10 text-center">
            <p className="text-on-surface-variant font-body">
              New to E‑Waste Management?<br/>
              <Link to="/signup" className="text-primary font-bold hover:underline decoration-2 underline-offset-4 ml-1">
                Create an account
              </Link>
            </p>
          </footer>
        </div>
      </div>
    </div>
  );
}

export default Login;