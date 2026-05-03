import { useEffect, useState } from 'react'

function Dashboard() {
  const [stats, setStats] = useState({
    total_scans: 0,
    total_co2_tracked: 0,
    status_distribution: {}
  })

  useEffect(() => {
    fetch('/api/v1/history/stats')
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(console.error)
  }, [])

  const bentoItems = [
    { label: "Resource Recovery Rate", value: "89%", icon: "recycling", color: "primary" },
    { label: "Active Partners", value: "150+", icon: "groups", color: "secondary" },
    { label: "Next Scheduled Dispatch", value: "Dec 15", icon: "event", color: "tertiary" },
    { label: "Total CO2 Tracked", value: `${(stats.total_co2_tracked || 0).toFixed(1)}kg`, icon: "eco", color: "primary" }
  ]

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <header className="mb-16 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-2">Dashboard</h1>
          <p className="text-on-surface-variant">Real-time sustainability metrics and recovery tracking</p>
        </div>
        <div className="flex gap-3">
          <button className="bg-primary text-on-primary px-6 py-3 rounded-xl font-bold hover:opacity-90 transition-all">
            Export Report
          </button>
          <button className="border border-outline text-on-surface px-6 py-3 rounded-xl font-bold hover:bg-surface-container transition-all">
            Refresh
          </button>
        </div>
      </header>

      {/* Hero Stats */}
      <section className="mb-12 bg-surface-container-lowest p-8 rounded-xl">
        <div className="flex items-center gap-4 mb-4">
          <span className="material-symbols-outlined text-primary text-3xl">eco</span>
          <h2 className="text-2xl font-bold text-on-surface">CO2 Averted</h2>
        </div>
        <div className="flex items-baseline gap-4">
          <span className="text-6xl font-black text-primary tracking-tight">2,450</span>
          <span className="text-xl text-on-surface-variant">tons</span>
        </div>
        <p className="text-sm text-on-surface-variant mt-2">Equivalent to planting 12,800 trees</p>
      </section>

      {/* Bento Grid */}
      <section className="mb-12">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {bentoItems.map((item, index) => (
            <div key={index} className="bg-surface-container-low p-6 rounded-xl">
              <span className={`material-symbols-outlined text-3xl text-${item.color} mb-4`}>
                {item.icon}
              </span>
              <p className="text-2xl font-black text-on-surface">{item.value}</p>
              <p className="text-sm text-on-surface-variant">{item.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Regional Impact Map */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold text-on-surface mb-6">Regional Impact Density</h2>
        <div className="bg-surface-container-lowest p-8 rounded-xl h-64 flex items-center justify-center">
          <div className="text-center">
            <span className="material-symbols-outlined text-6xl text-outline mb-4">map</span>
            <p className="text-on-surface-variant">Interactive Maharashtra district map</p>
            <p className="text-sm text-outline mt-2">Showing e-waste collection density by region</p>
          </div>
        </div>
      </section>

      {/* Recovery Stream */}
      <section>
        <h2 className="text-2xl font-bold text-on-surface mb-6">Real-time Recovery Stream</h2>
        <div className="bg-surface-container-lowest rounded-xl overflow-hidden">
          <div className="grid grid-cols-4 gap-4 p-4 border-b border-outline-variant text-sm font-bold text-on-surface-variant">
            <span>Time</span>
            <span>Institution</span>
            <span>Device</span>
            <span>Status</span>
          </div>
          <div className="divide-y divide-outline-variant">
            <div className="grid grid-cols-4 gap-4 p-4 items-center">
              <span className="text-sm text-on-surface">14:32</span>
              <span className="text-sm text-on-surface">Valia College</span>
              <span className="text-sm text-on-surface">Laptop Dell XPS</span>
              <span className="bg-primary-fixed text-on-primary-fixed px-3 py-1 rounded-full text-xs font-bold w-fit">Classified</span>
            </div>
            <div className="grid grid-cols-4 gap-4 p-4 items-center">
              <span className="text-sm text-on-surface">14:28</span>
              <span className="text-sm text-on-surface">IIT Bombay</span>
              <span className="text-sm text-on-surface">Desktop HP</span>
              <span className="bg-secondary-fixed text-on-secondary-fixed px-3 py-1 rounded-full text-xs font-bold w-fit">Scanned</span>
            </div>
            <div className="grid grid-cols-4 gap-4 p-4 items-center">
              <span className="text-sm text-on-surface">14:15</span>
              <span className="text-sm text-on-surface">Mumbai University</span>
              <span className="text-sm text-on-surface">iPhone 12</span>
              <span className="bg-tertiary-fixed text-on-tertiary-fixed px-3 py-1 rounded-full text-xs font-bold w-fit">Processed</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Dashboard
