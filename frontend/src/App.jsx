import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from './context/ThemeContext'
import { SignedOut } from '@clerk/clerk-react'
import { lazy, Suspense } from 'react'
import TopNavBar from './components/TopNavBar'
import Footer from './components/Footer'
import ProtectedRoute from './components/ProtectedRoute'

const Home = lazy(() => import('./components/Home'))
const Dashboard = lazy(() => import('./components/Dashboard'))
const Scanner = lazy(() => import('./components/Scanner'))
const LifespanPredictor = lazy(() => import('./components/LifespanPredictorV2.jsx'))
const Inventory = lazy(() => import('./components/Inventory'))
const History = lazy(() => import('./components/History'))
const Signup = lazy(() => import('./components/Signup'))
const Login = lazy(() => import('./components/Login'))

function PageLoader() {
  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto">
      <div className="skeleton-loader h-12 w-64 mb-4"></div>
      <div className="skeleton-loader h-6 w-96 mb-12"></div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="skeleton-loader h-64 rounded-xl"></div>
        <div className="skeleton-loader h-64 rounded-xl"></div>
      </div>
    </div>
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
            <Suspense fallback={<PageLoader />}>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/signup/*" element={
                  <SignedOut><Signup /></SignedOut>
                } />
                <Route path="/login/*" element={
                  <SignedOut><Login /></SignedOut>
                } />
                <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="/scanner" element={<ProtectedRoute><Scanner /></ProtectedRoute>} />
                <Route path="/lifespan" element={<ProtectedRoute><LifespanPredictor /></ProtectedRoute>} />
                <Route path="/inventory" element={<ProtectedRoute><Inventory /></ProtectedRoute>} />
                <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </main>
          <Footer />
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App
