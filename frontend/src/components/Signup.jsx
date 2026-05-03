import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { supabase } from '../utils/supabase';

function SignUp() {
  const [step, setStep] = useState('email'); // 'email' or 'otp'
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    otp: ''
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const navigate = useNavigate();

  const handleEmailSubmit = async () => {
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const { error } = await supabase.auth.signInWithOtp({
        email: formData.email,
        options: {
          create_user: true,
          data: {
            full_name: formData.fullName
          }
        }
      });

      if (error) throw error;

      setMessage({ type: 'success', text: 'OTP sent to your email' });
      setStep('otp');
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Error sending OTP' });
    } finally {
      setLoading(false);
    }
  };

  const handleOTPSubmit = async () => {
    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      const { error } = await supabase.auth.verifyOtp({
        email: formData.email,
        token: formData.otp,
        type: 'email'
      });

      if (error) throw error;

      setMessage({ type: 'success', text: 'Email verified successfully!' });
      setTimeout(() => navigate('/dashboard'), 2000);
    } catch (error) {
      setMessage({ type: 'error', text: 'Invalid OTP' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex">
      {/* Left side visual narrative remains unchanged */}
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
            <span className="material-symbols-outlined text-primary mr-2" style={{fontVariationSettings: "'FILL' 1"}}>eco</span>
            <span className="text-xs font-bold tracking-widest uppercase font-headline text-primary">Sustainability First</span>
          </div>
          <h1 className="font-display text-5xl md:text-6xl font-extrabold text-on-surface leading-tight tracking-tight mb-6">
            Preserving the <span className="text-primary">Ecosystem</span> through Digital Intelligence.
          </h1>
          <p className="text-on-surface-variant text-lg leading-relaxed max-w-lg">
            Join E‑Waste Management in redefining electronic lifecycles. Our conservatory approach treats every component with clinical precision and ecological care.
          </p>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="w-full lg:w-5/12 bg-surface-container-lowest flex flex-col justify-center px-8 md:px-16 lg:px-24">
        <div className="max-w-md w-full mx-auto">
          <div className="mb-12">
            <div className="flex items-center space-x-3 mb-10">
              <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                <span className="material-symbols-outlined text-on-primary text-2xl" style={{fontVariationSettings: "'FILL' 1"}}>spa</span>
              </div>
              <span className="text-2xl font-bold font-headline tracking-tight text-on-surface">E‑Waste Management</span>
            </div>
            <h2 className="font-display text-3xl font-bold text-on-surface mb-2">
              {step === 'email' ? 'Sign Up' : 'Verify Email'}
            </h2>
            <p className="text-on-surface-variant font-body">
              {step === 'email'
                ? 'Register your institution to begin life-cycle predictions.'
                : `Enter the code sent to ${formData.email}`}
            </p>
          </div>

          {message.text && (
            <div className={`mb-6 p-4 rounded-lg ${message.type === 'error' ? 'bg-error-container text-on-error-container' : 'bg-primary-container text-on-primary-container'}`}>
              {message.text}
            </div>
          )}

          {step === 'email' && (
            <form className="space-y-6" onSubmit={(e) => {
              e.preventDefault();
              handleEmailSubmit();
            }}>
              <div>
                <label className="block text-sm font-semibold text-on-surface-variant mb-2 font-label" htmlFor="fullName">
                  Full Name
                </label>
                <input
                  className="w-full bg-surface-container-low border-b-2 border-transparent border-b-outline-variant focus:border-b-primary focus:ring-0 transition-all px-0 py-3 text-on-surface placeholder:text-outline/50 font-body"
                  id="fullName"
                  name="fullName"
                  type="text"
                  placeholder="Dr. Julian Reed"
                  value={formData.fullName}
                  onChange={(e) => setFormData({...formData, fullName: e.target.value})}
                  required
                  minLength={3}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-on-surface-variant mb-2 font-label" htmlFor="email">
                  Institutional Email
                </label>
                <input
                  className="w-full bg-surface-container-low border-b-2 border-transparent border-b-outline-variant focus:border-b-primary focus:ring-0 transition-all px-0 py-3 text-on-surface placeholder:text-outline/50 font-body"
                  id="email"
                  name="email"
                  type="email"
                  placeholder="research@institution.edu"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  required
                />
              </div>

              <div className="pt-4">
                <button
                  type="submit"
                  disabled={loading || !formData.fullName || !formData.email}
                  className="w-full bg-primary hover:bg-primary-container text-on-primary font-bold py-4 rounded-xl shadow-lg shadow-primary/10 transition-all duration-200 flex items-center justify-center group disabled:opacity-50"
                >
                  <span>{loading ? 'Sending OTP...' : 'Send OTP'}</span>
                  {!loading && <span className="material-symbols-outlined ml-2 text-xl group-hover:translate-x-1 transition-transform">arrow_forward</span>}
                </button>
              </div>
            </form>
          )}

          {step === 'otp' && (
            <form className="space-y-6" onSubmit={(e) => {
              e.preventDefault();
              handleOTPSubmit();
            }}>
              <div>
                <label className="block text-sm font-semibold text-on-surface-variant mb-2 font-label" htmlFor="otp">
                  OTP
                </label>
                <input
                  className="w-full bg-surface-container-low border-b-2 border-transparent border-b-outline-variant focus:border-b-primary focus:ring-0 transition-all px-0 py-3 text-on-surface placeholder:text-outline/50 font-body text-center text-2xl tracking-widest"
                  id="otp"
                  name="otp"
                  type="text"
                  placeholder="------"
                  value={formData.otp}
                  onChange={(e) => setFormData({...formData, otp: e.target.value})}
                  required
                  maxLength={6}
                />
                <p className="text-xs text-on-surface-variant mt-2 text-center">
                  Didn't receive the code? <button type="button" onClick={handleEmailSubmit} className="text-primary font-semibold hover:underline">Resend OTP</button>
                </p>
              </div>

              <div className="pt-4">
                <button
                  type="submit"
                  disabled={loading || formData.otp.length < 6}
                  className="w-full bg-primary hover:bg-primary-container text-on-primary font-bold py-4 rounded-xl shadow-lg shadow-primary/10 transition-all duration-200 flex items-center justify-center group disabled:opacity-50"
                >
                  <span>{loading ? 'Verifying...' : 'Verify OTP'}</span>
                  {!loading && <span className="material-symbols-outlined ml-2 text-xl group-hover:translate-x-1 transition-transform">check</span>}
                </button>
              </div>
            </form>
          )}

          <footer className="mt-10 text-center">
            <p className="text-on-surface-variant font-body">
              Already have an account? {' '}
              <Link to="/login" className="text-primary font-bold hover:underline decoration-2 underline-offset-4">
                Sign In
              </Link>
            </p>
          </footer>

          <div className="mt-16 pt-8 border-t border-outline-variant/10 flex items-center justify-center text-outline/60 space-x-6">
            <div className="flex items-center space-x-1">
              <span className="material-symbols-outlined text-sm">lock</span>
              <span className="text-[10px] uppercase tracking-widest font-bold">Encrypted</span>
            </div>
            <div className="flex items-center space-x-1">
              <span className="material-symbols-outlined text-sm">verified_user</span>
              <span className="text-[10px] uppercase tracking-widest font-bold">Institutional Grade</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SignUp;