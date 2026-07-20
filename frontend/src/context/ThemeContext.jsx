import { createContext, useContext, useEffect, useState } from 'react'

/** @typedef {{ darkMode: boolean, toggleDarkMode: () => void }} ThemeContextValue */

const ThemeContext = createContext(/** @type {ThemeContextValue | undefined} */ (undefined))

function getInitialDarkMode() {
  if (typeof window === 'undefined') return false

  try {
    const stored = window.localStorage.getItem('darkMode')
    if (stored === 'true' || stored === 'false') return stored === 'true'
  } catch {
    // Storage may be unavailable in privacy mode or a sandboxed document.
  }

  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

/** @param {{ children: import('react').ReactNode }} props */
export function ThemeProvider({ children }) {
  const [darkMode, setDarkMode] = useState(getInitialDarkMode)

  useEffect(() => {
    const root = window.document.documentElement
    root.classList.toggle('dark', darkMode)
    root.classList.toggle('light', !darkMode)

    try {
      window.localStorage.setItem('darkMode', String(darkMode))
    } catch {
      // Theme still works for this session when persistence is unavailable.
    }
  }, [darkMode])

  const toggleDarkMode = () => setDarkMode((value) => !value)

  return (
    <ThemeContext.Provider value={{ darkMode, toggleDarkMode }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used within ThemeProvider')
  return context
}
