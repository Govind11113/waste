import { useEffect, useState, useCallback } from 'react'
import MaharashtraWeatherMap from './MaharashtraWeatherMap'

function Dashboard() {
  const [stats, setStats] = useState({
    total_scans: 0,
    total_co2_tracked: 0,
    status_distribution: {}
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStats = useCallback(() => {
    setError(null)
    fetch('/api/v1/history/stats')
      .then(res => {
        if (!res.ok) throw new Error('Failed to load stats')
        return res.json()
      })
      .then(data => {
        setStats(data)
        setLoading(false)
      })
      .catch(() => {
        setError('Failed to load dashboard stats')
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  const handleRefresh = () => {
    setLoading(true)
    fetchStats()
  }

  const eWasteCount = stats.status_distribution?.['E-Waste'] || 0
  const nonEWasteCount = stats.status_distribution?.['Non-E-Waste'] || 0
  const treesEquivalent = Math.max(0, Math.round((stats.total_co2_tracked || 0) * 0.045))

  const bentoItems = [
    { label: "Total Scans", value: stats.total_scans, icon: "qr_code_scanner", iconColor: "text-primary" },
    { label: "E-Waste Items", value: eWasteCount, icon: "delete", iconColor: "text-error" },
    { label: "Non-E-Waste Items", value: nonEWasteCount, icon: "recycling", iconColor: "text-primary" },
    { label: "CO₂ Tracked (kg)", value: (stats.total_co2_tracked || 0).toFixed(1), icon: "eco", iconColor: "text-secondary" }
  ]

  if (loading) {
    return (
      <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
        <div className="skeleton-loader h-12 w-64 mb-4"></div>
        <div className="skeleton-loader h-6 w-96 mb-16"></div>
        <div className="skeleton-loader h-32 mb-12 rounded-xl"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="skeleton-loader h-32 rounded-xl" style={{animationDelay: `${i * 0.1}s`}}></div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto text-center page-transition">
        <span className="material-symbols-outlined text-6xl text-error mb-4 animate-scale-in">error</span>
        <h2 className="text-2xl font-bold text-on-surface mb-4">{error}</h2>
        <button
          onClick={handleRefresh}
          className="bg-primary text-on-primary px-6 py-3 rounded-xl font-bold hover:opacity-90 transition-all btn-ripple active:scale-[0.98]"
        >
          Reload Page
        </button>
      </div>
    )
  }

  const isEmpty = stats.total_scans === 0

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
      <header className="mb-16 flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-down">
        <div>
          <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-2">Dashboard</h1>
          <p className="text-on-surface-variant">Real-time sustainability metrics from your scans</p>
        </div>
        <button
          onClick={handleRefresh}
          className="border border-outline text-on-surface px-6 py-3 rounded-xl font-bold hover:bg-surface-container transition-all hover:-translate-y-0.5 active:scale-[0.98] flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-lg">refresh</span>
          Refresh
        </button>
      </header>

      {isEmpty ? (
        <>
          <section className="mb-12 animate-fade-in-up">
            <MaharashtraWeatherMap compact={false} />
          </section>
          <div className="bg-surface-container-lowest p-16 rounded-xl text-center animate-scale-in hover-lift card-shadow">
          <span className="material-symbols-outlined text-6xl text-outline mb-4">analytics</span>
          <h2 className="text-2xl font-bold text-on-surface mb-2">No data yet</h2>
          <p className="text-on-surface-variant mb-6 max-w-md mx-auto">
            Start by scanning a device or running a lifespan prediction. Your dashboard will populate with real metrics as you use the platform.
          </p>
          <a href="/scanner" className="inline-flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-xl font-bold hover:opacity-90 transition-all hover:-translate-y-0.5 hover:shadow-xl active:scale-[0.98] btn-ripple">
            <span className="material-symbols-outlined">qr_code_scanner</span>
            Scan a Device
          </a>
        </div>
        </>
      ) : (
        <>
          <section className="mb-12 bg-surface-container-lowest p-8 rounded-xl animate-fade-in-up stagger-1 hover-lift card-shadow">
            <div className="flex items-center gap-4 mb-4">
              <span className="material-symbols-outlined text-primary text-3xl">eco</span>
              <h2 className="text-2xl font-bold text-on-surface">CO₂ Tracked from Recycling</h2>
            </div>
            <div className="flex items-baseline gap-4">
              <span className="text-6xl font-black text-primary tracking-tight">{(stats.total_co2_tracked || 0).toFixed(1)}</span>
              <span className="text-xl text-on-surface-variant">kg</span>
            </div>
            <p className="text-sm text-on-surface-variant mt-2">Roughly equivalent to {treesEquivalent} trees absorbing CO₂ for one year</p>
          </section>

          <section className="mb-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {bentoItems.map((item, index) => (
                <div key={index} className="bg-surface-container-low p-6 rounded-xl animate-scale-in hover-lift card-shadow" style={{animationDelay: `${(index + 1) * 0.1}s`}}>
                  <span className={`material-symbols-outlined text-3xl ${item.iconColor} mb-4`}>
                    {item.icon}
                  </span>
                  <p className="text-2xl font-black text-on-surface">{item.value}</p>
                  <p className="text-sm text-on-surface-variant">{item.label}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="mb-12 animate-fade-in-up stagger-2">
            <MaharashtraWeatherMap compact={false} />
          </section>

          <section className="mb-12 animate-fade-in-up stagger-3">
            <h2 className="text-2xl font-bold text-on-surface mb-6">Maharashtra IT Lab Insights</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-surface-container-lowest p-6 rounded-xl hover-lift card-shadow">
                <span className="material-symbols-outlined text-3xl text-primary mb-3">school</span>
                <h3 className="font-bold text-on-surface mb-2">Education Sector Share</h3>
                <p className="text-3xl font-black text-on-surface mb-2">~18%</p>
                <p className="text-sm text-on-surface-variant">of Maharashtra's institutional e-waste comes from schools, colleges and universities.</p>
              </div>
              <div className="bg-surface-container-lowest p-6 rounded-xl hover-lift card-shadow">
                <span className="material-symbols-outlined text-3xl text-secondary mb-3">schedule</span>
                <h3 className="font-bold text-on-surface mb-2">Avg Lab Computer Lifecycle</h3>
                <p className="text-3xl font-black text-on-surface mb-2">5–7 yrs</p>
                <p className="text-sm text-on-surface-variant">Climate-controlled labs in Pune & Mumbai see longer service life than coastal humidity zones.</p>
              </div>
              <div className="bg-surface-container-lowest p-6 rounded-xl hover-lift card-shadow">
                <span className="material-symbols-outlined text-3xl text-tertiary mb-3">event_repeat</span>
                <h3 className="font-bold text-on-surface mb-2">EPR Filing Window</h3>
                <p className="text-3xl font-black text-on-surface mb-2">30 Jun</p>
                <p className="text-sm text-on-surface-variant">Annual e-waste manifest must be filed with MPCB by financial year-end + 90 days.</p>
              </div>
            </div>
          </section>

          {Object.keys(stats.status_distribution || {}).length > 0 && (
            <section className="animate-fade-in-up stagger-3">
              <h2 className="text-2xl font-bold text-on-surface mb-6">Status Distribution</h2>
              <div className="bg-surface-container-lowest rounded-xl p-8 hover-lift card-shadow">
                <div className="space-y-4">
                  {Object.entries(stats.status_distribution).map(([status, count]) => {
                    const pct = stats.total_scans > 0 ? (count / stats.total_scans) * 100 : 0
                    return (
                      <div key={status}>
                        <div className="flex justify-between mb-2">
                          <span className="text-on-surface font-semibold">{status}</span>
                          <span className="text-on-surface-variant">{count} ({pct.toFixed(0)}%)</span>
                        </div>
                        <div className="bg-surface-container rounded-full h-3 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-1000"
                            style={{ width: `${pct}%`, backgroundColor: status === 'E-Waste' ? '#ba1a1a' : 'var(--primary)' }}
                          ></div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}

export default Dashboard
