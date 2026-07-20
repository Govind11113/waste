/** @param {{ message: string }} props */
export default function ConfigurationError({ message }) {
  return (
    <main className="min-h-screen bg-surface flex items-center justify-center p-6">
      <section role="alert" className="max-w-2xl w-full bg-surface-container-lowest rounded-xl p-8 sm:p-10 card-shadow">
        <div className="flex items-start gap-4">
          <span className="material-symbols-outlined text-5xl text-tertiary" aria-hidden="true">settings_alert</span>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-tertiary mb-2">Configuration required</p>
            <h1 className="text-3xl font-bold text-on-surface mb-3">E-Waste Management is not configured yet</h1>
            <p className="text-on-surface-variant mb-5">{message}</p>
            <ol className="list-decimal pl-5 space-y-2 text-sm text-on-surface-variant mb-6">
              <li>Run <strong>Configure E-Waste.cmd</strong> from the extracted Windows folder.</li>
              <li>Enter a Clerk development publishable key beginning with <code>pk_test_</code> and its HTTPS JWKS URL.</li>
              <li>Restart the application with <strong>Start E-Waste.cmd</strong>.</li>
            </ol>
            <p className="text-xs text-on-surface-variant mb-6">Do not use a Clerk production key on localhost. Production keys are restricted to their configured HTTPS domain.</p>
            <button type="button" onClick={() => window.location.reload()} className="bg-primary text-on-primary px-6 py-3 rounded-xl font-bold">
              Retry configuration
            </button>
          </div>
        </div>
      </section>
    </main>
  )
}
