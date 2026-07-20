import { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { toast } from 'react-hot-toast'
import { Leaf, Cpu, Camera, BarChart3, Trash2 } from 'lucide-react'
import { useApiFetch } from '../utils/api'
import AnimatedPage from './AnimatedPage'
import { fadeInUp } from '../utils/motion'

/**
 * @typedef {{
 *   id: string | number,
 *   timestamp: string,
 *   entity: string,
 *   confidence: number,
 *   waste_status: string,
 *   group_name: string,
 *   device_type: string,
 *   remaining_years: number,
 *   health_score: number,
 *   co2_avoided_kg: number,
 *   repair_savings_inr: number,
 *   units: number,
 *   total_tco2e: number,
 *   trees_planted: number,
 *   embodied_kg: number,
 *   operational_kg: number,
 *   model_requested?: string,
 *   model_used?: string,
 *   software_load?: string,
 *   normalized_weights?: Record<string, number>,
 * }} HistoryEntry
 * @typedef {{
 *   total_scans?: number,
 *   total_co2_tracked?: number,
 *   status_distribution?: Record<string, number>,
 *   total_predictions?: number,
 *   avg_health_score?: number,
 *   avg_remaining_years?: number,
 *   total_co2_avoided_kg?: number,
 *   total_repair_savings_inr?: number,
 *   total_calculations?: number,
 *   total_tco2e?: number,
 *   avg_total_tco2e?: number,
 *   total_trees_planted?: number,
 *   total_embodied_kg?: number,
 *   total_operational_kg?: number,
 * }} HistoryStats
 */

const API = '/api/v1/history'
const PER_PAGE = 10
const TABS = [
  { id: 'scans', label: 'Scans', icon: Camera, list: `${API}/`, stats: `${API}/stats` },
  { id: 'lifespan', label: 'Lifespan Predictions', icon: Cpu, list: `${API}/lifespan`, stats: `${API}/lifespan/stats` },
  { id: 'carbon', label: 'Carbon Calculations', icon: Leaf, list: `${API}/carbon`, stats: `${API}/carbon/stats` },
]

/** @param {unknown} detail */
function apiDetail(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg).filter(Boolean).join('; ')
  return ''
}

/** @param {Response} response @param {string} fallback */
async function responseError(response, fallback) {
  const payload = await response.json().catch(() => ({}))
  return new Error(apiDetail(payload.detail) || fallback)
}

