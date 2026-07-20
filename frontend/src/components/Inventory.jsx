import { useEffect, useRef, useState } from 'react'
import { toast } from 'react-hot-toast'
import { motion } from 'framer-motion'
import { useApiFetch } from '../utils/api'
import { createPdfFilename, createPdfReport, exportPdf } from '../utils/pdf'
import AnimatedPage from './AnimatedPage'
import { fadeInUp, stagger } from '../utils/motion'

/**
 * @typedef {{
 *   units: number,
 *   device_type: string,
 *   daily_hours: number,
 *   tdp: number,
 *   energy_rating: string,
 *   zip_code: string,
 *   lifespan_years: number,
 * }} CarbonForm
 * @typedef {{
 *   input_snapshot: CarbonForm,
 *   total_tco2e: number,
 *   trees_planted: number,
 *   embodied_kg: number,
 *   operational_kg: number,
 *   lifespan_years: number,
 *   grid_intensity: number,
 * }} CarbonResult
 */

const DEVICE_OPTIONS = [
  { value: 'Air Conditioner', label: 'Air Conditioner', tdp: 1500, lifespan: 10 },
  { value: 'Battery', label: 'Battery', tdp: 0, lifespan: 3 },
  { value: 'Camera', label: 'Camera', tdp: 5, lifespan: 5 },
  { value: 'Computer', label: 'Computer / Desktop', tdp: 200, lifespan: 6 },
  { value: 'Hard Disk / SSD', label: 'Hard Disk / SSD', tdp: 8, lifespan: 5 },
  { value: 'Keyboard', label: 'Keyboard', tdp: 2, lifespan: 4 },
  { value: 'Laptop', label: 'Laptop', tdp: 65, lifespan: 5 },
  { value: 'Microwave', label: 'Microwave', tdp: 1100, lifespan: 8 },
  { value: 'Monitor', label: 'Monitor', tdp: 35, lifespan: 7 },
  { value: 'Motherboard', label: 'Motherboard', tdp: 50, lifespan: 8 },
  { value: 'Mouse', label: 'Mouse', tdp: 2, lifespan: 3 },
  { value: 'Printer', label: 'Printer', tdp: 50, lifespan: 5 },
  { value: 'Projector', label: 'Projector', tdp: 250, lifespan: 5 },
  { value: 'Refrigerator', label: 'Refrigerator', tdp: 150, lifespan: 12 },
  { value: 'Remote Control', label: 'Remote Control', tdp: 0, lifespan: 6 },
  { value: 'Router / Switch', label: 'Router / Switch', tdp: 15, lifespan: 6 },
  { value: 'Smartphone', label: 'Smartphone', tdp: 5, lifespan: 4 },
  { value: 'Smartwatch', label: 'Smartwatch', tdp: 2, lifespan: 3 },
  { value: 'Television', label: 'Television', tdp: 100, lifespan: 8 },
  { value: 'Washing Machine', label: 'Washing Machine', tdp: 500, lifespan: 10 },
]

/** @param {unknown} detail */
function apiDetail(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg).filter(Boolean).join('; ')
  return ''
}

