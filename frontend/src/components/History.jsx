import { useState, useEffect } from 'react'

function History() {
  const [entries, setEntries] = useState([])
  const [stats, setStats] = useState({ total_scans: 0, total_co2_tracked: 0, status_distribution: {} })
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetchHistory()
    fetchStats()
  }, [page, search, filter])

  const fetchHistory = async () => {
    try {
      const url = new URL('/api/v1/history/', window.location.origin)
      url.searchParams.append('page', page)
      url.searchParams.append('per_page', 10)
      if (search) url.searchParams.append('search', search)
      if (filter !== 'all') url.searchParams.append('status', filter)

      const response = await fetch(url)
      const data = await response.json()
      setEntries(data.items || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/history/stats')
      const data = await response.json()
      setStats(data)
    } catch (err) {
      console.error(err)
    }
  }

  const activityData = [
    { icon: 'hourglass_empty', title: 'MacBook Pro M1 (2020)', date: 'Oct 24, 14:20', tool: 'Lifespan Predictor', result: '3.2 years remaining', color: 'secondary' },
    { icon: 'photo_camera', title: 'Broken iPhone Display', date: 'Oct 22, 09:15', tool: 'Classifier', result: 'Class B: Recyclable', color: 'primary' },
    { icon: 'eco', title: 'Monthly E-Waste Audit', date: 'Oct 20, 18:45', tool: 'Carbon Calculator', result: '14.2kg CO2 Saved', color: 'tertiary' },
    { icon: 'devices', title: 'iPad Air 2 Diagnostic', date: 'Oct 18, 11:30', tool: 'Lifespan Predictor', result: 'End of Life', color: 'secondary' },
  ]

  return (
    <div className="pt-32 pb-24 min-h-screen">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8">
          <div className="max-w-2xl">
            <h1 className="text-5xl font-extrabold tracking-tight text-on-surface mb-4">Activity History</h1>
            <p className="text-on-surface-variant text-lg leading-relaxed">
              A chronological archive of your digital conservatory observations. Monitor your device lifespan and carbon footprint over time.
            </p>
          </div>
          <div className="w-full md:w-96">
            <div className="relative">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline">search</span>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-surface-container-highest border-none rounded-xl pl-12 pr-4 py-4 focus:ring-2 focus:ring-primary text-on-surface placeholder-outline transition-all"
                placeholder="Search by device or tool..."
              />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 mb-10">
          {['all', 'Lifespan Predictor', 'Classifier', 'Carbon Calculator'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-5 py-2 rounded-full text-sm font-semibold transition-all ${
                filter === f
                  ? 'bg-secondary text-white'
                  : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
              }`}
            >
              {f === 'all' ? 'All Tools' : f}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-4">
            {loading ? (
              <div className="text-center py-12">
                <span className="material-symbols-outlined text-4xl animate-spin">refresh</span>
                <p className="text-on-surface-variant mt-4">Loading history...</p>
              </div>
            ) : entries.length === 0 ? (
              activityData.map((entry, index) => (
                <div key={index} className="bg-surface-container-lowest p-6 rounded-xl flex items-center gap-6 group hover:shadow-[0_12px_24px_rgba(0,98,158,0.04)] transition-all duration-300">
                  <div className={`w-16 h-16 rounded-xl bg-${entry.color}-container flex items-center justify-center shrink-0`}>
                    <span className="material-symbols-outlined text-3xl text-on-surface">{entry.icon}</span>
                  </div>
                  <div className="flex-grow">
                    <div className="flex justify-between items-start mb-1">
                      <h3 className="text-xl font-bold text-on-surface group-hover:text-primary transition-colors">{entry.title}</h3>
                      <span className="text-xs font-semibold uppercase tracking-widest text-outline">{entry.date}</span>
                    </div>
                    <p className="text-on-surface-variant text-sm mb-3">{entry.tool} Diagnostic</p>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-secondary">Result:</span>
                      <span className={`bg-${entry.color}-fixed text-on-${entry.color}-fixed px-3 py-1 rounded-full text-xs font-bold`}>
                        {entry.result}
                      </span>
                    </div>
                  </div>
                  <div className="shrink-0">
                    <button className="p-2 rounded-full hover:bg-surface-container transition-colors">
                      <span className="material-symbols-outlined text-outline">chevron_right</span>
                    </button>
                  </div>
                </div>
              ))
            ) : (
              entries.map((entry) => (
                <div key={entry.id} className="bg-surface-container-lowest p-6 rounded-xl flex items-center gap-6">
                  <div className="w-16 h-16 rounded-xl bg-primary-container flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-3xl">photo_camera</span>
                  </div>
                  <div className="flex-grow">
                    <div className="flex justify-between items-start mb-1">
                      <h3 className="text-xl font-bold text-on-surface">{entry.entity}</h3>
                      <span className="text-xs font-semibold uppercase tracking-widest text-outline">
                        {new Date(entry.timestamp).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-on-surface-variant text-sm mb-3">{entry.group_name} Classification</p>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-primary">Result:</span>
                      <span className="bg-primary-fixed text-on-primary-fixed px-3 py-1 rounded-full text-xs font-bold">
                        {entry.waste_status} ({(entry.confidence * 100).toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="lg:col-span-4 space-y-6">
            <div className="bg-surface-container-low p-8 rounded-xl relative overflow-hidden">
              <div className="relative z-10">
                <h4 className="text-xs font-bold uppercase tracking-widest text-primary mb-6">Conservation Impact</h4>
                <div className="mb-8">
                  <span className="text-5xl font-black tracking-tighter text-on-surface">{stats.total_scans}</span>
                  <p className="text-sm text-on-surface-variant mt-2">Total Scans</p>
                </div>
                <div className="relative w-full h-2 bg-outline-variant rounded-full overflow-hidden mb-8">
                  <div className="absolute top-0 left-0 h-full bg-primary" style={{width: '84%'}}></div>
                </div>
                <button className="w-full py-4 bg-white text-primary font-bold rounded-xl shadow-sm hover:shadow-md transition-all text-sm">
                  Download Full Report
                </button>
              </div>
              <div className="absolute -right-12 -bottom-12 w-48 h-48 bg-primary/5 rounded-full blur-3xl"></div>
            </div>

            <div className="bg-surface-container-highest p-8 rounded-xl">
              <h4 className="text-xs font-bold uppercase tracking-widest text-secondary mb-6">Activity Trends</h4>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-on-surface-variant">Predictions</span>
                  <span className="text-sm font-bold text-on-surface">12</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-on-surface-variant">Classifications</span>
                  <span className="text-sm font-bold text-on-surface">{stats.total_scans}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-on-surface-variant">CO2 Tracked</span>
                  <span className="text-sm font-bold text-on-surface">{stats.total_co2_tracked.toFixed(1)}kg</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-16 flex justify-center">
          <nav className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container-low text-on-surface-variant hover:bg-primary hover:text-white transition-all disabled:opacity-50"
            >
              <span className="material-symbols-outlined text-sm">chevron_left</span>
            </button>
            <span className="px-4 font-bold text-on-surface">Page {page}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container-low text-on-surface-variant hover:bg-primary hover:text-white transition-all"
            >
              <span className="material-symbols-outlined text-sm">chevron_right</span>
            </button>
          </nav>
        </div>
      </div>
    </div>
  )
}

export default History
