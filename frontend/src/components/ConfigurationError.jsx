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
            <p className="text-sm text-on-surface-variant mb-3">
              Add a Clerk development publishable key beginning with <code>pk_test_</code> and its HTTPS JWKS URL to both environment files, then restart the app.
            </p>
            <ol className="list-decimal pl-5 space-y-2 text-sm text-on-surface-variant mb-4">
              <li>
                In <strong>backend/.env</strong> set <code>EWASTE_CLERK_PUBLISHABLE_KEY</code> and <code>CLERK_JWKS_URL</code>.
              </li>
              <li>
                In <strong>frontend/.env</strong> set <code>VITE_CLERK_PUBLISHABLE_KEY</code> to the same <code>pk_test_</code> value.
              </li>
              <li>
                Restart the servers.<br />
                <span className="text-xs">
                  macOS/Linux: <code>./run_backend.sh</code> and <code>./run_frontend.sh</code> — Windows: <code>.\run-windows.ps1</code>, or run the packaged <code>Configure E-Waste.cmd</code> then <code>Start E-Waste.cmd</code>.
                </span>
              </li>
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
