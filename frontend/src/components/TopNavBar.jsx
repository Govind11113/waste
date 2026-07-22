import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { UserButton, useAuth } from '@clerk/clerk-react'
import DarkModeToggle from './DarkModeToggle'
import { hoverLift } from '../utils/motion'

const MotionLink = motion(Link)
const APP_LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/scanner', label: 'Classifier' },
  { to: '/lifespan', label: 'Lifespan' },
  { to: '/inventory', label: 'Carbon' },
  { to: '/history', label: 'History' },
]

function TopNavBar() {
  const location = useLocation()
  const { isSignedIn } = useAuth()
  const reduce = useReducedMotion()
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => setMobileOpen(false), [location.pathname])

  /** @param {string} path */
  const isActive = (path) => location.pathname === path
  const navVariants = reduce
    ? { hidden: { opacity: 1 }, visible: { opacity: 1 } }
    : {
        hidden: { opacity: 0, y: -16 },
        visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
      }
  const linkHover = reduce ? undefined : hoverLift

  return (
    <motion.nav
      variants={navVariants}
      initial="hidden"
      animate="visible"
      className="fixed top-0 w-full z-50 bg-surface/90 backdrop-blur-xl shadow-[0_24px_24px_0_rgba(0,98,158,0.06)]"
      aria-label="Primary navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-8 flex justify-between items-center h-20">
        <Link to="/" className="text-xl sm:text-2xl font-black tracking-tighter text-primary" aria-label="E-Waste Management home">
          <span className="sm:hidden">E-Waste</span>
          <span className="hidden sm:inline">E-Waste Management</span>
        </Link>

        {isSignedIn && (
          <div className="hidden md:flex items-center gap-5 lg:gap-7 font-manrope text-sm font-semibold tracking-tight">
            {APP_LINKS.map((link) => (
              <MotionLink
                key={link.to}
                whileHover={linkHover}
                to={link.to}
                aria-current={isActive(link.to) ? 'page' : undefined}
                className={`transition-all duration-300 pb-1 hover:text-secondary ${isActive(link.to) ? 'text-secondary border-b-2 border-secondary' : 'text-on-surface-variant'}`}
              >
                {link.label}
              </MotionLink>
            ))}
          </div>
        )}

        <div className="flex items-center gap-2 sm:gap-4">
          <DarkModeToggle />
          {isSignedIn ? (
            <>
              <UserButton afterSignOutUrl="/login" />
              <button
                type="button"
                className="md:hidden w-10 h-10 inline-flex items-center justify-center rounded-full text-on-surface hover:bg-surface-container"
                aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
                aria-expanded={mobileOpen}
                aria-controls="mobile-auth-navigation"
                onClick={() => setMobileOpen((open) => !open)}
              >
                <span className="material-symbols-outlined" aria-hidden="true">{mobileOpen ? 'close' : 'menu'}</span>
              </button>
            </>
          ) : (
            <Link to="/login" className="bg-primary text-on-primary px-4 sm:px-6 py-2.5 rounded-full font-semibold hover:opacity-80 transition-all duration-300 active:scale-95">
              Login
            </Link>
          )}
        </div>
      </div>

      {isSignedIn && mobileOpen && (
        <div id="mobile-auth-navigation" className="md:hidden border-t border-outline-variant/40 bg-surface-container-lowest px-4 py-3 shadow-lg">
          <div className="grid grid-cols-2 gap-2">
            {APP_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                aria-current={isActive(link.to) ? 'page' : undefined}
                className={`rounded-lg px-4 py-3 text-sm font-bold transition ${isActive(link.to) ? 'bg-primary text-on-primary' : 'text-on-surface-variant hover:bg-surface-container'}`}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </motion.nav>
  )
}

export default TopNavBar
