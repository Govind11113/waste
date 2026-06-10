import { useState, useEffect, useRef } from 'react'
import { Leaf, Cpu, Camera, BarChart3, Trash2 } from 'lucide-react'

const API = '/api/v1/history'
const TABS = [
  { id: 'scans', label: 'Scans', icon: Camera },
  { id: 'lifespan', label: 'Lifespan Predictions', icon: Cpu },
  { id: 'carbon', label: 'Carbon Calculations', icon: Leaf },
]

function History() {
  const [tab, setTab] = useState('scans')
  const [entries, setEntries] = useState([])
  const [stats, setStats] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [perPage] = useState(10)
  const [hasMore, setHasMore] = useState(true)
  const [search, setSearch] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [filter, setFilter] = useState('all')
  const searchTimeoutRef = useRef(null)

  useEffect(() => {
    fetchAll()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, page, search, filter])

  const handleSearch = (value) => {
    setSearchTerm(value)
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    searchTimeoutRef.current = setTimeout(() => {
      setSearch(value)
      setPage(1)
    }, 300)
  }

  const fetchAll = async () => {
    setLoading(true)
    setError(null)
    try {
      if (tab === 'scans') {
        await Promise.all([fetchScans(), fetchScanStats()])
      } else if (tab === 'lifespan') {
        await Promise.all([fetchLifespan(), fetchLifespanStats()])
      } else if (tab === 'carbon') {
        await Promise.all([fetchCarbon(), fetchCarbonStats()])
      }
    } catch (e) {
      setError('Unable to load history. Please check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  const fetchScans = async () => {
    const url = new URL(`${API}/`, window.location.origin)
    url.searchParams.append('page', page)
    url.searchParams.append('per_page', perPage)
    if (search) url.searchParams.append('search', search)
    if (filter !== 'all') url.searchParams.append('status', filter)
    const res = await fetch(url)
    if (!res.ok) throw new Error('Failed to load scans')
    const data = await res.json()
    setEntries(data.items || [])
    setTotal(data.total || 0)
    setHasMore((data.items || []).length === perPage)
  }

  const fetchScanStats = async () => {
    const res = await fetch(`${API}/stats`)
    const data = await res.json()
    setStats(data)
  }

  const fetchLifespan = async () => {
    const url = new URL(`${API}/lifespan`, window.location.origin)
    url.searchParams.append('page', page)
    url.searchParams.append('per_page', perPage)
    const res = await fetch(url)
    if (!res.ok) throw new Error('Failed to load lifespan history')
    const data = await res.json()
    setEntries(data.items || [])
    setTotal(data.total || 0)
    setHasMore((data.items || []).length === perPage)
  }

  const fetchLifespanStats = async () => {
    const res = await fetch(`${API}/lifespan/stats`)
    const data = await res.json()
    setStats(data)
  }

  const fetchCarbon = async () => {
    const url = new URL(`${API}/carbon`, window.location.origin)
    url.searchParams.append('page', page)
    url.searchParams.append('per_page', perPage)
    const res = await fetch(url)
    if (!res.ok) throw new Error('Failed to load carbon history')
    const data = await res.json()
    setEntries(data.items || [])
    setTotal(data.total || 0)
    setHasMore((data.items || []).length === perPage)
  }

  const fetchCarbonStats = async () => {
    const res = await fetch(`${API}/carbon/stats`)
    const data = await res.json()
    setStats(data)
  }

  const clearCurrentTab = async () => {
    if (!confirm(`Clear all ${tab} history? This cannot be undone.`)) return
    const endpoint = tab === 'lifespan' ? `${API}/lifespan` : tab === 'carbon' ? `${API}/carbon` : `${API}/`
    await fetch(endpoint, { method: 'DELETE' })
    setPage(1)
    fetchAll()
  }

  return (
    <div className="pt-32 pb-24 min-h-screen page-transition">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-8 animate-fade-in-down">
          <div className="max-w-2xl">
            <h1 className="text-5xl font-extrabold tracking-tight text-on-surface mb-4">
              Activity History
            </h1>
            <p className="text-on-surface-variant text-lg leading-relaxed">
              A chronological archive of your scans, lifespan predictions, and carbon calculations.
            </p>
          </div>
          <div className="w-full md:w-96">
            <div className="relative">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline">
                search
              </span>
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="w-full bg-surface-container-highest border-none rounded-xl pl-12 pr-4 py-4 focus:ring-2 focus:ring-primary text-on-surface placeholder-outline transition-all form-field"
                placeholder="Search…"
                disabled={tab !== 'scans'}
              />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div className="flex flex-wrap gap-2">
            {TABS.map((t) => {
              const Icon = t.icon
              return (
                <button
                  key={t.id}
                  onClick={() => { setTab(t.id); setPage(1); setSearch('') }}
                  className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition ${
                    tab === t.id
                      ? 'bg-primary text-on-primary shadow-md'
                      : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {t.label}
                </button>
              )
            })}
          </div>
          <button
            onClick={clearCurrentTab}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-rose-600 hover:bg-rose-50 rounded-lg transition"
          >
            <Trash2 className="w-4 h-4" />
            Clear {tab}
          </button>
        </div>

        {/* Filter chips for scans */}
        {tab === 'scans' && (
          <div className="flex flex-wrap gap-2 mb-6">
            {['all', 'E-Waste', 'Non-E-Waste'].map((f) => (
              <button
                key={f}
                onClick={() => { setFilter(f); setPage(1) }}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition ${
                  filter === f
                    ? 'bg-secondary text-white'
                    : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
                }`}
              >
                {f === 'all' ? 'All' : f}
              </button>
            ))}
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-error-container rounded-xl flex items-center gap-3">
            <span className="material-symbols-outlined text-on-error-container">cloud_off</span>
            <span className="text-sm text-on-error-container">{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-3">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="skeleton-loader h-24 rounded-xl"></div>
                ))}
              </div>
            ) : entries.length === 0 ? (
              <div className="bg-surface-container-lowest rounded-xl p-16 text-center">
                <span className="material-symbols-outlined text-6xl text-outline mb-4">
                  history_toggle_off
                </span>
                <h3 className="text-xl font-bold text-on-surface mb-2">No history yet</h3>
                <p className="text-on-surface-variant">
                  {tab === 'scans' && 'Scan a device to see it here.'}
                  {tab === 'lifespan' && 'Run a lifespan prediction to see it here.'}
                  {tab === 'carbon' && 'Calculate carbon to see it here.'}
                </p>
              </div>
            ) : (
              entries.map((entry, index) => (
                <HistoryCard key={entry.id} tab={tab} entry={entry} index={index} />
              ))
            )}

            {/* Pagination */}
            {entries.length > 0 && (
              <div className="mt-6 flex justify-center items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container-low hover:bg-primary hover:text-white disabled:opacity-50 transition"
                >
                  <span className="material-symbols-outlined text-sm">chevron_left</span>
                </button>
                <span className="px-4 font-bold text-on-surface">Page {page}</span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!hasMore}
                  className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container-low hover:bg-primary hover:text-white disabled:opacity-50 transition"
                >
                  <span className="material-symbols-outlined text-sm">chevron_right</span>
                </button>
              </div>
            )}
          </div>

          {/* Right column — stats */}
          <div className="lg:col-span-4 space-y-4">
            {tab === 'scans' && <ScanStats stats={stats} />}
            {tab === 'lifespan' && <LifespanStats stats={stats} />}
            {tab === 'carbon' && <CarbonStats stats={stats} />}
          </div>
        </div>
      </div>
    </div>
  )
}

function HistoryCard({ tab, entry, index }) {
  if (tab === 'scans') {
    return (
      <div className="bg-surface-container-lowest p-5 rounded-xl flex items-center gap-4 hover-lift card-shadow" style={{ animationDelay: `${index * 0.04}s` }}>
        <div className="w-14 h-14 rounded-xl bg-primary-container flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-2xl">photo_camera</span>
        </div>
        <div className="flex-grow min-w-0">
          <div className="flex justify-between items-start mb-1">
            <h3 className="text-lg font-bold text-on-surface truncate">{entry.entity}</h3>
            <span className="text-xs text-outline whitespace-nowrap ml-2">
              {new Date(entry.timestamp).toLocaleDateString()}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="bg-primary-fixed text-on-primary-fixed px-2 py-0.5 rounded-full text-xs font-bold">
              {entry.waste_status} ({(entry.confidence * 100).toFixed(1)}%)
            </span>
            <span className="text-xs text-on-surface-variant truncate">{entry.group_name}</span>
          </div>
        </div>
      </div>
    )
  }
  if (tab === 'lifespan') {
    const eol = entry.remaining_years <= 0
    return (
      <div className={`p-5 rounded-xl flex items-center gap-4 hover-lift card-shadow ${eol ? 'bg-rose-50 border border-rose-200' : 'bg-surface-container-lowest'}`}>
        <div className="w-14 h-14 rounded-xl bg-emerald-100 flex items-center justify-center shrink-0">
          <Cpu className="w-6 h-6 text-emerald-700" />
        </div>
        <div className="flex-grow min-w-0">
          <div className="flex justify-between items-start mb-1">
            <h3 className="text-lg font-bold text-on-surface truncate">{entry.device_type}</h3>
            <span className="text-xs text-outline whitespace-nowrap ml-2">
              {new Date(entry.timestamp).toLocaleDateString()}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
              {entry.remaining_years} yrs left
            </span>
            <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full font-bold">
              Health {(entry.health_score * 100).toFixed(0)}%
            </span>
            <span className="text-on-surface-variant">
              CO₂ {entry.co2_avoided_kg.toFixed(1)} kg · ₹{entry.repair_savings_inr.toFixed(0)}
            </span>
          </div>
        </div>
      </div>
    )
  }
  if (tab === 'carbon') {
    return (
      <div className="bg-surface-container-lowest p-5 rounded-xl flex items-center gap-4 hover-lift card-shadow">
        <div className="w-14 h-14 rounded-xl bg-green-100 flex items-center justify-center shrink-0">
          <Leaf className="w-6 h-6 text-green-700" />
        </div>
        <div className="flex-grow min-w-0">
          <div className="flex justify-between items-start mb-1">
            <h3 className="text-lg font-bold text-on-surface truncate">
              {entry.device_type} ×{entry.units}
            </h3>
            <span className="text-xs text-outline whitespace-nowrap ml-2">
              {new Date(entry.timestamp).toLocaleDateString()}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="bg-green-100 text-green-800 px-2 py-0.5 rounded-full font-bold">
              {entry.total_tco2e.toFixed(2)} tCO₂e
            </span>
            <span className="bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full font-bold">
              {entry.trees_planted} trees
            </span>
            <span className="text-on-surface-variant">
              Embodied {entry.embodied_kg.toFixed(0)}kg · Op {entry.operational_kg.toFixed(0)}kg
            </span>
          </div>
        </div>
      </div>
    )
  }
  return null
}

function StatBlock({ label, value, accent = 'primary' }) {
  return (
    <div className="p-4 bg-surface-container rounded-lg flex items-center justify-between">
      <span className="text-sm text-on-surface-variant">{label}</span>
      <span className={`text-sm font-bold text-${accent}`}>{value}</span>
    </div>
  )
}

function ScanStats({ stats }) {
  return (
    <div className="bg-surface-container-low p-6 rounded-xl hover-lift card-shadow">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-4 h-4 text-primary" />
        <h4 className="text-xs font-bold uppercase tracking-widest text-primary">Scan Activity</h4>
      </div>
      <p className="text-4xl font-black text-on-surface mb-1">{stats.total_scans ?? 0}</p>
      <p className="text-xs text-on-surface-variant mb-4">Total Scans</p>
      <div className="space-y-2">
        <StatBlock label="CO₂ Tracked" value={`${(stats.total_co2_tracked || 0).toFixed(1)} kg`} />
        {Object.entries(stats.status_distribution || {}).map(([k, v]) => (
          <StatBlock key={k} label={k} value={v} />
        ))}
      </div>
    </div>
  )
}

function LifespanStats({ stats }) {
  return (
    <div className="bg-surface-container-low p-6 rounded-xl hover-lift card-shadow">
      <div className="flex items-center gap-2 mb-4">
        <Cpu className="w-4 h-4 text-emerald-600" />
        <h4 className="text-xs font-bold uppercase tracking-widest text-emerald-700">Lifespan Stats</h4>
      </div>
      <p className="text-4xl font-black text-on-surface mb-1">{stats.total_predictions ?? 0}</p>
      <p className="text-xs text-on-surface-variant mb-4">Predictions Run</p>
      <div className="space-y-2">
        <StatBlock label="Avg Health" value={`${((stats.avg_health_score || 0) * 100).toFixed(0)}%`} accent="emerald-600" />
        <StatBlock label="Avg Remaining" value={`${stats.avg_remaining_years || 0} yrs`} accent="emerald-600" />
        <StatBlock label="CO₂ Avoided" value={`${stats.total_co2_avoided_kg || 0} kg`} accent="emerald-600" />
        <StatBlock label="Repair Savings" value={`₹${(stats.total_repair_savings_inr || 0).toFixed(0)}`} accent="emerald-600" />
      </div>
    </div>
  )
}

function CarbonStats({ stats }) {
  return (
    <div className="bg-surface-container-low p-6 rounded-xl hover-lift card-shadow">
      <div className="flex items-center gap-2 mb-4">
        <Leaf className="w-4 h-4 text-green-600" />
        <h4 className="text-xs font-bold uppercase tracking-widest text-green-700">Carbon Stats</h4>
      </div>
      <p className="text-4xl font-black text-on-surface mb-1">{stats.total_calculations ?? 0}</p>
      <p className="text-xs text-on-surface-variant mb-4">Calculations</p>
      <div className="space-y-2">
        <StatBlock label="Total tCO₂e" value={`${stats.total_tco2e || 0}`} accent="green-600" />
        <StatBlock label="Avg per calc" value={`${stats.avg_total_tco2e || 0} tCO₂e`} accent="green-600" />
        <StatBlock label="Trees Equivalent" value={stats.total_trees_planted || 0} accent="green-600" />
        <StatBlock label="Embodied CO₂" value={`${stats.total_embodied_kg || 0} kg`} accent="green-600" />
        <StatBlock label="Operational CO₂" value={`${stats.total_operational_kg || 0} kg`} accent="green-600" />
      </div>
    </div>
  )
}

export default History
