import { useMemo, useState } from 'react'
import { toast } from 'react-hot-toast'
import html2pdf from 'html2pdf.js'

const DEFAULT_WEIGHTS = {
  age: 0.30,
  usage: 0.25,
  temperature: 0.15,
  power: 0.15,
  environment: 0.10,
  service: 0.05,
}

const DEVICE_TYPES = [
  'Computer', 'Laptop', 'Monitor', 'Printer', 'Projector',
  'Router / Switch', 'Smartphone', 'Motherboard', 'Hard Disk / SSD',
  'Mouse', 'Keyboard', 'Air Conditioner', 'Television', 'Battery', 'Microwave',
]

const TEMP_LEVELS = ['Cool', 'Normal', 'Hot']
const ENV_LEVELS = ['Clean', 'Normal', 'Harsh']
const POWER_LEVELS = ['UPS Protected', 'Direct Grid', 'Frequent Outages']
const MAINT_LEVELS = ['Regular', 'Occasional', 'None']

const clamp = (x, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, x))

function fAge(age, base) {
  if (base <= 0) return 0
  return clamp(1 - age / base)
}

function fUsage(h) {
  if (h <= 4) return 1.0
  if (h <= 8) return 0.85
  if (h <= 12) return 0.7
  return 0.5
}

const F_TEMPERATURE = { Cool: 0.9, Normal: 0.75, Hot: 0.5 }
const F_ENVIRONMENT = { Clean: 0.9, Normal: 0.7, Harsh: 0.4 }
const F_POWER = { 'UPS Protected': 0.9, 'Direct Grid': 0.7, 'Frequent Outages': 0.45 }
const F_SERVICE = { Regular: 0.9, Occasional: 0.7, None: 0.5 }

const DEVICE_BASE_LIFESPAN = {
  'Motherboard': 8, 'Hard Disk / SSD': 5, 'Monitor': 7, 'Mouse': 3,
  'Keyboard': 4, 'Smartphone': 4, 'Computer': 6, 'Printer': 5,
  'Projector': 5, 'Router / Switch': 6, 'Air Conditioner': 10,
  'Laptop': 5, 'Television': 8, 'Battery': 3, 'Microwave': 8,
}
const DEVICE_WEIGHT_KG = {
  'Motherboard': 0.5, 'Hard Disk / SSD': 0.2, 'Monitor': 6.0, 'Mouse': 0.15,
  'Keyboard': 0.5, 'Smartphone': 0.2, 'Computer': 10.0, 'Printer': 8.0,
  'Projector': 3.5, 'Router / Switch': 1.0, 'Air Conditioner': 50.0,
  'Laptop': 2.0, 'Television': 25.0, 'Battery': 2.0, 'Microwave': 12.0,
}
const DEVICE_BASE_REPAIR = {
  'Motherboard': 2500, 'Hard Disk / SSD': 800, 'Monitor': 1500, 'Mouse': 100,
  'Keyboard': 200, 'Smartphone': 3000, 'Computer': 5000, 'Printer': 2500,
  'Projector': 6000, 'Router / Switch': 500, 'Air Conditioner': 5000,
  'Laptop': 6000, 'Television': 8000, 'Battery': 1500, 'Microwave': 2500,
}
const DEVICE_BASE_REPLACE = {
  'Motherboard': 8000, 'Hard Disk / SSD': 4000, 'Monitor': 9000, 'Mouse': 500,
  'Keyboard': 1000, 'Smartphone': 15000, 'Computer': 35000, 'Printer': 12000,
  'Projector': 25000, 'Router / Switch': 3000, 'Air Conditioner': 40000,
  'Laptop': 50000, 'Television': 30000, 'Battery': 4500, 'Microwave': 12000,
}
const DEVICE_MFG_CO2 = {
  'Motherboard': 80, 'Hard Disk / SSD': 40, 'Monitor': 180, 'Mouse': 15,
  'Keyboard': 20, 'Smartphone': 80, 'Computer': 300, 'Printer': 120,
  'Projector': 150, 'Router / Switch': 50, 'Air Conditioner': 600,
  'Laptop': 200, 'Television': 220, 'Battery': 30, 'Microwave': 90,
}
const DEVICE_ANNUAL_CO2 = {
  'Motherboard': 10, 'Hard Disk / SSD': 5, 'Monitor': 40, 'Mouse': 1,
  'Keyboard': 2, 'Smartphone': 20, 'Computer': 80, 'Printer': 30,
  'Projector': 40, 'Router / Switch': 15, 'Air Conditioner': 250,
  'Laptop': 50, 'Television': 60, 'Battery': 5, 'Microwave': 80,
}

