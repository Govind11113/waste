import { useState } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import { toast } from 'react-hot-toast';

function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/login`,
      });
      if (error) throw error;
      setSent(true);
      toast.success('Password reset email sent! Check your inbox.');
    } catch (error) {
      toast.error(error.message || 'Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface flex">
      <div className="hidden lg:flex lg:w-7/12 relative bg-surface-dim items-center justify-center p-12">
        <div className="relative z-10 max-w-xl">
          <h1 className="font-display text-5xl font-extrabold text-on-surface mb-6">
            Reset Your <span className="text-primary">Password</span>
          </h1>
          <p className="text-on-surface-variant text-lg">
            Enter your email to receive a password reset link.
          </p>
        </div>
      </div>

      <div className="w-full lg:w-5/12 bg-surface-container-lowest flex flex-col justify-center px-8 md:px-16 lg:px-24">
        <div className="max-w-md w-full mx-auto">
          <div className="mb-12">
            <div className="flex items-center space-x-3 mb-10">
              <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
                <span className="material-symbols-outlined text-on-primary text-2xl">spa</span>
              </div>
              <span className="text-2xl font-bold tracking-tight text-on-surface">E‑Waste Management</span>
            </div>
            <h2 className="font-display text-3xl font-bold text-on-surface mb-2">
              Forgot Password
            </h2>
            <p className="text-on-surface-variant">
              {sent ? 'Check your email for the reset link.' : 'Enter your email to reset your password.'}
            </p>
          </div>

          {!sent ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-semibold text-on-surface-variant mb-2">
                  Email address
                </label>
                <input
                  className="w-full bg-surface-container-low border-b-2 border-transparent border-b-outline-variant focus:border-b-primary focus:ring-0 transition-all px-0 py-3 text-on-surface placeholder:text-outline/50"
                  type="email"
                  placeholder="name@institution.org"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary hover:bg-primary-container text-on-primary font-bold py-4 rounded-xl shadow-lg shadow-primary/10 transition-all disabled:opacity-50"
              >
                {loading ? 'Sending...' : 'Send Reset Link'}
              </button>
            </form>
          ) : (
            <div className="bg-primary-container text-on-primary-container p-4 rounded-lg mb-6">
              Password reset email sent! Check your inbox and follow the link to reset your password.
            </div>
          )}

          <footer className="mt-10 text-center">
            <Link to="/login" className="text-primary font-bold hover:underline">
              ← Back to Sign In
            </Link>
          </footer>
        </div>
      </div>
    </div>
  );
}

export default ForgotPassword;
