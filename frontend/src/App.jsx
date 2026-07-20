import { lazy, Suspense } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from './context/ThemeContext'
import TopNavBar from './components/TopNavBar'
import Footer from './components/Footer'
import ProtectedRoute from './components/ProtectedRoute'

const Home = lazy(() => import('./components/Home'))
const Dashboard = lazy(() => import('./components/Dashboard'))
const Scanner = lazy(() => import('./components/Scanner'))
const LifespanPredictor = lazy(() => import('./components/LifespanPredictorV2.jsx'))
const Inventory = lazy(() => import('./components/Inventory'))
const GenerationForecast = lazy(() => import('./components/GenerationForecast'))
const History = lazy(() => import('./components/History'))
const Signup = lazy(() => import('./components/Signup'))
const Login = lazy(() => import('./components/Login'))
const LegalPage = lazy(() => import('./components/LegalPage'))

function PageLoader() {
  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto" role="status" aria-label="Loading page">
      <div className="skeleton-loader h-12 w-64 max-w-full mb-4"></div>
      <div className="skeleton-loader h-6 w-96 max-w-full mb-12"></div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="skeleton-loader h-64 rounded-xl"></div>
        <div className="skeleton-loader h-64 rounded-xl"></div>
      </div>
    </div>
  )
}

/** @param {{ children: import('react').ReactNode }} props */
function PublicOnlyRoute({ children }) {
  const { isLoaded, isSignedIn } = useAuth()
  if (!isLoaded) return <PageLoader />
  return isSignedIn ? <Navigate to="/dashboard" replace /> : children
}

function AnimatedRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={<PageLoader />}>
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Home />} />
          <Route path="/signup/*" element={<PublicOnlyRoute><Signup /></PublicOnlyRoute>} />
          <Route path="/login/*" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/scanner" element={<ProtectedRoute><Scanner /></ProtectedRoute>} />
          <Route path="/lifespan" element={<ProtectedRoute><LifespanPredictor /></ProtectedRoute>} />
          <Route path="/inventory" element={<ProtectedRoute><Inventory /></ProtectedRoute>} />
          <Route path="/generation" element={<ProtectedRoute><GenerationForecast /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
          <Route path="/privacy" element={<LegalPage page="privacy" />} />
          <Route path="/terms" element={<LegalPage page="terms" />} />
          <Route path="/methodology" element={<LegalPage page="methodology" />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AnimatePresence>
  )
}

function App() {
  return (
    <ThemeProvider>
      <Toaster position="top-right" toastOptions={{ duration: 4000, style: { borderRadius: '12px', padding: '12px 16px' } }} />
      <Router>
        <div className="min-h-screen bg-surface-container-lowest text-on-surface">
          <TopNavBar />
          <main>
            <AnimatedRoutes />
          </main>
          <Footer />
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App
