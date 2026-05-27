import { useState, useEffect } from 'react'
import { SignUp, useClerk } from '@clerk/clerk-react'
import { clerkAppearance } from '../config/clerkAppearance'

function Signup() {
  const { loaded } = useClerk()
  const [showContent, setShowContent] = useState(false)

  useEffect(() => {
    if (loaded) {
      const timer = setTimeout(() => setShowContent(true), 100)
      return () => clearTimeout(timer)
    }
  }, [loaded])

  return (
    <div className="min-h-screen bg-surface flex page-transition">
      <div className="hidden lg:flex lg:w-7/12 relative bg-surface-dim items-center justify-center p-12 overflow-hidden group">
        <div className="absolute inset-0 z-0">
          <img
            alt="Digital Conservatory"
            className="w-full h-full object-cover img-zoom"
            src="https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?q=80&w=1470&auto=format&fit=crop"
          />
          <div className="absolute inset-0 bg-gradient-to-tr from-surface/60 via-surface/20 to-transparent"></div>
        </div>
        <div className={`relative z-10 max-w-xl transition-all duration-700 ${showContent ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-8'}`}>
          <div className="mb-8 inline-flex items-center px-4 py-2 rounded-full glass-panel border border-outline-variant/20 shadow-sm hover:shadow-md transition-shadow duration-300">
            <span className="material-symbols-outlined text-primary mr-2" style={{fontVariationSettings: "'FILL' 1"}}>eco</span>
            <span className="text-xs font-bold tracking-widest uppercase font-headline text-primary">Sustainability First</span>
          </div>
          <h1 className="font-display text-5xl md:text-6xl font-extrabold text-on-surface leading-tight tracking-tight mb-6">
            Preserving the <span className="text-primary">Ecosystem</span> through Digital Intelligence.
          </h1>
          <p className="text-on-surface-variant text-lg leading-relaxed max-w-lg">
            Join E-Waste Management in redefining electronic lifecycles. Our conservatory approach treats every component with clinical precision and ecological care.
          </p>
        </div>
      </div>

      <div className="w-full lg:w-5/12 bg-surface-container-lowest flex flex-col justify-center px-6 sm:px-12 lg:px-20 relative">
        <div className={`max-w-md w-full mx-auto transition-all duration-500 ${showContent ? 'opacity-0 scale-95 absolute pointer-events-none' : 'opacity-100 scale-100'}`}>
          <div className="mb-8">
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-10 h-10 bg-primary rounded-xl animate-pulse-slow"></div>
              <div className="skeleton-loader h-8 w-48"></div>
            </div>
            <div className="skeleton-loader h-6 w-32 mb-2"></div>
            <div className="skeleton-loader h-4 w-56"></div>
          </div>
          <div className="space-y-4">
            <div className="skeleton-loader h-12 rounded-xl"></div>
            <div className="skeleton-loader h-12 rounded-xl"></div>
            <div className="skeleton-loader h-12 rounded-xl"></div>
            <div className="skeleton-loader h-12 rounded-xl"></div>
          </div>
        </div>

        <div className={`max-w-md w-full mx-auto transition-all duration-600 ease-out ${showContent ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-6 scale-95 absolute pointer-events-none'}`}>
          <div className="mb-8 animate-fade-in-down">
            <div className="flex items-center space-x-3 mb-6 group cursor-pointer">
              <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center transition-transform duration-300 group-hover:scale-110">
                <span className="material-symbols-outlined text-on-primary text-2xl" style={{fontVariationSettings: "'FILL' 1"}}>spa</span>
              </div>
              <span className="text-2xl font-bold font-headline tracking-tight text-on-surface">E-Waste Management</span>
            </div>
            <h2 className="font-display text-3xl font-bold text-on-surface mb-2">Create Account</h2>
            <p className="text-on-surface-variant font-body">Register your institution to begin life-cycle predictions.</p>
          </div>

          <SignUp
            routing="path"
            path="/signup"
            signInUrl="/login"
            forceRedirectUrl="/dashboard"
            fallbackRedirectUrl="/dashboard"
            appearance={clerkAppearance}
          />

          <div className="mt-16 pt-8 border-t border-outline-variant/10 flex items-center justify-center text-outline/60 space-x-6 animate-fade-in-up">
            <div className="flex items-center space-x-1 hover:text-primary transition-colors duration-300">
              <span className="material-symbols-outlined text-sm">lock</span>
              <span className="text-[10px] uppercase tracking-widest font-bold">Encrypted</span>
            </div>
            <div className="flex items-center space-x-1 hover:text-primary transition-colors duration-300">
              <span className="material-symbols-outlined text-sm">verified_user</span>
              <span className="text-[10px] uppercase tracking-widest font-bold">Institutional Grade</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Signup
