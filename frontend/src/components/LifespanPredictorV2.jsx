import { useEffect, useRef, useState } from 'react'
import { toast } from 'react-hot-toast'
import { motion } from 'framer-motion'
import { useApiFetch } from '../utils/api'
import { createPdfFilename, createPdfReport, exportPdf } from '../utils/pdf'
import AnimatedPage from './AnimatedPage'
import { fadeInUp, stagger } from '../utils/motion'
import { useCountUp } from '../utils/useCountUp'

/**
 * @typedef {{ age: number, usage: number, temperature: number, power: number, environment: number, service: number, software: number }} LifespanWeights
 * @typedef {{
 *   deviceType: string,
 *   year: number,
 *   usage: number,
 *   temperature: string,
 *   environment: string,
 *   power: string,
 *   maintenance: string,
 *   software: string,
 *   weights: LifespanWeights,
 * }} LifespanForm
 * @typedef {{ name: string, raw: number, weight: number, weighted: number, label?: string }} FactorDetail
 * @typedef {{
 *   input_snapshot: LifespanForm,
 *   device_type: string,
 *   age: number,
 *   base_lifespan: number,
 *   factors: FactorDetail[],
 *   normalized_weights: Record<string, number>,
 *   health_score: number,
 *   remaining_years: number,
 *   remaining_min: number,
 *   remaining_max: number,
 *   end_of_life: boolean,
 *   co2_avoided_kg: number,
 *   repair_savings_inr: number,
 *   model_requested: string,
 *   model_used: string,
 *   formula_text: string,
 * }} LifespanResult
 */

const DEFAULT_WEIGHTS = {
  age: 0.25,
  usage: 0.20,
  temperature: 0.15,
  power: 0.13,
  environment: 0.10,
  service: 0.05,
  software: 0.12,
}

const DEVICE_TYPES = [
  'Air Conditioner', 'Battery', 'Camera', 'Computer', 'Hard Disk / SSD',
  'Keyboard', 'Laptop', 'Microwave', 'Monitor', 'Motherboard', 'Mouse',
  'Printer', 'Projector', 'Refrigerator', 'Remote Control', 'Router / Switch',
  'Smartphone', 'Smartwatch', 'Television', 'Washing Machine',
]
const TEMP_LEVELS = ['Cool', 'Normal', 'Hot']
const ENV_LEVELS = ['Clean', 'Normal', 'Harsh']
const POWER_LEVELS = ['UPS Protected', 'Direct Grid', 'Frequent Outages']
const MAINT_LEVELS = ['Regular', 'Occasional', 'None']
const SOFTWARE_LEVELS = ['Light', 'Office', 'Heavy']

/** @param {unknown} detail */
function apiDetail(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg).filter(Boolean).join('; ')
  return ''
}