function History() {
  const apiFetch = useApiFetch()
  const [tab, setTab] = useState('scans')
  const [entries, setEntries] = useState(/** @type {HistoryEntry[]} */ ([]))
  const [stats, setStats] = useState(/** @type {HistoryStats} */ ({}))
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState(/** @type {string | null} */ (null))
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [filter, setFilter] = useState('all')
  const [reloadKey, setReloadKey] = useState(0)
  const searchTimeoutRef = useRef(/** @type {number | null} */ (null))
  const requestSequenceRef = useRef(0)

  useEffect(() => () => {
    if (searchTimeoutRef.current !== null) window.clearTimeout(searchTimeoutRef.current)
  }, [])

  useEffect(() => {
    const sequence = ++requestSequenceRef.current
    const controller = new AbortController()
    const activeTab = TABS.find((item) => item.id === tab) ?? TABS[0]

    const load = async () => {
      setLoading(true)
      setError(null)
      setEntries([])
      setStats({})

      try {
        const url = new URL(activeTab.list, window.location.origin)
        url.searchParams.set('page', String(page))
        url.searchParams.set('per_page', String(PER_PAGE))
        if (tab === 'scans' && search) url.searchParams.set('search', search)
        if (tab === 'scans' && filter !== 'all') url.searchParams.set('status', filter)

        const [listResponse, statsResponse] = await Promise.all([
          apiFetch(url, { signal: controller.signal }),
          apiFetch(activeTab.stats, { signal: controller.signal }),
        ])
        if (!listResponse.ok) throw await responseError(listResponse, `Failed to load ${activeTab.label.toLowerCase()}`)
        if (!statsResponse.ok) throw await responseError(statsResponse, `Failed to load ${activeTab.label.toLowerCase()} statistics`)

        const [listData, statsData] = await Promise.all([listResponse.json(), statsResponse.json()])
        if (controller.signal.aborted || requestSequenceRef.current !== sequence) return

        const nextTotal = Number(listData.total) || 0
        const nextTotalPages = Math.max(1, Math.ceil(nextTotal / PER_PAGE))
        if (page > nextTotalPages) {
          setPage(nextTotalPages)
          return
        }
        setEntries(Array.isArray(listData.items) ? listData.items : [])
        setTotal(nextTotal)
        setStats(statsData && typeof statsData === 'object' ? statsData : {})
      } catch (caught) {
        if (controller.signal.aborted || requestSequenceRef.current !== sequence) return
        const message = caught instanceof Error
          ? caught.message
          : 'Unable to load history. Please check your connection and try again.'
        setError(message)
        setEntries([])
        setTotal(0)
        setStats({})
      } finally {
        if (!controller.signal.aborted && requestSequenceRef.current === sequence) setLoading(false)
      }
    }

    load()
    return () => controller.abort()
  }, [apiFetch, filter, page, reloadKey, search, tab])

  /** @param {string} value */
  const handleSearch = (value) => {
    setSearchTerm(value)
    if (searchTimeoutRef.current !== null) window.clearTimeout(searchTimeoutRef.current)
    searchTimeoutRef.current = window.setTimeout(() => {
      setSearch(value.trim())
      setPage(1)
    }, 300)
  }

  /** @param {string} nextTab */
  const selectTab = (nextTab) => {
    setTab(nextTab)
    setPage(1)
    setSearch('')
    setSearchTerm('')
    setFilter('all')
  }

  const clearCurrentTab = async () => {
    if (!window.confirm(`Clear all ${tab} history? This cannot be undone.`)) return
    const endpoint = tab === 'lifespan' ? `${API}/lifespan` : tab === 'carbon' ? `${API}/carbon` : `${API}/`
    setDeleting(true)
    setError(null)
    try {
      const response = await apiFetch(endpoint, { method: 'DELETE' })
      if (!response.ok) throw await responseError(response, `Failed to clear ${tab} history`)
      setPage(1)
      setReloadKey((value) => value + 1)
      toast.success(`${tab[0].toUpperCase()}${tab.slice(1)} history cleared`)
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : `Failed to clear ${tab} history`
      setError(message)
      toast.error(message)
    } finally {
      setDeleting(false)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  return (
    <AnimatedPage>
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
            <label htmlFor="history-search" className="sr-only">Search scan history</label>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline" aria-hidden="true">
                search
              </span>
              <input
                id="history-search"
                type="search"
                value={searchTerm}
                onChange={(event) => handleSearch(event.target.value)}
                className="w-full bg-surface-container-highest border-none rounded-xl pl-12 pr-4 py-4 focus:ring-2 focus:ring-primary text-on-surface placeholder-outline transition-all form-field"
                placeholder="Search scans…"
                disabled={tab !== 'scans'}
              />
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="History category">
            {TABS.map((item) => {
              const Icon = item.icon
              const selected = tab === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  aria-controls="history-panel"
                  onClick={() => selectTab(item.id)}
                  className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition ${
                    selected
                      ? 'bg-primary text-on-primary shadow-md'
                      : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
                  }`}
                >
                  <Icon className="w-4 h-4" aria-hidden="true" />
                  {item.label}
                </button>
              )
            })}
          </div>
          <button
            type="button"
            onClick={clearCurrentTab}
            disabled={deleting || loading}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-error hover:bg-error-container rounded-lg transition disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" aria-hidden="true" />
            {deleting ? 'Clearing…' : `Clear ${tab}`}
          </button>
        </div>

        {tab === 'scans' && (
          <div className="flex flex-wrap gap-2 mb-6" role="group" aria-label="Filter scan history by status">
            {['all', 'E-Waste', 'Non-E-Waste'].map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={filter === value}
                onClick={() => { setFilter(value); setPage(1) }}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition ${
                  filter === value
                    ? 'bg-secondary text-on-secondary'
                    : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'
                }`}
              >
                {value === 'all' ? 'All' : value}
              </button>
            ))}
          </div>
        )}

        {error && (
          <div role="alert" className="mb-6 p-4 bg-error-container rounded-xl flex items-center gap-3">
            <span className="material-symbols-outlined text-on-error-container" aria-hidden="true">cloud_off</span>
            <span className="text-sm text-on-error-container">{error}</span>
          </div>
        )}

        <div id="history-panel" role="tabpanel" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
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

            {total > 0 && (
              <nav className="mt-6 flex justify-center items-center gap-2" aria-label="History pagination">
                <button
                  type="button"
                  aria-label="Previous history page"
                  onClick={() => setPage((value) => Math.max(1, value - 1))}
                  disabled={page <= 1}
                  className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container-low hover:bg-primary hover:text-on-primary disabled:opacity-50 transition"
                >
                  <span className="material-symbols-outlined text-sm" aria-hidden="true">chevron_left</span>
                </button>
                <span className="px-4 font-bold text-on-surface" aria-live="polite">
                  Page {page} of {totalPages} · {total} records
                </span>
                <button
                  type="button"
                  aria-label="Next history page"
                  onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                  disabled={page >= totalPages}
                  className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container-low hover:bg-primary hover:text-on-primary disabled:opacity-50 transition"
                >
                  <span className="material-symbols-outlined text-sm" aria-hidden="true">chevron_right</span>
                </button>
              </nav>
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
    </AnimatedPage>
  )
}

/** @param {{ tab: string, entry: HistoryEntry, index: number }} props */
function HistoryCard({ tab, entry, index }) {
  const reduce = useReducedMotion()
  const variants = reduce
    ? { hidden: { opacity: 1 }, visible: { opacity: 1 } }
    : fadeInUp
  const motionProps = { variants, initial: 'hidden', animate: 'visible' }
  if (tab === 'scans') {
    return (
      <motion.div {...motionProps} className="bg-surface-container-lowest p-5 rounded-xl flex items-center gap-4 hover-lift card-shadow" style={{ animationDelay: `${index * 0.04}s` }}>
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
            <span className="text-xs text-on-surface-variant truncate">{entry.group_name}{entry.model_used ? ` · ${entry.model_used}` : ''}</span>
          </div>
        </div>
      </motion.div>
    )
  }
  if (tab === 'lifespan') {
    const eol = entry.remaining_years <= 0
    return (
      <motion.div {...motionProps} className={`p-5 rounded-xl flex items-center gap-4 hover-lift card-shadow ${eol ? 'bg-rose-50 border border-rose-200' : 'bg-surface-container-lowest'}`}>
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
              CO₂ proxy {entry.co2_avoided_kg.toFixed(1)} kg · repair proxy ₹{entry.repair_savings_inr.toFixed(0)}
            </span>
            {(entry.model_used || entry.software_load) && (
              <span className="text-on-surface-variant">
                {entry.model_used ? `model ${entry.model_used}` : ''}{entry.model_used && entry.software_load ? ' · ' : ''}{entry.software_load ? `workload ${entry.software_load}` : ''}
              </span>
            )}
          </div>
        </div>
      </motion.div>
    )
  }
  if (tab === 'carbon') {
    return (
      <motion.div {...motionProps} className="bg-surface-container-lowest p-5 rounded-xl flex items-center gap-4 hover-lift card-shadow">
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
              {entry.trees_planted} tree-year eq.
            </span>
            <span className="text-on-surface-variant">
              Embodied {entry.embodied_kg.toFixed(0)}kg · Op {entry.operational_kg.toFixed(0)}kg
            </span>
          </div>
        </div>
      </motion.div>
    )
  }
  return null
}

const STAT_ACCENT_CLASSES = {
  primary: 'text-primary',
  'emerald-600': 'text-emerald-600',
  'green-600': 'text-green-600',
}

/** @param {'primary' | 'emerald-600' | 'green-600'} accent */
export function statAccentClass(accent) {
  return STAT_ACCENT_CLASSES[accent]
}

/** @param {{ label: string, value: import('react').ReactNode, accent?: 'primary' | 'emerald-600' | 'green-600' }} props */
function StatBlock({ label, value, accent = 'primary' }) {
  return (
    <div className="p-4 bg-surface-container rounded-lg flex items-center justify-between">
      <span className="text-sm text-on-surface-variant">{label}</span>
      <span className={`text-sm font-bold ${statAccentClass(accent)}`}>{value}</span>
    </div>
  )
}

/** @param {{ stats: HistoryStats }} props */
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
        <StatBlock label="Indicative recovery CO₂" value={`${(stats.total_co2_tracked || 0).toFixed(1)} kg`} />
        {Object.entries(stats.status_distribution || {}).map(([k, v]) => (
          <StatBlock key={k} label={k} value={v} />
        ))}
      </div>
    </div>
  )
}

/** @param {{ stats: HistoryStats }} props */
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
        <StatBlock label="CO₂ proxy total" value={`${stats.total_co2_avoided_kg || 0} kg`} accent="emerald-600" />
        <StatBlock label="Repair-cost proxy" value={`₹${(stats.total_repair_savings_inr || 0).toFixed(0)}`} accent="emerald-600" />
      </div>
    </div>
  )
}

/** @param {{ stats: HistoryStats }} props */
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
        <StatBlock label="Tree-year equivalents" value={stats.total_trees_planted || 0} accent="green-600" />
        <StatBlock label="Embodied CO₂" value={`${stats.total_embodied_kg || 0} kg`} accent="green-600" />
        <StatBlock label="Operational CO₂" value={`${stats.total_operational_kg || 0} kg`} accent="green-600" />
      </div>
    </div>
  )
}

export default History
