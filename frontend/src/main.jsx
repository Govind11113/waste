import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ClerkProvider } from '@clerk/clerk-react'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import ConfigurationError from './components/ConfigurationError.jsx'
import { loadRuntimeConfig } from './runtimeConfig.js'
import 'leaflet/dist/leaflet.css'
import './index.css'

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Missing #root mount element')
}

const root = createRoot(rootElement)

async function bootstrap() {
  try {
    const config = await loadRuntimeConfig()
    if (!config.clerkPublishableKey) throw new Error('Clerk publishable key is missing')

    root.render(
      <StrictMode>
        <ErrorBoundary>
          <ClerkProvider publishableKey={config.clerkPublishableKey}>
            <App />
          </ClerkProvider>
        </ErrorBoundary>
      </StrictMode>,
    )
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Application configuration could not be loaded.'
    root.render(
      <StrictMode>
        <ConfigurationError message={message} />
      </StrictMode>,
    )
  }
}

bootstrap()
