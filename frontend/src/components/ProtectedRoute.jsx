import { SignedIn, SignedOut } from '@clerk/clerk-react'
import { Navigate, useLocation } from 'react-router-dom'

function ProtectedRoute({ children }) {
  const location = useLocation()

  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto text-center min-h-[60vh] flex flex-col items-center justify-center">
          <span className="material-symbols-outlined text-6xl text-primary mb-4">lock</span>
          <h2 className="text-2xl font-bold text-on-surface mb-2">Sign in required</h2>
          <p className="text-on-surface-variant mb-6 max-w-md">
            Please sign in to access this feature. Your data is saved to your account.
          </p>
          <Navigate to="/login" state={{ from: location }} replace />
        </div>
      </SignedOut>
    </>
  )
}

export default ProtectedRoute
