import { useEffect, useRef, useState } from 'react'
import { toast } from 'react-hot-toast'
import AnimatedPage from './AnimatedPage'
import { useApiFetch } from '../utils/api'

/**
 * @typedef {{
 *   year_offset: number,
 *   expected_eol_devices: number,
 *   expected_e_waste_kg: number,
 *   scenario_min_eol_devices: number,
 *   scenario_max_eol_devices: number,
 * }} AnnualGenerationEstimate
 * @typedef {{
 *   annual: AnnualGenerationEstimate[],
 *   assumptions: string[],
 *   expected_eol_devices_within_horizon: number,
 *   expected_e_waste_kg_within_horizon: number,
 *   expected_devices_remaining_after_horizon: number,
 *   uncertainty_note: string,
 *   method: string,
 *   formula: string,
 * }} GenerationForecastResult
 */

const DEVICE_TYPES = [
  'Air Conditioner', 'Battery', 'Camera', 'Computer', 'Hard Disk / SSD',
  'Keyboard', 'Laptop', 'Microwave', 'Monitor', 'Motherboard', 'Mouse',
  'Printer', 'Projector', 'Refrigerator', 'Remote Control', 'Router / Switch',
  'Smartphone', 'Smartwatch', 'Television', 'Washing Machine',
]

let nextCohortId = 1

function createCohort() {
  return {
    id: nextCohortId++,
    device_type: 'Computer',
    quantity: 25,
    average_age_years: 3,
  }
}

/** @param {unknown} value */
function numberFrom(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

/** @param {unknown} error */
function errorMessage(error) {
  return error instanceof Error ? error.message : 'Unable to generate the forecast.'
}

/** @param {unknown} detail */
function apiDetail(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg).filter(Boolean).join('; ')
  }
  return ''
}

/** @param {unknown} value @param {number} [digits] */
function formatNumber(value, digits = 1) {
  return numberFrom(value).toLocaleString('en-IN', { maximumFractionDigits: digits })
}