function computeLocally(form) {
  const baseLifespan = DEVICE_BASE_LIFESPAN[form.deviceType]
  const currentYear = new Date().getFullYear()
  const age = Math.max(0, currentYear - form.year)

  const total = Object.values(form.weights).reduce((a, b) => a + b, 0)
  const w = total > 0
    ? Object.fromEntries(Object.entries(form.weights).map(([k, v]) => [k, v / total]))
    : { ...DEFAULT_WEIGHTS }

  const factors = [
    { name: 'age', raw: fAge(age, baseLifespan), weight: w.age, weighted: w.age * fAge(age, baseLifespan), label: `${age} / ${baseLifespan} yr` },
    { name: 'usage', raw: fUsage(form.usage), weight: w.usage, weighted: w.usage * fUsage(form.usage), label: `${form.usage} h/day` },
    { name: 'temperature', raw: F_TEMPERATURE[form.temperature], weight: w.temperature, weighted: w.temperature * F_TEMPERATURE[form.temperature], label: form.temperature },
    { name: 'power', raw: F_POWER[form.power], weight: w.power, weighted: w.power * F_POWER[form.power], label: form.power },
    { name: 'environment', raw: F_ENVIRONMENT[form.environment], weight: w.environment, weighted: w.environment * F_ENVIRONMENT[form.environment], label: form.environment },
    { name: 'service', raw: F_SERVICE[form.maintenance], weight: w.service, weighted: w.service * F_SERVICE[form.maintenance], label: form.maintenance },
  ]

  let health = factors.reduce((sum, f) => sum + f.weighted, 0)
  health = clamp(health)

  const eol = age >= baseLifespan
  let remaining = 0, rmin = 0, rmax = 0
  if (!eol) {
    const raw = baseLifespan * health - age
    const maxR = baseLifespan - age
    remaining = Math.max(0, Math.min(raw, maxR))
    const band = baseLifespan * 0.15 * (1 - health)
    rmin = Math.max(0, remaining - band)
    rmax = Math.min(maxR, remaining + band)
  }

  const weight_kg = DEVICE_WEIGHT_KG[form.deviceType]
  const co2 = (weight_kg * 0.05) * (remaining / baseLifespan) * 1000
  const baseRepair = DEVICE_BASE_REPAIR[form.deviceType]
  const savings = baseRepair * health

  return {
    device_type: form.deviceType,
    age,
    base_lifespan: baseLifespan,
    factors,
    health_score: health,
    remaining_years: Number(remaining.toFixed(2)),
    remaining_min: Number(rmin.toFixed(2)),
    remaining_max: Number(rmax.toFixed(2)),
    end_of_life: eol,
    co2_avoided_kg: Number(co2.toFixed(2)),
    repair_savings_inr: Number(savings.toFixed(2)),
    base_repair_cost_inr: baseRepair,
    base_replace_cost_inr: DEVICE_BASE_REPLACE[form.deviceType],
    device_weight_kg: weight_kg,
    manufacturing_co2_kg: DEVICE_MFG_CO2[form.deviceType],
    annual_co2_kg: DEVICE_ANNUAL_CO2[form.deviceType],
    model_used: 'Weighted-Average (v2)',
    formula_text: 'L = Σ(wᵢ × fᵢ(M, T, E, U, P, S))',
  }
}