function Inventory() {
  const [formData, setFormData] = useState(/** @type {CarbonForm} */ ({
    units: 1,
    device_type: 'Computer',
    daily_hours: 8,
    tdp: 200,
    energy_rating: 'A',
    zip_code: '400001',
    lifespan_years: 6,
  }))
  const [result, setResult] = useState(/** @type {CarbonResult | null} */ (null))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(/** @type {string | null} */ (null))
  const apiFetch = useApiFetch()
  const requestRef = useRef(/** @type {AbortController | null} */ (null))

  useEffect(() => () => requestRef.current?.abort(), [])

  /** @param {Partial<CarbonForm>} patch */
  const updateFormData = (patch) => {
    requestRef.current?.abort()
    requestRef.current = null
    setLoading(false)
    setResult(null)
    setError(null)
    setFormData((current) => ({ ...current, ...patch }))
  }

  /** @param {import('react').ChangeEvent<HTMLSelectElement>} event */
  const handleDeviceChange = (event) => {
    const value = event.target.value
    const option = DEVICE_OPTIONS.find((device) => device.value === value)
    updateFormData({
      device_type: value,
      tdp: option?.tdp ?? formData.tdp,
      lifespan_years: option?.lifespan ?? formData.lifespan_years,
    })
  }

  const runCalculation = async () => {
    requestRef.current?.abort()
    const controller = new AbortController()
    requestRef.current = controller
    const snapshot = { ...formData }
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await apiFetch('/api/v1/carbon/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(snapshot),
        signal: controller.signal,
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(apiDetail(data.detail) || 'Carbon calculation failed')
      if (requestRef.current === controller) setResult({ ...data, input_snapshot: snapshot })
    } catch (caught) {
      if (controller.signal.aborted) return
      const message = caught instanceof Error
        ? caught.message
        : 'Failed to calculate carbon footprint. Please try again.'
      setError(message)
      toast.error(message)
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null
        setLoading(false)
      }
    }
  }

  /** @param {import('react').FormEvent<HTMLFormElement>} event */
  const handleSubmit = (event) => {
    event.preventDefault()
    runCalculation()
  }

  const handleDownloadPDF = async () => {
    if (!result) return
    const snapshot = result.input_snapshot
    const generatedAt = new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    const totalKg = Number(result.embodied_kg) + Number(result.operational_kg)
    const embodiedPct = totalKg > 0 ? (Number(result.embodied_kg) / totalKg) * 100 : 0
    const operationalPct = totalKg > 0 ? (Number(result.operational_kg) / totalKg) * 100 : 0
    const report = createPdfReport({
      title: 'Carbon Footprint Report',
      subtitle: 'Maharashtra Educational Sector — Device Carbon Analysis',
      summaryLabel: 'Estimated lifecycle emissions',
      summaryValue: `${result.total_tco2e} tCO₂e`,
      summaryDetail: `Planning equivalence: ${result.trees_planted} tree-years (rounded up)`,
      sections: [
        {
          heading: 'Calculation inputs',
          rows: [
            { label: 'Device type', value: snapshot.device_type },
            { label: 'Units', value: snapshot.units },
            { label: 'Daily usage', value: `${snapshot.daily_hours} hours` },
            { label: 'Power draw', value: `${snapshot.tdp} W` },
            { label: 'Energy rating', value: snapshot.energy_rating },
            { label: 'Lifespan', value: `${snapshot.lifespan_years} years` },
            { label: 'Postal code', value: snapshot.zip_code },
            { label: 'Grid intensity', value: `${result.grid_intensity} kg CO₂/kWh` },
          ],
        },
        {
          heading: 'Emissions breakdown',
          rows: [
            { label: 'Embodied emissions', value: `${result.embodied_kg} kg (${embodiedPct.toFixed(1)}%)` },
            { label: 'Operational emissions', value: `${result.operational_kg} kg (${operationalPct.toFixed(1)}%)` },
            { label: 'Total', value: `${totalKg.toFixed(1)} kg CO₂e` },
          ],
          paragraphs: [
            'These outputs are deterministic planning estimates based on device profiles, submitted usage, energy-rating multipliers, and grid-intensity lookup values. They are not measured emissions, uncertainty intervals, or a certified product life-cycle assessment.',
          ],
        },
      ],
      footerLeft: `Generated: ${generatedAt}`,
      footerRight: 'E-Waste Management v3',
    })

    try {
      await exportPdf(report, createPdfFilename(snapshot.device_type, 'Carbon_Report'))
      toast.success('Report downloaded')
    } catch {
      toast.error('Could not generate the PDF report')
    }
  }

  return (
    <AnimatedPage>
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
      <header className="mb-12 animate-fade-in-down">
        <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-4">Carbon Calculator</h1>
        <p className="text-xl text-on-surface-variant max-w-2xl">Estimate the lifetime carbon footprint of IT-lab electronics including AC, computers, projectors, and more.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <section className="lg:col-span-5 animate-fade-in-up stagger-1">
          <form onSubmit={handleSubmit} className="bg-surface-container-lowest rounded-xl p-8 space-y-6 hover-lift card-shadow">
            <div className="flex items-center gap-3 mb-2">
              <span className="material-symbols-outlined text-primary">eco</span>
              <h2 className="text-2xl font-bold text-on-surface">Device Parameters</h2>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="carbon-device" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Device Type</label>
                <select id="carbon-device" value={formData.device_type} onChange={handleDeviceChange} className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field">
                  {DEVICE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label htmlFor="carbon-units" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Units</label>
                  <input
                    id="carbon-units"
                    type="number"
                    min={1}
                    max={100_000}
                    step={1}
                    value={formData.units}
                    onChange={(event) => updateFormData({ units: Math.max(1, Number.parseInt(event.target.value, 10) || 1) })}
                    className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="carbon-lifespan" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Lifespan (yrs)</label>
                  <input
                    id="carbon-lifespan"
                    type="number"
                    min={1}
                    max={50}
                    step={0.5}
                    value={formData.lifespan_years}
                    onChange={(event) => updateFormData({ lifespan_years: Math.max(1, Number.parseFloat(event.target.value) || 1) })}
                    className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label htmlFor="carbon-hours" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Daily Hours</label>
                  <input
                    id="carbon-hours"
                    type="number"
                    min={0}
                    max={24}
                    step={0.5}
                    value={formData.daily_hours}
                    onChange={(event) => updateFormData({ daily_hours: Math.max(0, Number.parseFloat(event.target.value) || 0) })}
                    className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label htmlFor="carbon-tdp" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Power (W / TDP)</label>
                  <input
                    id="carbon-tdp"
                    type="number"
                    min={0}
                    max={10_000}
                    step={1}
                    value={formData.tdp}
                    onChange={(event) => updateFormData({ tdp: Math.max(0, Number.parseFloat(event.target.value) || 0) })}
                    className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="carbon-rating" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Energy Rating</label>
                <select id="carbon-rating" value={formData.energy_rating} onChange={(event) => updateFormData({ energy_rating: event.target.value })} className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field">
                  <option value="A">A (Most Efficient)</option>
                  <option value="B">B</option>
                  <option value="C">C</option>
                  <option value="D">D (Least Efficient)</option>
                </select>
              </div>

              <div className="space-y-2">
                <label htmlFor="carbon-postal-code" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Postal Code</label>
                <input
                  id="carbon-postal-code"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  value={formData.zip_code}
                  onChange={(event) => updateFormData({ zip_code: event.target.value.replace(/\D/g, '').slice(0, 6) })}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                  placeholder="400001"
                  maxLength={6}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 bg-primary text-on-primary py-4 rounded-xl font-bold text-lg hover:opacity-90 transition-all active:scale-[0.98] shadow-lg shadow-primary/20 disabled:opacity-50 hover:-translate-y-0.5 hover:shadow-xl btn-ripple"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="material-symbols-outlined animate-spin">progress_activity</span>
                  Calculating...
                </span>
              ) : 'Calculate Carbon Footprint'}
            </button>
          </form>
        </section>

        <section className="lg:col-span-7 animate-fade-in-up stagger-2">
          {error && (
            <div role="alert" className="mb-6 p-4 bg-error-container rounded-xl flex items-center gap-3 animate-scale-in">
              <span className="material-symbols-outlined text-on-error-container" aria-hidden="true">error</span>
              <span className="text-sm font-medium text-on-error-container">{error}</span>
              <button
                type="button"
                onClick={runCalculation}
                className="ml-auto text-sm font-bold text-on-error-container hover:underline"
              >
                Retry
              </button>
            </div>
          )}

          {loading ? (
            <div className="bg-surface-container-lowest rounded-xl p-12 animate-fade-in">
              <div className="flex flex-col items-center justify-center gap-4">
                <span className="material-symbols-outlined text-5xl text-primary animate-spin">eco</span>
                <div className="text-center">
                  <p className="text-lg font-semibold text-on-surface">Calculating carbon footprint...</p>
                  <p className="text-sm text-on-surface-variant mt-1">Analyzing device parameters and grid intensity</p>
                </div>
                <div className="w-full bg-surface-container rounded-full h-2 overflow-hidden mt-4">
                  <div className="bg-primary h-2 rounded-full animate-pulse" style={{width: '50%'}}></div>
                </div>
              </div>
            </div>
          ) : result ? (
            <motion.div className="space-y-6" variants={stagger} initial="hidden" animate="visible">
              <motion.div className="bg-surface-container-lowest rounded-xl p-8 animate-scale-in-bounce hover-lift card-shadow" variants={fadeInUp}>
                <h2 className="text-2xl font-bold text-on-surface mb-6">Environmental Impact Summary</h2>
                <div className="grid grid-cols-2 gap-6">
                  <div className="text-center p-6 bg-surface-container rounded-xl hover:bg-surface-container-high transition-all duration-300 transform hover:scale-105">
                    <p className="text-4xl font-black text-primary">{result.total_tco2e}</p>
                    <p className="text-sm text-on-surface-variant mt-1">Total tCO₂e</p>
                  </div>
                  <div className="text-center p-6 bg-surface-container rounded-xl hover:bg-surface-container-high transition-all duration-300 transform hover:scale-105">
                    <p className="text-4xl font-black text-secondary">{result.trees_planted}</p>
                    <p className="text-sm text-on-surface-variant mt-1">Tree-year equivalents</p>
                  </div>
                </div>
                <p className="text-center text-sm text-on-surface-variant mt-4">Over {result.lifespan_years}-year lifespan · tree-year value uses the documented 22 kg CO₂/year planning basis</p>
                <p className="mt-4 p-4 rounded-lg bg-secondary/5 border-l-4 border-secondary text-sm text-on-surface-variant">Deterministic scenario estimate only. Profile factors, grid lookup values, and submitted usage are assumptions; this is not measured emissions, an uncertainty interval, or a certified product LCA.</p>
              </motion.div>

              <motion.div className="bg-surface-container-lowest rounded-xl p-8 animate-fade-in-up hover-lift card-shadow" style={{animationDelay: '0.15s'}} variants={fadeInUp}>
                <h3 className="text-lg font-bold text-on-surface mb-4">Emissions Breakdown</h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-on-surface-variant">Embodied Carbon</span>
                      <span className="font-semibold">{result.embodied_kg} kg CO₂</span>
                    </div>
                    <div className="w-full bg-surface-container rounded-full h-3 overflow-hidden">
                      <div className="bg-primary h-3 rounded-full transition-all duration-1000" style={{width: `${(result.embodied_kg / (result.embodied_kg + result.operational_kg)) * 100}%`}}></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-on-surface-variant">Operational Carbon</span>
                      <span className="font-semibold">{result.operational_kg} kg CO₂</span>
                    </div>
                    <div className="w-full bg-surface-container rounded-full h-3 overflow-hidden">
                      <div className="bg-secondary h-3 rounded-full transition-all duration-1000" style={{width: `${(result.operational_kg / (result.embodied_kg + result.operational_kg)) * 100}%`}}></div>
                    </div>
                  </div>
                </div>
                <div className="mt-6 pt-6 border-t border-outline-variant">
                  <div className="flex justify-between items-center p-3 bg-surface-container rounded-lg">
                    <span className="text-on-surface-variant">Grid Intensity</span>
                    <span className="font-bold text-on-surface">{result.grid_intensity} kg CO₂/kWh</span>
                  </div>
                </div>
              </motion.div>

              <motion.button
                onClick={handleDownloadPDF}
                className="w-full bg-secondary text-white py-3.5 rounded-xl font-bold hover:opacity-90 transition-all flex items-center justify-center gap-2 hover:-translate-y-0.5 hover:shadow-lg active:scale-[0.98] btn-ripple"
                variants={fadeInUp}
              >
                <span className="material-symbols-outlined text-lg">download</span>
                Download PDF Report
              </motion.button>
            </motion.div>
          ) : (
            <div className="h-full flex items-center justify-center bg-surface-container-lowest rounded-xl hover-lift card-shadow animate-scale-in">
              <div className="text-center p-12">
                <span className="material-symbols-outlined text-6xl text-outline mb-4">calculate</span>
                <p className="text-on-surface-variant">Enter device parameters to calculate carbon footprint</p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
    </AnimatedPage>
  )
}

export default Inventory
