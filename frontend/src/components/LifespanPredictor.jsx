import { useState } from 'react'
import html2pdf from 'html2pdf.js'
import { toast } from 'react-hot-toast'

const DEVICE_TYPES = [
  'Computer', 'Laptop', 'Monitor', 'Printer', 'Projector', 'Router / Switch',
  'Smartphone', 'Motherboard', 'Hard Disk / SSD', 'Mouse', 'Keyboard', 'Air Conditioner'
]

const TEMP_LEVELS = [
  { label: 'Cool', value: 0.2 },
  { label: 'Normal', value: 0.5 },
  { label: 'Hot', value: 0.8 },
]

const ENV_LEVELS = [
  { label: 'Clean', value: 0.2 },
  { label: 'Normal', value: 0.5 },
  { label: 'Harsh', value: 0.8 },
]

function LifespanPredictor() {
  const currentYear = new Date().getFullYear()
  const [formData, setFormData] = useState({
    deviceType: 'Computer',
    year: currentYear - 2,
    usage: 8,
    tempStress: 0.5,
    environment: 0.5,
    powerQuality: 'Direct Grid',
    maintenance: 'Occasional',
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const payload = {
      device_type: formData.deviceType,
      manufacturing_year: parseInt(formData.year),
      usage_hours_per_day: parseFloat(formData.usage),
      temperature_stress: parseFloat(formData.tempStress),
      humidity_index: parseFloat(formData.environment),
      dust_index: parseFloat(formData.environment),
      power_outage_freq: formData.powerQuality,
      maintenance_frequency: formData.maintenance,
    }

    try {
      const response = await fetch('/api/v1/predict/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) throw new Error('Prediction failed')
      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError('Failed to predict lifespan. Please try again.')
      toast.error('Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadPDF = () => {
    if (!result) return
    const generatedAt = new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    const tempLabel = TEMP_LEVELS.find(t => t.value === parseFloat(formData.tempStress))?.label || 'Custom'
    const envLabel = ENV_LEVELS.find(e => e.value === parseFloat(formData.environment))?.label || 'Custom'

    const element = document.createElement('div')
    element.innerHTML = `
      <div style="padding: 40px; font-family: 'Inter', Arial, sans-serif; color: #1a1c18; max-width: 800px;">
        <div style="border-bottom: 3px solid #486730; padding-bottom: 16px; margin-bottom: 24px;">
          <h1 style="color: #486730; margin: 0 0 4px 0; font-size: 26px;">Lifespan Prediction Report</h1>
          <p style="color: #555; font-size: 13px; margin: 0;">Maharashtra Educational Sector — Device Health Assessment</p>
        </div>

        <div style="background: #f0f4f8; padding: 24px; border-radius: 12px; margin-bottom: 24px; text-align: center;">
          <h2 style="margin: 0 0 6px 0; color: #1a1c18; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Predicted Remaining Life</h2>
          <div style="font-size: 48px; font-weight: 800; color: #486730; margin-bottom: 6px;">${result.remaining_years} Years</div>
          <div style="font-size: 13px; color: #555;">Health: <strong>${result.health_percentage}%</strong> · Age: ${result.age} yrs · Base lifespan: ${result.base_lifespan} yrs</div>
          <div style="margin-top: 14px; background: #e2e8f0; height: 10px; border-radius: 5px; overflow: hidden;">
            <div style="background: #486730; width: ${result.health_percentage}%; height: 100%;"></div>
          </div>
        </div>

        <h3 style="color: #486730; margin-bottom: 12px;">Inputs</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc; width: 40%;">Device Type</td><td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>${formData.deviceType}</strong></td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Manufacturing Year</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${formData.year}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Daily Usage</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${formData.usage} hours</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Temperature</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${tempLabel}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Environment</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${envLabel}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Power Quality</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${formData.powerQuality}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Maintenance</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${formData.maintenance}</td></tr>
        </table>

        <h3 style="color: #486730; margin-bottom: 12px;">Factor Breakdown — L = (1/N) · Σ fᵢ</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
          ${Object.entries(result.factor_breakdown || {}).map(([k, v]) => `
            <tr>
              <td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc; width: 40%; text-transform: capitalize;">${k}</td>
              <td style="padding: 10px; border: 1px solid #e2e8f0;">
                <div style="display: flex; align-items: center; gap: 12px;">
                  <div style="flex: 1; background: #e2e8f0; height: 8px; border-radius: 4px; overflow: hidden;">
                    <div style="background: #00629e; width: ${v * 100}%; height: 100%;"></div>
                  </div>
                  <strong>${(v * 100).toFixed(0)}%</strong>
                </div>
              </td>
            </tr>
          `).join('')}
        </table>

        <h3 style="color: #486730; margin-bottom: 12px;">Environmental Impact</h3>
        <p style="margin: 0 0 16px 0; line-height: 1.6;">By extending this device's life by <strong>${result.remaining_years} years</strong>, the institution avoids <strong>${result.co2_avoided} kg</strong> of embodied CO₂ emissions.</p>

        <h3 style="color: #486730; margin-bottom: 12px;">Repair vs Replace</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Estimated Replacement Cost</td><td style="padding: 10px; border: 1px solid #e2e8f0;">₹${result.replace_cost.toLocaleString()}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Average Repair Cost</td><td style="padding: 10px; border: 1px solid #e2e8f0;">₹${result.repair_cost.toLocaleString()}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc; font-weight: 600;">Potential Savings (Repair)</td><td style="padding: 10px; border: 1px solid #e2e8f0; color: #486730; font-weight: 700;">₹${(result.replace_cost - result.repair_cost).toLocaleString()}</td></tr>
        </table>

        <div style="display: flex; justify-content: space-between; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #999;">
          <span>Generated: ${generatedAt}</span>
          <span>${result.model_used}</span>
        </div>
      </div>
    `

    const opt = {
      margin: 0.4,
      filename: `${formData.deviceType.replace(/\s|\//g, '_')}_Lifespan_Report.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' },
    }

    html2pdf().from(element).set(opt).save()
    toast.success('Report downloaded')
  }

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
      <header className="mb-12 animate-fade-in-down">
        <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-4">Lifespan Predictor</h1>
        <p className="text-xl text-on-surface-variant max-w-2xl">
          Predict remaining device life using a transparent weighted-average formula
          <span className="font-mono text-base"> L = (1/N) · Σ fᵢ(M, T, E, U, P, S)</span>
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <section className="lg:col-span-5 animate-fade-in-up stagger-1">
          <form onSubmit={handleSubmit} className="bg-surface-container-lowest rounded-xl p-8 space-y-5 hover-lift card-shadow">
            <div className="flex items-center gap-3 mb-2">
              <span className="material-symbols-outlined text-primary">hourglass_empty</span>
              <h2 className="text-2xl font-bold text-on-surface">Device Inputs</h2>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Device Type</label>
              <select
                value={formData.deviceType}
                onChange={(e) => setFormData({ ...formData, deviceType: e.target.value })}
                className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
              >
                {DEVICE_TYPES.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Manufacturing Year</label>
              <input
                type="number"
                min="1990"
                max={currentYear}
                value={formData.year}
                onChange={(e) => setFormData({ ...formData, year: e.target.value })}
                className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                required
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Daily Usage</label>
                <span className="text-xs font-bold text-primary">{formData.usage} hrs</span>
              </div>
              <input
                type="range"
                min="0"
                max="24"
                step="1"
                value={formData.usage}
                onChange={(e) => setFormData({ ...formData, usage: parseInt(e.target.value) })}
                className="w-full range-slider"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Temperature</label>
              <div className="grid grid-cols-3 gap-2">
                {TEMP_LEVELS.map(t => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => setFormData({ ...formData, tempStress: t.value })}
                    className={`py-2.5 rounded-lg font-semibold text-sm transition-all ${
                      parseFloat(formData.tempStress) === t.value
                        ? 'bg-primary text-on-primary shadow-md'
                        : 'bg-surface-container-highest text-on-surface hover:bg-surface-container-high'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Environment (Dust + Humidity)</label>
              <div className="grid grid-cols-3 gap-2">
                {ENV_LEVELS.map(env => (
                  <button
                    key={env.value}
                    type="button"
                    onClick={() => setFormData({ ...formData, environment: env.value })}
                    className={`py-2.5 rounded-lg font-semibold text-sm transition-all ${
                      parseFloat(formData.environment) === env.value
                        ? 'bg-primary text-on-primary shadow-md'
                        : 'bg-surface-container-highest text-on-surface hover:bg-surface-container-high'
                    }`}
                  >
                    {env.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Power Quality</label>
              <select
                value={formData.powerQuality}
                onChange={(e) => setFormData({ ...formData, powerQuality: e.target.value })}
                className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
              >
                <option value="UPS Protected">UPS Protected</option>
                <option value="Direct Grid">Direct Grid</option>
                <option value="Frequent Outages">Frequent Outages</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Maintenance</label>
              <select
                value={formData.maintenance}
                onChange={(e) => setFormData({ ...formData, maintenance: e.target.value })}
                className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
              >
                <option value="Regular">Regular</option>
                <option value="Occasional">Occasional</option>
                <option value="None">None</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-primary text-on-primary py-4 rounded-xl font-bold text-lg hover:opacity-90 transition-all active:scale-[0.98] shadow-lg shadow-primary/20 disabled:opacity-50 hover:-translate-y-0.5 hover:shadow-xl btn-ripple"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="material-symbols-outlined animate-spin">progress_activity</span>
                  Predicting...
                </span>
              ) : 'Predict Lifespan'}
            </button>
          </form>
        </section>

        <section className="lg:col-span-7 animate-fade-in-up stagger-2">
          {error && (
            <div className="mb-6 p-4 bg-error-container rounded-xl flex items-center gap-3 animate-scale-in">
              <span className="material-symbols-outlined text-on-error-container">error</span>
              <span className="text-sm font-medium text-on-error-container">{error}</span>
            </div>
          )}

          {loading ? (
            <div className="bg-surface-container-lowest rounded-xl p-12 animate-fade-in">
              <div className="flex flex-col items-center justify-center gap-4">
                <span className="material-symbols-outlined text-5xl text-primary animate-spin">hourglass_empty</span>
                <p className="text-lg font-semibold text-on-surface">Computing weighted health score...</p>
              </div>
            </div>
          ) : result ? (
            <div className="space-y-6">
              <div className="bg-surface-container-lowest rounded-xl p-8 animate-scale-in-bounce hover-lift card-shadow text-center">
                <p className="text-xs font-bold uppercase tracking-widest text-primary mb-2">Predicted Remaining Life</p>
                <p className="text-6xl font-black text-primary mb-2">{result.remaining_years}</p>
                <p className="text-sm text-on-surface-variant">years remaining</p>
                <div className="mt-6 max-w-sm mx-auto">
                  <div className="flex justify-between text-xs text-on-surface-variant mb-1">
                    <span>Health</span>
                    <span className="font-bold text-on-surface">{result.health_percentage}%</span>
                  </div>
                  <div className="bg-surface-container rounded-full h-3 overflow-hidden">
                    <div className="bg-primary h-3 rounded-full transition-all duration-1000" style={{ width: `${result.health_percentage}%` }}></div>
                  </div>
                </div>
                <p className="text-xs text-outline mt-4">Age: {result.age} yrs · Base lifespan: {result.base_lifespan} yrs · {result.model_used}</p>
              </div>

              <div className="bg-surface-container-lowest rounded-xl p-6 animate-fade-in-up hover-lift card-shadow" style={{ animationDelay: '0.15s' }}>
                <h3 className="text-lg font-bold text-on-surface mb-4">Factor Breakdown</h3>
                <div className="space-y-3">
                  {Object.entries(result.factor_breakdown || {}).map(([k, v]) => (
                    <div key={k}>
                      <div className="flex justify-between mb-1.5">
                        <span className="text-on-surface-variant capitalize text-sm">{k}</span>
                        <span className="font-bold text-on-surface text-sm">{(v * 100).toFixed(0)}%</span>
                      </div>
                      <div className="bg-surface-container rounded-full h-2 overflow-hidden">
                        <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${v * 100}%`, backgroundColor: v > 0.7 ? 'var(--primary)' : v > 0.4 ? '#00629e' : '#ba1a1a' }}></div>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-outline mt-4 font-mono">L = ({Object.values(result.factor_breakdown || {}).map(v => v.toFixed(2)).join(' + ')}) / 6 = {(result.health_percentage / 100).toFixed(3)}</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-primary/5 border border-primary/20 rounded-xl p-6">
                  <p className="text-xs font-bold uppercase tracking-widest text-primary mb-2">CO₂ Avoided</p>
                  <p className="text-3xl font-black text-primary">{result.co2_avoided} <span className="text-base font-bold text-on-surface-variant">kg</span></p>
                </div>
                <div className="bg-secondary/5 border border-secondary/20 rounded-xl p-6">
                  <p className="text-xs font-bold uppercase tracking-widest text-secondary mb-2">Repair Savings</p>
                  <p className="text-3xl font-black text-secondary">₹{(result.replace_cost - result.repair_cost).toLocaleString()}</p>
                </div>
              </div>

              <button
                onClick={handleDownloadPDF}
                className="w-full bg-secondary text-white py-3.5 rounded-xl font-bold hover:opacity-90 transition-all flex items-center justify-center gap-2 hover:-translate-y-0.5 hover:shadow-lg active:scale-[0.98] btn-ripple"
              >
                <span className="material-symbols-outlined text-lg">download</span>
                Download PDF Report
              </button>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center bg-surface-container-lowest rounded-xl hover-lift card-shadow animate-scale-in">
              <div className="text-center p-12">
                <span className="material-symbols-outlined text-6xl text-outline mb-4">hourglass_empty</span>
                <p className="text-on-surface-variant">Fill in device parameters to predict its remaining lifespan</p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default LifespanPredictor