export default function LifespanPredictorV2() {
  const currentYear = new Date().getFullYear()
  const [form, setForm] = useState({
    deviceType: 'Computer',
    year: currentYear - 2,
    usage: 8,
    temperature: 'Normal',
    environment: 'Normal',
    power: 'Direct Grid',
    maintenance: 'Occasional',
    weights: { ...DEFAULT_WEIGHTS },
  })
  const [result, setResult] = useState(null)

  const livePreview = useMemo(() => computeLocally(form), [form])

  const handlePredict = () => {
    setResult(computeLocally(form))
  }

  const handleReset = () => {
    setForm({
      deviceType: 'Computer',
      year: currentYear - 2,
      usage: 8,
      temperature: 'Normal',
      environment: 'Normal',
      power: 'Direct Grid',
      maintenance: 'Occasional',
      weights: { ...DEFAULT_WEIGHTS },
    })
    setResult(null)
  }

  const display = result ?? livePreview
  const eol = display.end_of_life

  const healthColor = display.health_score > 0.7 ? 'text-primary' : display.health_score > 0.4 ? 'text-secondary' : 'text-error'

  const handleDownloadPDF = () => {
    const generatedAt = new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    const healthPct = (display.health_score * 100).toFixed(1)

    const element = document.createElement('div')
    element.innerHTML = `
      <div style="padding: 40px; font-family: 'Inter', Arial, sans-serif; color: #1a1c18; max-width: 800px;">
        <div style="border-bottom: 3px solid #486730; padding-bottom: 16px; margin-bottom: 24px;">
          <h1 style="color: #486730; margin: 0 0 4px 0; font-size: 26px;">E-Waste Lifespan Report</h1>
          <p style="color: #555; font-size: 13px; margin: 0;">Maharashtra Educational Sector — Device Lifespan Analysis</p>
        </div>

        <div style="background: #f0f4f8; padding: 24px; border-radius: 12px; margin-bottom: 24px; text-align: center;">
          <h2 style="margin: 0 0 6px 0; color: #1a1c18; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Predicted Remaining Life</h2>
          <div style="font-size: 42px; font-weight: 800; color: #486730;">${display.remaining_years} years</div>
          <div style="font-size: 13px; color: #555;">Health Score: <strong>${healthPct}%</strong> · Range: ${display.remaining_min} – ${display.remaining_max} years</div>
        </div>

        <h3 style="color: #486730; margin-bottom: 12px;">Device Details</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc; width: 40%;">Device Type</td><td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>${form.deviceType}</strong></td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Age</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${display.age} years (base: ${display.base_lifespan} years)</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Daily Usage</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${form.usage} hours</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Temperature</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${form.temperature}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Environment</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${form.environment}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Power Quality</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${form.power}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Maintenance</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${form.maintenance}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Device Weight</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${display.device_weight_kg} kg</td></tr>
        </table>

        <h3 style="color: #486730; margin-bottom: 12px;">Factor Breakdown</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
          <tr style="background: #f0f4f8;"><th style="padding: 8px; border: 1px solid #e2e8f0; text-align: left;">Factor</th><th style="padding: 8px; border: 1px solid #e2e8f0;">Raw (fᵢ)</th><th style="padding: 8px; border: 1px solid #e2e8f0;">Weight (wᵢ)</th><th style="padding: 8px; border: 1px solid #e2e8f0;">Weighted</th></tr>
          ${display.factors.map(f => `<tr><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: 600;">${f.name} (${f.label})</td><td style="padding: 8px; border: 1px solid #e2e8f0; text-align: center;">${f.raw.toFixed(3)}</td><td style="padding: 8px; border: 1px solid #e2e8f0; text-align: center;">${f.weight.toFixed(2)}</td><td style="padding: 8px; border: 1px solid #e2e8f0; text-align: center;">${f.weighted.toFixed(3)}</td></tr>`).join('')}
          <tr style="background: #f0f4f8;"><td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: 700;">Health Score</td><td colspan="3" style="padding: 8px; border: 1px solid #e2e8f0; text-align: center; font-weight: 700;">${display.health_score.toFixed(4)}</td></tr>
        </table>

        <h3 style="color: #486730; margin-bottom: 12px;">Environmental Impact</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
          <div style="background: #f0f4f8; padding: 16px; border-radius: 8px; text-align: center;">
            <div style="font-size: 28px; font-weight: 800; color: #486730;">${display.co2_avoided_kg.toFixed(1)} kg</div>
            <div style="font-size: 12px; color: #555;">CO₂ Avoided</div>
          </div>
          <div style="background: #f0f4f8; padding: 16px; border-radius: 8px; text-align: center;">
            <div style="font-size: 28px; font-weight: 800; color: #00629e;">₹${display.repair_savings_inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
            <div style="font-size: 12px; color: #555;">Repair Savings</div>
          </div>
        </div>

        <div style="padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 32px; background: #fff;">
          <h3 style="margin: 0 0 8px 0; color: #555; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Compliance Note</h3>
          <p style="margin: 0; font-size: 12px; line-height: 1.5; color: #555;">
            Under the E-Waste (Management) Rules, 2022, educational institutions in Maharashtra must channel
            end-of-life electronics through authorized recyclers and maintain audit-ready disposal records.
          </p>
        </div>

        <div style="display: flex; justify-content: space-between; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #999;">
          <span>Generated: ${generatedAt}</span>
          <span>E-Waste Management v3</span>
        </div>
      </div>
    `

    const opt = {
      margin: 0.4,
      filename: `${form.deviceType.replace(/\s|\//g, '_')}_Lifespan_Report.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    }

    html2pdf().from(element).set(opt).save()
    toast.success('Report downloaded')
  }

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
      <header className="mb-12 animate-fade-in-down">
        <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-4">Lifespan Predictor</h1>
        <p className="text-xl text-on-surface-variant max-w-2xl">Predict remaining device life with a transparent weighted-average formula across age, usage, and environment.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <section className="lg:col-span-5 animate-fade-in-up stagger-1">
          <div className="bg-surface-container-lowest rounded-xl p-8 space-y-6 hover-lift card-shadow">
            <div className="flex items-center gap-3 mb-2">
              <span className="material-symbols-outlined text-primary">hourglass_empty</span>
              <h2 className="text-2xl font-bold text-on-surface">Device Parameters</h2>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Device Type</label>
                <select
                  value={form.deviceType}
                  onChange={(e) => setForm({ ...form, deviceType: e.target.value })}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                >
                  {DEVICE_TYPES.map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Manufacturing Year</label>
                  <input
                    type="number"
                    min={1990}
                    max={currentYear}
                    value={form.year}
                    onChange={(e) => setForm({ ...form, year: parseInt(e.target.value) || currentYear })}
                    className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Age</label>
                  <div className="w-full bg-surface-container-highest px-4 py-3 rounded-t-lg text-on-surface font-semibold">
                    {currentYear - form.year} years
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Daily Usage ({form.usage}h)</label>
                <input
                  type="range"
                  min={0} max={24} step={1}
                  value={form.usage}
                  onChange={(e) => setForm({ ...form, usage: parseInt(e.target.value) })}
                  className="w-full accent-primary"
                />
                <div className="flex justify-between text-xs text-on-surface-variant">
                  <span>0h</span><span>4h</span><span>8h</span><span>12h</span><span>24h</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Temperature</label>
                  <div className="grid grid-cols-3 gap-1 bg-surface-container rounded-lg p-1">
                    {TEMP_LEVELS.map(o => (
                      <button
                        key={o}
                        type="button"
                        onClick={() => setForm({ ...form, temperature: o })}
                        className={`py-2 rounded-md text-xs font-semibold transition ${
                          form.temperature === o ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                      >{o}</button>
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Environment</label>
                  <div className="grid grid-cols-3 gap-1 bg-surface-container rounded-lg p-1">
                    {ENV_LEVELS.map(o => (
                      <button
                        key={o}
                        type="button"
                        onClick={() => setForm({ ...form, environment: o })}
                        className={`py-2 rounded-md text-xs font-semibold transition ${
                          form.environment === o ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
                        }`}
                      >{o}</button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Power Quality</label>
                <select
                  value={form.power}
                  onChange={(e) => setForm({ ...form, power: e.target.value })}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                >
                  {POWER_LEVELS.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Maintenance</label>
                <select
                  value={form.maintenance}
                  onChange={(e) => setForm({ ...form, maintenance: e.target.value })}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                >
                  {MAINT_LEVELS.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
            </div>

            <button
              onClick={handlePredict}
              disabled={loading}
              className="w-full mt-4 bg-primary text-on-primary py-4 rounded-xl font-bold text-lg hover:opacity-90 transition-all active:scale-[0.98] shadow-lg shadow-primary/20 disabled:opacity-50 hover:-translate-y-0.5 hover:shadow-xl btn-ripple"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="material-symbols-outlined animate-spin">progress_activity</span>
                  Calculating...
                </span>
              ) : 'Predict Lifespan'}
            </button>
          </div>
        </section>

        <section className="lg:col-span-7 animate-fade-in-up stagger-2">
          {result ? (
            <div className="space-y-6">
              <div className={`bg-surface-container-lowest rounded-xl p-8 animate-scale-in-bounce hover-lift card-shadow ${eol ? 'border-2 border-error/30' : ''}`}>
                <h2 className="text-2xl font-bold text-on-surface mb-6">
                  {eol ? 'End of Life Reached' : 'Lifespan Prediction'}
                </h2>
                {eol ? (
                  <div className="text-center py-4">
                    <span className="material-symbols-outlined text-6xl text-error mb-3">warning</span>
                    <p className="text-on-surface-variant">This device has exceeded its expected lifespan of {display.base_lifespan} years.</p>
                    <p className="text-sm text-on-surface-variant mt-1">Recommend responsible recycling or replacement.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-6">
                    <div className="text-center p-6 bg-surface-container rounded-xl hover:bg-surface-container-high transition-all duration-300 transform hover:scale-105">
                      <p className={`text-4xl font-black ${healthColor}`}>{display.remaining_years}</p>
                      <p className="text-sm text-on-surface-variant mt-1">Years Remaining</p>
                    </div>
                    <div className="text-center p-6 bg-surface-container rounded-xl hover:bg-surface-container-high transition-all duration-300 transform hover:scale-105">
                      <p className="text-4xl font-black text-secondary">{(display.health_score * 100).toFixed(0)}%</p>
                      <p className="text-sm text-on-surface-variant mt-1">Health Score</p>
                    </div>
                  </div>
                )}
                {!eol && (
                  <p className="text-center text-sm text-on-surface-variant mt-4">
                    Range: {display.remaining_min} – {display.remaining_max} years · {display.model_used}
                  </p>
                )}
              </div>

              <div className="bg-surface-container-lowest rounded-xl p-8 animate-fade-in-up hover-lift card-shadow" style={{animationDelay: '0.15s'}}>
                <h3 className="text-lg font-bold text-on-surface mb-4">Environmental Impact</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-4 bg-surface-container rounded-xl hover:bg-surface-container-high transition-all duration-300 transform hover:scale-105">
                    <span className="material-symbols-outlined text-3xl text-primary mb-2">eco</span>
                    <p className="text-2xl font-black text-primary">{display.co2_avoided_kg.toFixed(1)}</p>
                    <p className="text-xs text-on-surface-variant">CO₂ Avoided (kg)</p>
                  </div>
                  <div className="text-center p-4 bg-surface-container rounded-xl hover:bg-surface-container-high transition-all duration-300 transform hover:scale-105">
                    <span className="material-symbols-outlined text-3xl text-secondary mb-2">savings</span>
                    <p className="text-2xl font-black text-secondary">₹{display.repair_savings_inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</p>
                    <p className="text-xs text-on-surface-variant">Repair Savings</p>
                  </div>
                </div>
              </div>

              <div className="bg-surface-container-lowest rounded-xl p-8 animate-fade-in-up hover-lift card-shadow" style={{animationDelay: '0.2s'}}>
                <h3 className="text-lg font-bold text-on-surface mb-4">Factor Breakdown</h3>
                <div className="space-y-3">
                  {display.factors.map(f => {
                    const pct = (f.weighted / Math.max(display.health_score, 0.001)) * 100
                    return (
                      <div key={f.name}>
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-sm font-semibold text-on-surface capitalize">{f.name} <span className="text-on-surface-variant font-normal">({f.label})</span></span>
                          <span className="text-xs font-mono text-on-surface-variant">{f.weight.toFixed(2)} × {f.raw.toFixed(2)} = <span className="font-bold text-primary">{f.weighted.toFixed(3)}</span></span>
                        </div>
                        <div className="w-full bg-surface-container rounded-full h-2 overflow-hidden">
                          <div className="bg-primary h-2 rounded-full transition-all duration-700" style={{width: `${Math.min(pct, 100)}%`}}></div>
                        </div>
                      </div>
                    )
                  })}
                </div>
                <p className="text-xs text-on-surface-variant mt-3">Health = Σ(wᵢ × fᵢ) = {display.health_score.toFixed(4)}</p>
              </div>

              <button
                onClick={handleDownloadPDF}
                className="w-full bg-secondary text-white py-3.5 rounded-xl font-bold hover:opacity-90 transition-all flex items-center justify-center gap-2 hover:-translate-y-0.5 hover:shadow-lg active:scale-[0.98] btn-ripple"
              >
                <span className="material-symbols-outlined text-lg">download</span>
                Download PDF Report
              </button>
            </div>          ) : (
            <div className="h-full flex items-center justify-center bg-surface-container-lowest rounded-xl hover-lift card-shadow animate-scale-in">
              <div className="text-center p-12">
                <span className="material-symbols-outlined text-6xl text-outline mb-4">hourglass_empty</span>
                <p className="text-on-surface-variant">Click "Predict Lifespan" to see results</p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
