import { Component } from 'react'

/** @typedef {{ children: import('react').ReactNode }} ErrorBoundaryProps */
/** @typedef {{ error: Error | null }} ErrorBoundaryState */

/** Keep an unexpected render error from turning the packaged app into a blank page. */
export default class ErrorBoundary extends Component {
  /** @param {ErrorBoundaryProps} props */
  constructor(props) {
    super(props)
    /** @type {ErrorBoundaryState} */
    this.state = { error: null }
  }

  /** @param {Error} error */
  static getDerivedStateFromError(error) {
    return { error }
  }

  /** @param {Error} error @param {import('react').ErrorInfo} info */
  componentDidCatch(error, info) {
    console.error('Unexpected application render error', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="min-h-screen bg-surface flex items-center justify-center p-6">
          <section role="alert" className="max-w-xl w-full bg-surface-container-lowest rounded-xl p-8 card-shadow text-center">
            <span className="material-symbols-outlined text-6xl text-error mb-4" aria-hidden="true">error</span>
            <h1 className="text-3xl font-bold text-on-surface mb-3">The application hit an unexpected error</h1>
            <p className="text-on-surface-variant mb-6">
              Your saved history is unaffected. Restart E-Waste Management, then run the diagnostic tool if this continues.
            </p>
            <button type="button" onClick={() => window.location.reload()} className="bg-primary text-on-primary px-6 py-3 rounded-xl font-bold">
              Reload application
            </button>
          </section>
        </main>
      )
    }
    return this.props.children
  }
}
