import { useState, useEffect, useRef } from 'react'

function History() {
  const [entries, setEntries] = useState([])
  const [stats, setStats] = useState({ total_scans: 0, total_co2_tracked: 0, status_distribution: {} })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [search, setSearch] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [filter, setFilter] = useState('all')
  const searchTimeoutRef = useRef(null)

  useEffect(() => {
    fetchHistory()
    fetchStats()
  }, [page, search, filter])

  const handleSearch = (value) => {
    setSearchTerm(value)
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    searchTimeoutRef.current = setTimeout(() => {
      setSearch(value)
      setPage(1)
    }, 300)
  }

  const fetchHistory = async () => {
    setError(null)
    try {
      const url = new URL('/api/v1/history/', window.location.origin)
      url.searchParams.append('page', page)
      url.searchParams.append('per_page', 10)
      if (search) url.searchParams.append('search', search)
      if (filter !== 'all') url.searchParams.append('status', filter)

      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to load history')
      const data = await response.json()
      const items = data.items || []
      setEntries(items)
      setHasMore(items.length === 10)
    } catch (err) {
      setError('Unable to load scan history. Please check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/history/stats')
      if (!response.ok) throw new Error('Failed to load stats')
      const data = await response.json()
      setStats(data)
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="pt-32 pb-24 min-h-screen page-transition">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8 animate-fade-in-down">
          <div className="max-w-2xl">
            <h1 className="text-5xl font-extrabold tracking-tight text-on-surface mb-4">Activity History</h1>
            <p className="text-on-surface-variant text-lg leading-relaxed">
              A chronological archive of your scans and predictions.
            </p>
          </div>
          <div className="w-full md:w-96">
            <div className="relative">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline">search</span>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full bg-surface-container-highest border-none rounded-xl pl-12 pr-4 py-4 focus:ring-2 focus:ring-primary text-on-surface placeholder-outline transition-all form-field"
                placeholder="Search by device or filename..."
              />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 mb-10 animate-fade-in-up stagger-1">
          {['all', 'E-Waste', 'Non-E-Waste'].map((f) => (
            <button
              key={f}
              onClick={() => { setFilter(f); setPage(1) }}
              className={`px-5 py-2 rounded-full text-sm font-semibold transition-all duration-300 transform hover:scale-105 ${
                filter === f
                  ? 'bg-secondary text-white shadow-lg'
                  : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container hover:shadow-md'
              }`}
            >
              {f === 'all' ? 'All' : f}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-8 p-6 bg-error-container rounded-xl flex items-center gap-4 animate-scale-in">
            <span className="material-symbols-outlined text-on-error-container text-2xl">cloud_off</span>
            <div className="flex-1">
              <p className="font-semibold text-on-error-container">{error}</p>
            </div>
            <button
              onClick={() => { setLoading(true); fetchHistory() }}
              className="px-4 py-2 bg-error text-on-error rounded-lg font-semibold text-sm hover:opacity-90 transition-all active:scale-95"
            >
              Retry
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-4">
            {loading ? (
              <div className="space-y-4">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="skeleton-loader h-24 rounded-xl" style={{animationDelay: `${i * 0.1}s`}}></div>
                ))}
              </div>
            ) : entries.length === 0 ? (
              <div className="bg-surface-container-lowest rounded-xl p-16 text-center animate-scale-in">
                <span className="material-symbols-outlined text-6xl text-outline mb-4">history_toggle_off</span>
                <h3 className="text-xl font-bold text-on-surface mb-2">No activity yet</h3>
                <p className="text-on-surface-variant">Scan a device or run a prediction to see it appear here.</p>
              </div>
            ) : (
              entries.map((entry, index) => (
                <div key={entry.id} className="bg-surface-container-lowest p-6 rounded-xl flex items-center gap-6 hover-lift card-shadow animate-fade-in-up" style={{animationDelay: `${index * 0.05}s`}}>
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

          <div className="lg:col-span-4 space-y-6 animate-fade-in-up stagger-2">
            <div className="bg-surface-container-low p-8 rounded-xl relative overflow-hidden hover-lift card-shadow">
              <div className="relative z-10">
                <h4 className="text-xs font-bold uppercase tracking-widest text-primary mb-6">Total Activity</h4>
                <div className="mb-6">
                  <span className="text-5xl font-black tracking-tighter text-on-surface">{stats.total_scans}</span>
                  <p className="text-sm text-on-surface-variant mt-2">Total Scans</p>
                </div>
              </div>
              <div className="absolute -right-12 -bottom-12 w-48 h-48 bg-primary/5 rounded-full blur-3xl"></div>
            </div>

            <div className="bg-surface-container-highest p-8 rounded-xl hover-lift card-shadow">
              <h4 className="text-xs font-bold uppercase tracking-widest text-secondary mb-6">Activity Summary</h4>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-surface-container rounded-lg">
                  <span className="text-sm text-on-surface-variant">Classifications</span>
                  <span className="text-sm font-bold text-on-surface">{stats.total_scans}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-surface-container rounded-lg">
                  <span className="text-sm text-on-surface-variant">CO₂ Tracked</span>
                  <span className="text-sm font-bold text-on-surface">{(stats.total_co2_tracked || 0).toFixed(1)}kg</span>
                </div>
                {Object.entries(stats.status_distribution || {}).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between p-3 bg-surface-container rounded-lg">
                    <span className="text-sm text-on-surface-variant">{k}</span>
                    <span className="text-sm font-bold text-on-surface">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {entries.length > 0 && (
          <div className="mt-16 flex justify-center animate-fade-in-up stagger-3">
            <nav className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container-low text-on-surface-variant hover:bg-primary hover:text-white transition-all duration-300 disabled:opacity-50 hover:scale-110 active:scale-95"
              >
                <span className="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <span className="px-4 font-bold text-on-surface">Page {page}</span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={!hasMore}
                className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container-low text-on-surface-variant hover:bg-primary hover:text-white transition-all duration-300 disabled:opacity-50 hover:scale-110 active:scale-95"
              >
                <span className="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </nav>
          </div>
        )}
      </div>
    </div>
  )
}

export default History