export default function GenerationForecast() {
  const apiFetch = useApiFetch()
  const [cohorts, setCohorts] = useState(() => [createCohort()])
  const [horizonYears, setHorizonYears] = useState(10)
  const [sensitivityPercent, setSensitivityPercent] = useState(20)
  const [result, setResult] = useState(/** @type {GenerationForecastResult | null} */ (null))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(/** @type {string | null} */ (null))
  const requestRef = useRef(/** @type {AbortController | null} */ (null))

  useEffect(() => () => requestRef.current?.abort(), [])

  const clearResult = () => {
    requestRef.current?.abort()
    requestRef.current = null
    setLoading(false)
    setResult(null)
    setError(null)
  }

  /** @param {number} id @param {'device_type' | 'quantity' | 'average_age_years'} field @param {string | number} value */
  const updateCohort = (id, field, value) => {
    clearResult()
    setCohorts((items) => items.map((item) => (
      item.id === id ? { ...item, [field]: value } : item
    )))
  }

  const addCohort = () => {
    clearResult()
    setCohorts((items) => [...items, createCohort()])
  }

  /** @param {number} id */
  const removeCohort = (id) => {
    clearResult()
    setCohorts((items) => items.filter((item) => item.id !== id))
  }

  /** @param {import('react').FormEvent<HTMLFormElement>} event */
  const handleSubmit = async (event) => {
    event.preventDefault()
    requestRef.current?.abort()
    const controller = new AbortController()
    requestRef.current = controller
    setLoading(true)
    setError(null)
    setResult(null)

    const payload = {
      cohorts: cohorts.map(({ device_type, quantity, average_age_years }) => ({
        device_type,
        quantity,
        average_age_years,
      })),
      horizon_years: horizonYears,
      lifespan_sensitivity_fraction: sensitivityPercent / 100,
    }

    try {
      const response = await apiFetch('/api/v1/generation/forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(apiDetail(data.detail) || 'The forecast service rejected these cohort inputs.')
      }
      if (requestRef.current === controller) setResult(data)
    } catch (caught) {
      if (controller.signal.aborted) return
      const message = errorMessage(caught)
      setError(message)
      toast.error(message)
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null
        setLoading(false)
      }
    }
  }

  const annual = Array.isArray(result?.annual) ? result.annual : []
  const assumptions = Array.isArray(result?.assumptions) ? result.assumptions : []

  return (
    <AnimatedPage>
      <div className="pt-32 pb-20 px-6 sm:px-8 max-w-7xl mx-auto page-transition">
        <header className="mb-10 animate-fade-in-down">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Assumption-based planning calculation</p>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-on-surface tracking-tight mb-4">E-Waste Generation Forecast</h1>
          <p className="text-lg text-on-surface-variant max-w-3xl">
            Project when currently in-service cohorts may reach end of life. The fixed conditional Weibull curve is not fitted to observed failures or disposal records, and projected end of life is not the same as collected waste.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <section className="lg:col-span-7" aria-labelledby="cohort-heading">
            <form onSubmit={handleSubmit} className="bg-surface-container-lowest rounded-xl p-6 sm:p-8 card-shadow space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 id="cohort-heading" className="text-2xl font-bold text-on-surface">Current inventory cohorts</h2>
                  <p className="text-sm text-on-surface-variant mt-1">Group in-service units of one device type with a shared current average age.</p>
                </div>
                <button type="button" onClick={addCohort} className="px-4 py-2 rounded-full bg-primary-container text-on-primary-container font-bold text-sm hover:opacity-90">
                  + Add cohort
                </button>
              </div>

              <div className="space-y-4">
                {cohorts.map((cohort, index) => {
                  const prefix = `cohort-${cohort.id}`
                  return (
                    <fieldset key={cohort.id} className="border border-outline-variant rounded-xl p-4 sm:p-5">
                      <legend className="px-2 text-sm font-bold text-primary">Cohort {index + 1}</legend>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        <div>
                          <label htmlFor={`${prefix}-device`} className="block text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2">Device type</label>
                          <select id={`${prefix}-device`} value={cohort.device_type} onChange={(event) => updateCohort(cohort.id, 'device_type', event.target.value)} className="w-full bg-surface-container-highest rounded-lg px-3 py-3 form-field">
                            {DEVICE_TYPES.map((device) => <option key={device} value={device}>{device}</option>)}
                          </select>
                        </div>
                        <div>
                          <label htmlFor={`${prefix}-quantity`} className="block text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2">In-service units</label>
                          <input id={`${prefix}-quantity`} type="number" min={1} max={10_000_000} step={1} required value={cohort.quantity} onChange={(event) => updateCohort(cohort.id, 'quantity', Math.max(1, Number.parseInt(event.target.value, 10) || 1))} className="w-full bg-surface-container-highest rounded-lg px-3 py-3 form-field" />
                        </div>
                        <div>
                          <label htmlFor={`${prefix}-age`} className="block text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2">Average age (years)</label>
                          <input id={`${prefix}-age`} type="number" min={0} max={100} step={0.25} required value={cohort.average_age_years} onChange={(event) => updateCohort(cohort.id, 'average_age_years', Math.max(0, numberFrom(event.target.value)))} className="w-full bg-surface-container-highest rounded-lg px-3 py-3 form-field" />
                        </div>
                      </div>
                      {cohorts.length > 1 && (
                        <button type="button" onClick={() => removeCohort(cohort.id)} className="mt-4 text-sm font-bold text-error hover:underline" aria-label={`Remove cohort ${index + 1}`}>
                          Remove cohort
                        </button>
                      )}
                    </fieldset>
                  )
                })}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="forecast-years" className="block text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2">Forecast horizon (years)</label>
                  <input id="forecast-years" type="number" min={1} max={30} step={1} value={horizonYears} onChange={(event) => { clearResult(); setHorizonYears(Math.min(30, Math.max(1, Number.parseInt(event.target.value, 10) || 1))) }} className="w-full bg-surface-container-highest rounded-lg px-3 py-3 form-field" required />
                </div>
                <div>
                  <label htmlFor="forecast-sensitivity" className="block text-xs font-bold uppercase tracking-wider text-on-surface-variant mb-2">Lifespan sensitivity (±%)</label>
                  <input id="forecast-sensitivity" type="number" min={0} max={50} step={1} value={sensitivityPercent} onChange={(event) => { clearResult(); setSensitivityPercent(Math.min(50, Math.max(0, numberFrom(event.target.value)))) }} className="w-full bg-surface-container-highest rounded-lg px-3 py-3 form-field" required />
                </div>
              </div>

              <div className="rounded-lg bg-secondary/5 border border-secondary/20 p-4 text-sm text-on-surface-variant">
                Device lifespan and unit mass come from the shared planning profile. The lifespan sensitivity changes that profile by the displayed fraction; it does not create a confidence interval.
              </div>

              <button type="submit" disabled={loading || cohorts.length === 0} className="w-full bg-primary text-on-primary py-4 rounded-xl font-bold text-lg disabled:opacity-50 hover:opacity-90">
                {loading ? 'Generating forecast…' : 'Generate planning forecast'}
              </button>
            </form>
          </section>

          <section className="lg:col-span-5" aria-labelledby="forecast-result-heading" aria-live="polite">
            <div className="bg-surface-container-low rounded-xl p-6 sm:p-8 card-shadow min-h-72">
              <h2 id="forecast-result-heading" className="text-2xl font-bold text-on-surface mb-3">Projection</h2>
              {error && <div role="alert" className="p-4 bg-error-container text-on-error-container rounded-xl mb-4">{error}</div>}
              {!result && !loading && !error && (
                <p className="text-on-surface-variant">Add one or more cohorts, then generate a forecast to see expected annual end-of-life devices and mass.</p>
              )}
              {loading && <p className="text-on-surface-variant">Projecting conditional cohort survival…</p>}
              {result && (
                <div className="space-y-5">
                  <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3 gap-3">
                    <div className="bg-surface-container-lowest rounded-xl p-4 text-center">
                      <p className="text-2xl font-black text-primary">{formatNumber(result.expected_eol_devices_within_horizon)}</p>
                      <p className="text-xs text-on-surface-variant">expected EOL devices</p>
                    </div>
                    <div className="bg-surface-container-lowest rounded-xl p-4 text-center">
                      <p className="text-2xl font-black text-secondary">{formatNumber(result.expected_e_waste_kg_within_horizon)}</p>
                      <p className="text-xs text-on-surface-variant">expected kg</p>
                    </div>
                    <div className="bg-surface-container-lowest rounded-xl p-4 text-center">
                      <p className="text-2xl font-black text-on-surface">{formatNumber(result.expected_devices_remaining_after_horizon)}</p>
                      <p className="text-xs text-on-surface-variant">expected remaining</p>
                    </div>
                  </div>

                  {annual.length > 0 && (
                    <div className="space-y-2" aria-label="Annual generation estimates">
                      {annual.map((item) => (
                        <div key={item.year_offset} className="rounded-lg bg-surface-container-lowest px-4 py-3">
                          <div className="flex items-center justify-between gap-4">
                            <span className="font-semibold text-on-surface">Year +{item.year_offset}</span>
                            <span className="font-black text-primary">{formatNumber(item.expected_eol_devices)} devices</span>
                          </div>
                          <p className="text-xs text-on-surface-variant mt-1">
                            {formatNumber(item.expected_e_waste_kg)} kg · lifespan-sensitivity range {formatNumber(item.scenario_min_eol_devices)}–{formatNumber(item.scenario_max_eol_devices)} devices
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="border-l-4 border-secondary bg-secondary/5 rounded-r-lg p-4 text-sm text-on-surface-variant leading-relaxed">
                    <strong className="text-on-surface">Interpretation boundary:</strong> {result.uncertainty_note}
                  </div>

                  <details className="rounded-lg border border-outline-variant bg-surface-container-lowest p-4">
                    <summary className="cursor-pointer font-bold text-on-surface">Method and assumptions</summary>
                    <p className="mt-3 text-sm text-on-surface-variant"><strong>Method:</strong> {result.method}</p>
                    <p className="mt-2 text-xs font-mono text-on-surface-variant break-words">{result.formula}</p>
                    <ul className="mt-3 list-disc pl-5 space-y-2 text-sm text-on-surface-variant">
                      {assumptions.map((assumption) => <li key={assumption}>{assumption}</li>)}
                    </ul>
                  </details>
                </div>
              )}
            </div>
          </section>
        </div>
      </div>
    </AnimatedPage>
  )
}