export default function LifespanPredictorV2() {
  const currentYear = new Date().getFullYear()
  const apiFetch = useApiFetch()
  const requestRef = useRef(/** @type {AbortController | null} */ (null))
  const [form, setForm] = useState(/** @type {LifespanForm} */ ({
    deviceType: 'Computer',
    year: currentYear - 2,
    usage: 8,
    temperature: 'Normal',
    environment: 'Normal',
    power: 'Direct Grid',
    maintenance: 'Occasional',
    software: 'Office',
    weights: { ...DEFAULT_WEIGHTS },
  }))
  const [result, setResult] = useState(/** @type {LifespanResult | null} */ (null))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(/** @type {string | null} */ (null))

  useEffect(() => () => requestRef.current?.abort(), [])

  /** @param {Partial<LifespanForm>} patch */
  const updateForm = (patch) => {
    requestRef.current?.abort()
    requestRef.current = null
    setLoading(false)
    setResult(null)
    setError(null)
    setForm((current) => ({ ...current, ...patch }))
  }

  const handlePredict = async () => {
    requestRef.current?.abort()
    const controller = new AbortController()
    requestRef.current = controller
    const snapshot = { ...form, weights: { ...form.weights } }
    setLoading(true)
    setResult(null)
    setError(null)

    try {
      const response = await apiFetch('/api/v1/predict/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_type: snapshot.deviceType,
          manufacturing_year: snapshot.year,
          usage_hours_per_day: snapshot.usage,
          temperature_stress: snapshot.temperature,
          environment: snapshot.environment,
          power_outage_freq: snapshot.power,
          maintenance_frequency: snapshot.maintenance,
          software_load: snapshot.software,
          weights: snapshot.weights,
          model_choice: 'formula',
        }),
        signal: controller.signal,
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(apiDetail(data.detail) || 'Lifespan calculation failed')
      if (requestRef.current === controller) setResult({ ...data, input_snapshot: snapshot })
    } catch (caught) {
      if (controller.signal.aborted || (caught instanceof DOMException && caught.name === 'AbortError')) return
      const message = caught instanceof Error ? caught.message : 'Unable to calculate lifespan.'
      setError(message)
      toast.error(message)
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null
        setLoading(false)
      }
    }
  }

  const remainingYearsCount = useCountUp(result?.remaining_years ?? 0)
  const healthScoreCount = useCountUp((result?.health_score ?? 0) * 100)
  const healthColor = (result?.health_score ?? 0) > 0.7
    ? 'text-primary'
    : (result?.health_score ?? 0) > 0.4
      ? 'text-secondary'
      : 'text-error'

  const handleDownloadPDF = async () => {
    if (!result) return
    const snapshot = result.input_snapshot
    const generatedAt = new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    const report = createPdfReport({
      title: 'E-Waste Lifespan Report',
      subtitle: 'Seven-Factor Device Lifespan Planning Calculation',
      summaryLabel: 'Estimated remaining life',
      summaryValue: `${result.remaining_years} years`,
      summaryDetail: `Health score ${(result.health_score * 100).toFixed(1)}% · Scenario band ${result.remaining_min}–${result.remaining_max} years`,
      sections: [
        {
          heading: 'Submitted inputs',
          rows: [
            { label: 'Device type', value: snapshot.deviceType },
            { label: 'Manufacturing year', value: snapshot.year },
            { label: 'Age', value: `${result.age} years (profile lifespan: ${result.base_lifespan} years)` },
            { label: 'Daily usage', value: `${snapshot.usage} hours` },
            { label: 'Temperature', value: snapshot.temperature },
            { label: 'Environment', value: snapshot.environment },
            { label: 'Power quality', value: snapshot.power },
            { label: 'Maintenance', value: snapshot.maintenance },
            { label: 'Software / workload', value: snapshot.software },
            { label: 'Model used', value: result.model_used },
          ],
        },
        {
          heading: 'Seven-factor breakdown',
          rows: result.factors.map((factor) => ({
            label: `${factor.name} (${factor.label || 'n/a'})`,
            value: `factor ${factor.raw.toFixed(3)} × weight ${factor.weight.toFixed(3)} = ${factor.weighted.toFixed(3)}`,
          })),
        },
        {
          heading: 'Planning proxies',
          rows: [
            { label: 'CO₂ avoidance proxy', value: `${result.co2_avoided_kg.toFixed(1)} kg` },
            { label: 'Repair-cost proxy', value: `₹${result.repair_savings_inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` },
            { label: 'Formula', value: result.formula_text },
          ],
          paragraphs: [
            'This deterministic result uses submitted inputs, profile assumptions, and normalized design weights. It is not a measured failure date, calibrated probability interval, field-validated forecast, or warranty assessment.',
            'Verify current disposal obligations and recycler authorization through official CPCB/MPCB sources before operational use.',
          ],
        },
      ],
      footerLeft: `Generated: ${generatedAt}`,
      footerRight: 'E-Waste Management v3',
    })

    try {
      await exportPdf(report, createPdfFilename(snapshot.deviceType, 'Lifespan_Report'))
      toast.success('Report downloaded')
    } catch {
      toast.error('Could not generate the PDF report')
    }
  }

  return (
    <AnimatedPage>
      <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
        <header className="mb-12 animate-fade-in-down">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">Deterministic seven-factor formula</p>
          <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-4">Lifespan Estimator</h1>
          <p className="text-xl text-on-surface-variant max-w-3xl">Calculate a planning estimate from age, usage, temperature, power, environment, maintenance, and software/workload inputs.</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <section className="lg:col-span-5 animate-fade-in-up">
            <div className="bg-surface-container-lowest rounded-xl p-8 space-y-6 card-shadow">
              <h2 className="text-2xl font-bold text-on-surface">Device Parameters</h2>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="lifespan-device" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Device Type</label>
                  <select id="lifespan-device" value={form.deviceType} onChange={(event) => updateForm({ deviceType: event.target.value })} className="w-full bg-surface-container-highest px-4 py-3 rounded-lg form-field">
                    {DEVICE_TYPES.map((device) => <option key={device} value={device}>{device}</option>)}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <label htmlFor="lifespan-year" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Manufacturing Year</label>
                    <input id="lifespan-year" type="number" min={1970} max={currentYear} value={form.year} onChange={(event) => updateForm({ year: Math.min(currentYear, Math.max(1970, Number.parseInt(event.target.value, 10) || currentYear)) })} className="w-full bg-surface-container-highest px-4 py-3 rounded-lg form-field" required />
                  </div>
                  <div className="space-y-2">
                    <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Age</span>
                    <output htmlFor="lifespan-year" className="block w-full bg-surface-container-highest px-4 py-3 rounded-lg text-on-surface font-semibold">{currentYear - form.year} years</output>
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="lifespan-usage" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Daily Usage ({form.usage}h)</label>
                  <input id="lifespan-usage" type="range" min={0} max={24} step={1} value={form.usage} aria-valuetext={`${form.usage} hours per day`} onChange={(event) => updateForm({ usage: Number.parseInt(event.target.value, 10) })} className="w-full accent-primary" />
                </div>

                <ChoiceGroup id="temperature" label="Temperature" options={TEMP_LEVELS} value={form.temperature} onChange={(temperature) => updateForm({ temperature })} />
                <ChoiceGroup id="environment" label="Environment" options={ENV_LEVELS} value={form.environment} onChange={(environment) => updateForm({ environment })} />

                <div className="space-y-2">
                  <label htmlFor="lifespan-power" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Power Quality</label>
                  <select id="lifespan-power" value={form.power} onChange={(event) => updateForm({ power: event.target.value })} className="w-full bg-surface-container-highest px-4 py-3 rounded-lg form-field">
                    {POWER_LEVELS.map((power) => <option key={power} value={power}>{power}</option>)}
                  </select>
                </div>

                <div className="space-y-2">
                  <label htmlFor="lifespan-maintenance" className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Maintenance</label>
                  <select id="lifespan-maintenance" value={form.maintenance} onChange={(event) => updateForm({ maintenance: event.target.value })} className="w-full bg-surface-container-highest px-4 py-3 rounded-lg form-field">
                    {MAINT_LEVELS.map((maintenance) => <option key={maintenance} value={maintenance}>{maintenance}</option>)}
                  </select>
                </div>

                <ChoiceGroup id="software" label="Software / Workload" options={SOFTWARE_LEVELS} value={form.software} onChange={(software) => updateForm({ software })} />
              </div>

              <button type="button" onClick={handlePredict} disabled={loading} className="w-full bg-primary text-on-primary py-4 rounded-xl font-bold text-lg hover:opacity-90 disabled:opacity-50">
                {loading ? 'Calculating…' : 'Calculate Lifespan Estimate'}
              </button>
            </div>
          </section>

          <section className="lg:col-span-7 animate-fade-in-up" aria-live="polite">
            {error && <div role="alert" className="mb-6 p-4 bg-error-container text-on-error-container rounded-xl">{error}</div>}
            {loading && <div className="bg-surface-container-lowest rounded-xl p-12 text-center card-shadow" role="status">Calculating the seven-factor estimate…</div>}
            {!loading && result ? (
              <div className="space-y-6">
                <div className={`bg-surface-container-lowest rounded-xl p-8 card-shadow ${result.end_of_life ? 'border-2 border-error/30' : ''}`}>
                  <h2 className="text-2xl font-bold text-on-surface mb-6">{result.end_of_life ? 'Profile Lifespan Reached' : 'Planning Estimate'}</h2>
                  <div className="grid grid-cols-2 gap-6">
                    <div className="text-center p-6 bg-surface-container rounded-xl">
                      <p className={`text-4xl font-black ${healthColor}`}>{remainingYearsCount.toFixed(2)}</p>
                      <p className="text-sm text-on-surface-variant mt-1">Estimated years remaining</p>
                    </div>
                    <div className="text-center p-6 bg-surface-container rounded-xl">
                      <p className="text-4xl font-black text-secondary">{healthScoreCount.toFixed(0)}%</p>
                      <p className="text-sm text-on-surface-variant mt-1">Formula health score</p>
                    </div>
                  </div>
                  <p className="text-center text-sm text-on-surface-variant mt-4">Scenario band {result.remaining_min}–{result.remaining_max} years · model used: {result.model_used}</p>
                </div>

                <div className="bg-surface-container-lowest rounded-xl p-8 card-shadow">
                  <h3 className="text-lg font-bold text-on-surface mb-4">Planning Proxies</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-4 bg-surface-container rounded-xl">
                      <p className="text-2xl font-black text-primary">{result.co2_avoided_kg.toFixed(1)}</p>
                      <p className="text-xs text-on-surface-variant">CO₂ avoidance proxy (kg)</p>
                    </div>
                    <div className="text-center p-4 bg-surface-container rounded-xl">
                      <p className="text-2xl font-black text-secondary">₹{result.repair_savings_inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</p>
                      <p className="text-xs text-on-surface-variant">Repair-cost proxy</p>
                    </div>
                  </div>
                </div>

                <div className="bg-surface-container-lowest rounded-xl p-8 card-shadow">
                  <h3 className="text-lg font-bold text-on-surface mb-4">Factor Breakdown</h3>
                  <motion.div className="space-y-3" variants={stagger} initial="hidden" animate="visible">
                    {result.factors.map((factor) => {
                      const percentage = (factor.weighted / Math.max(result.health_score, 0.001)) * 100
                      return (
                        <motion.div key={factor.name} variants={fadeInUp}>
                          <div className="flex flex-wrap justify-between gap-2 mb-1">
                            <span className="text-sm font-semibold text-on-surface capitalize">{factor.name} <span className="text-on-surface-variant font-normal">({factor.label || 'n/a'})</span></span>
                            <span className="text-xs font-mono text-on-surface-variant">{factor.weight.toFixed(3)} × {factor.raw.toFixed(3)} = {factor.weighted.toFixed(3)}</span>
                          </div>
                          <div className="w-full bg-surface-container rounded-full h-2 overflow-hidden"><div className="bg-primary h-2 rounded-full" style={{ width: `${Math.min(percentage, 100)}%` }}></div></div>
                        </motion.div>
                      )
                    })}
                  </motion.div>
                  <p className="text-xs text-on-surface-variant mt-4">{result.formula_text}</p>
                </div>

                <div className="border-l-4 border-secondary bg-secondary/5 rounded-r-xl p-4 text-sm text-on-surface-variant">
                  This is a deterministic planning estimate from submitted inputs and design assumptions. The displayed band is not a calibrated confidence interval, measured failure date, or warranty assessment.
                </div>

                <button type="button" onClick={handleDownloadPDF} className="w-full bg-secondary text-on-secondary py-3.5 rounded-xl font-bold hover:opacity-90 flex items-center justify-center gap-2">
                  <span className="material-symbols-outlined text-lg" aria-hidden="true">download</span>
                  Download PDF Report
                </button>
              </div>
            ) : !loading && !error ? (
              <div className="h-full min-h-80 flex items-center justify-center bg-surface-container-lowest rounded-xl card-shadow">
                <div className="text-center p-12"><span className="material-symbols-outlined text-6xl text-outline mb-4" aria-hidden="true">hourglass_empty</span><p className="text-on-surface-variant">Submit device parameters to calculate an estimate.</p></div>
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </AnimatedPage>
  )
}

/** @param {{ id: string, label: string, options: string[], value: string, onChange: (value: string) => void }} props */
function ChoiceGroup({ id, label, options, value, onChange }) {
  return (
    <div className="space-y-2">
      <span id={`${id}-label`} className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">{label}</span>
      <div className="grid grid-cols-3 gap-1 bg-surface-container rounded-lg p-1" role="group" aria-labelledby={`${id}-label`}>
        {options.map((option) => (
          <button key={option} type="button" aria-pressed={value === option} onClick={() => onChange(option)} className={`py-2 rounded-md text-xs font-semibold transition ${value === option ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}>
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}
