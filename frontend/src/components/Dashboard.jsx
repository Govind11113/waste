import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import MaharashtraWeatherMap from './MaharashtraWeatherMap'
import AnimatedPage from './AnimatedPage'
import { useApiFetch } from '../utils/api'
import { fadeInUp, stagger } from '../utils/motion'
import { useCountUp } from '../utils/useCountUp'

/** @typedef {{ total_scans: number, total_co2_tracked: number, status_distribution: Record<string, number> }} DashboardStats */

function Dashboard() {
  const apiFetch = useApiFetch()
  const [stats, setStats] = useState(/** @type {DashboardStats} */ ({
    total_scans: 0,
    total_co2_tracked: 0,
    status_distribution: {},
  }))
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(/** @type {string | null} */ (null))

  const fetchStats = useCallback(() => {
    setError(null)
    apiFetch('/api/v1/history/stats')
      .then((response) => {
        if (!response.ok) throw new Error('Failed to load stats')
        return response.json()
      })
      .then((data) => {
        setStats(data)
        setLoading(false)
      })
      .catch(() => {
        setError('Failed to load dashboard stats')
        setLoading(false)
      })
  }, [apiFetch])

  useEffect(() => fetchStats(), [fetchStats])

  const handleRefresh = () => {
    setLoading(true)
    fetchStats()
  }

  const eWasteCount = stats.status_distribution?.['E-Waste'] || 0
  const nonEWasteCount = stats.status_distribution?.['Non-E-Waste'] || 0
  const treeYearEquivalent = Math.max(0, Math.ceil((stats.total_co2_tracked || 0) / 22))

  const animatedTotalScans = useCountUp(stats.total_scans || 0)
  const animatedEWaste = useCountUp(eWasteCount)
  const animatedNonEWaste = useCountUp(nonEWasteCount)
  const animatedCo2 = useCountUp(stats.total_co2_tracked || 0)

  const bentoItems = [
    { label: 'Recorded scans', value: Math.round(animatedTotalScans), icon: 'qr_code_scanner', iconColor: 'text-primary' },
    { label: 'Classified e-waste', value: Math.round(animatedEWaste), icon: 'delete', iconColor: 'text-error' },
    { label: 'Classified non-e-waste', value: Math.round(animatedNonEWaste), icon: 'category', iconColor: 'text-primary' },
    { label: 'Indicative recovery CO₂ (kg)', value: animatedCo2.toFixed(1), icon: 'eco', iconColor: 'text-secondary' },
  ]

  if (loading) {
    return (
      <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition" role="status" aria-label="Loading dashboard">
        <div className="skeleton-loader h-12 w-64 max-w-full mb-4"></div>
        <div className="skeleton-loader h-6 w-96 max-w-full mb-16"></div>
        <div className="skeleton-loader h-32 mb-12 rounded-xl"></div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((item) => <div key={item} className="skeleton-loader h-32 rounded-xl"></div>)}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto text-center page-transition">
        <span className="material-symbols-outlined text-6xl text-error mb-4" aria-hidden="true">error</span>
        <h2 className="text-2xl font-bold text-on-surface mb-4">{error}</h2>
        <button type="button" onClick={handleRefresh} className="bg-primary text-on-primary px-6 py-3 rounded-xl font-bold hover:opacity-90 transition-all">
          Retry
        </button>
      </div>
    )
  }

  const isEmpty = stats.total_scans === 0

  return (
    <AnimatedPage>
      <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
        <header className="mb-12 flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in-down">
          <div>
            <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-2">Dashboard</h1>
            <p className="text-on-surface-variant">Authenticated activity summaries and assumption-based planning values</p>
          </div>
          <button type="button" onClick={handleRefresh} className="border border-outline text-on-surface px-6 py-3 rounded-xl font-bold hover:bg-surface-container transition-all flex items-center gap-2">
            <span className="material-symbols-outlined text-lg" aria-hidden="true">refresh</span>
            Refresh
          </button>
        </header>

        {isEmpty ? (
          <>
            <section className="mb-12 animate-fade-in-up">
              <MaharashtraWeatherMap compact={false} />
            </section>
            <div className="bg-surface-container-lowest p-12 sm:p-16 rounded-xl text-center card-shadow">
              <span className="material-symbols-outlined text-6xl text-outline mb-4" aria-hidden="true">analytics</span>
              <h2 className="text-2xl font-bold text-on-surface mb-2">No scan records yet</h2>
              <p className="text-on-surface-variant mb-6 max-w-md mx-auto">Scan a device to populate this per-user activity summary. Lifespan and carbon records are available on the History page.</p>
              <Link to="/scanner" className="inline-flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-xl font-bold hover:opacity-90 transition-all">
                <span className="material-symbols-outlined" aria-hidden="true">qr_code_scanner</span>
                Scan a Device
              </Link>
            </div>
          </>
        ) : (
          <>
            <section className="mb-12 bg-surface-container-lowest p-8 rounded-xl card-shadow">
              <div className="flex items-center gap-4 mb-4">
                <span className="material-symbols-outlined text-primary text-3xl" aria-hidden="true">eco</span>
                <h2 className="text-2xl font-bold text-on-surface">Indicative Material-Recovery CO₂ Estimate</h2>
              </div>
              <div className="flex items-baseline gap-4">
                <span className="text-6xl font-black text-primary tracking-tight">{animatedCo2.toFixed(1)}</span>
                <span className="text-xl text-on-surface-variant">kg</span>
              </div>
              <p className="text-sm text-on-surface-variant mt-2">Profile-based sum for your recognized scans, not a measured recycling outcome. At the 22 kg CO₂/year planning basis, this is {treeYearEquivalent} rounded-up tree-year equivalent{treeYearEquivalent === 1 ? '' : 's'}.</p>
            </section>

            <section className="mb-12">
              <motion.div className="grid grid-cols-2 md:grid-cols-4 gap-6" variants={stagger} initial="hidden" animate="visible">
                {bentoItems.map((item) => (
                  <motion.div key={item.label} variants={fadeInUp} className="bg-surface-container-low p-6 rounded-xl card-shadow">
                    <span className={`material-symbols-outlined text-3xl ${item.iconColor} mb-4`} aria-hidden="true">{item.icon}</span>
                    <p className="text-2xl font-black text-on-surface">{item.value}</p>
                    <p className="text-sm text-on-surface-variant">{item.label}</p>
                  </motion.div>
                ))}
              </motion.div>
            </section>

            <section className="mb-12 animate-fade-in-up">
              <MaharashtraWeatherMap compact={false} />
            </section>

            {Object.keys(stats.status_distribution || {}).length > 0 && (
              <section className="mb-12 animate-fade-in-up">
                <h2 className="text-2xl font-bold text-on-surface mb-6">Recorded Classification Distribution</h2>
                <div className="bg-surface-container-lowest rounded-xl p-8 card-shadow space-y-4">
                  {Object.entries(stats.status_distribution).map(([status, count]) => {
                    const percentage = stats.total_scans > 0 ? (count / stats.total_scans) * 100 : 0
                    return (
                      <div key={status}>
                        <div className="flex justify-between mb-2">
                          <span className="text-on-surface font-semibold">{status}</span>
                          <span className="text-on-surface-variant">{count} ({percentage.toFixed(0)}%)</span>
                        </div>
                        <div className="bg-surface-container rounded-full h-3 overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${percentage}%`, backgroundColor: status === 'E-Waste' ? 'var(--error)' : 'var(--primary)' }}></div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </section>
            )}

            <section className="grid grid-cols-1 md:grid-cols-3 gap-6" aria-label="Interpretation boundaries">
              <div className="bg-surface-container-lowest p-6 rounded-xl card-shadow">
                <h3 className="font-bold text-on-surface mb-2">Per-user scope</h3>
                <p className="text-sm text-on-surface-variant">Counts include only records associated with the current authenticated user.</p>
              </div>
              <div className="bg-surface-container-lowest p-6 rounded-xl card-shadow">
                <h3 className="font-bold text-on-surface mb-2">Model output</h3>
                <p className="text-sm text-on-surface-variant">Classification scores and condition labels are not certified inspection results.</p>
              </div>
              <div className="bg-surface-container-lowest p-6 rounded-xl card-shadow">
                <h3 className="font-bold text-on-surface mb-2">No impact claim</h3>
                <p className="text-sm text-on-surface-variant">Recorded activity does not establish recycling, emissions reduction, adoption, or institutional impact.</p>
              </div>
            </section>
          </>
        )}
      </div>
    </AnimatedPage>
  )
}

export default Dashboard
