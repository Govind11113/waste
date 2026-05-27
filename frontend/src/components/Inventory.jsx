import { useState } from 'react'
import { toast } from 'react-hot-toast'
import html2pdf from 'html2pdf.js'

const DEVICE_OPTIONS = [
  { value: 'Computer', label: 'Computer / Desktop', tdp: 200 },
  { value: 'Laptop', label: 'Laptop', tdp: 65 },
  { value: 'Monitor', label: 'Monitor', tdp: 35 },
  { value: 'Printer', label: 'Printer', tdp: 50 },
  { value: 'Projector', label: 'Projector', tdp: 250 },
  { value: 'Router / Switch', label: 'Router / Switch', tdp: 15 },
  { value: 'Smartphone', label: 'Smartphone', tdp: 5 },
  { value: 'Motherboard', label: 'Motherboard (component)', tdp: 50 },
  { value: 'Hard Disk / SSD', label: 'Hard Disk / SSD', tdp: 8 },
  { value: 'Mouse', label: 'Mouse', tdp: 2 },
  { value: 'Keyboard', label: 'Keyboard', tdp: 2 },
  { value: 'Air Conditioner', label: 'Air Conditioner (1.5 ton)', tdp: 1500 },
  { value: 'Television', label: 'Television', tdp: 100 },
  { value: 'Microwave', label: 'Microwave', tdp: 1100 },
]

function Inventory() {
  const [formData, setFormData] = useState({
    units: 1,
    device_type: 'Computer',
    daily_hours: 8,
    tdp: 200,
    energy_rating: 'A',
    zip_code: '400001',
    lifespan_years: 5,
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleDeviceChange = (e) => {
    const value = e.target.value
    const opt = DEVICE_OPTIONS.find(d => d.value === value)
    setFormData({ ...formData, device_type: value, tdp: opt?.tdp ?? formData.tdp })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/v1/carbon/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      if (!response.ok) throw new Error('Carbon calculation failed')
      const data = await response.json()
      setResult(data)
    } catch (err) {
      const message = 'Failed to calculate carbon footprint. Please try again.'
      setError(message)
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadPDF = () => {
    if (!result) return
    const generatedAt = new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    const totalKg = (result.embodied_kg + result.operational_kg).toFixed(1)
    const embodiedPct = ((result.embodied_kg / (result.embodied_kg + result.operational_kg)) * 100).toFixed(1)
    const operationalPct = (100 - parseFloat(embodiedPct)).toFixed(1)

    const element = document.createElement('div')
    element.innerHTML = `
      <div style="padding: 40px; font-family: 'Inter', Arial, sans-serif; color: #1a1c18; max-width: 800px;">
        <div style="border-bottom: 3px solid #486730; padding-bottom: 16px; margin-bottom: 24px;">
          <h1 style="color: #486730; margin: 0 0 4px 0; font-size: 26px;">Carbon Footprint Report</h1>
          <p style="color: #555; font-size: 13px; margin: 0;">Maharashtra Educational Sector — Device Carbon Analysis</p>
        </div>

        <div style="background: #f0f4f8; padding: 24px; border-radius: 12px; margin-bottom: 24px; text-align: center;">
          <h2 style="margin: 0 0 6px 0; color: #1a1c18; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Total Lifecycle Emissions</h2>
          <div style="font-size: 42px; font-weight: 800; color: #486730;">${result.total_tco2e} tCO₂e</div>
          <div style="font-size: 13px; color: #555;">Equivalent to planting <strong>${result.trees_planted}</strong> trees to offset</div>
        </div>

        <h3 style="color: #486730; margin-bottom: 12px;">Inputs</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc; width: 40%;">Device Type</td><td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>${formData.device_type}</strong></td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Units</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${formData.units}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Daily Usage</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${formData.daily_hours} hours</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Power Draw (TDP)</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${formData.tdp} W</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Energy Rating</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${formData.energy_rating}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Lifespan</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${result.lifespan_years} years</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Postal Code</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${formData.zip_code}</td></tr>
          <tr><td style="padding: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">Grid Intensity</td><td style="padding: 10px; border: 1px solid #e2e8f0;">${result.grid_intensity} kg CO₂/kWh</td></tr>
        </table>

        <h3 style="color: #486730; margin-bottom: 12px;">Emissions Breakdown</h3>
        <div style="margin-bottom: 24px;">
          <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span>Embodied (manufacturing)</span><strong>${result.embodied_kg} kg (${embodiedPct}%)</strong></div>
            <div style="background: #e2e8f0; height: 12px; border-radius: 6px; overflow: hidden;"><div style="background: #486730; width: ${embodiedPct}%; height: 100%;"></div></div>
          </div>
          <div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span>Operational (use phase)</span><strong>${result.operational_kg} kg (${operationalPct}%)</strong></div>
            <div style="background: #e2e8f0; height: 12px; border-radius: 6px; overflow: hidden;"><div style="background: #00629e; width: ${operationalPct}%; height: 100%;"></div></div>
          </div>
          <p style="margin-top: 12px; font-size: 13px; color: #555;">Total: <strong>${totalKg} kg CO₂e</strong> over the device's ${result.lifespan_years}-year lifespan.</p>
        </div>

        <div style="display: flex; justify-content: space-between; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #999;">
          <span>Generated: ${generatedAt}</span>
          <span>E-Waste Management v3</span>
        </div>
      </div>
    `

    const opt = {
      margin: 0.4,
      filename: `${formData.device_type.replace(/\s|\//g, '_')}_Carbon_Report.pdf`,
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
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Device Type</label>
                <select
                  value={formData.device_type}
                  onChange={handleDeviceChange}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                >
                  {DEVICE_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Units</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.units}
                    onChange={(e) => setFormData({...formData, units: parseInt(e.target.value) || 1})}
                    className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Lifespan (yrs)</label>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={formData.lifespan_years}
                    onChange={(e) => setFormData({...formData, lifespan_years: parseFloat(e.target.value) || 5})}
                    className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Daily Hours</label>
                  <input
                    type="number"
                    min="0"
                    max="24"
                    step="0.5"
                    value={formData.daily_hours}
                    onChange={(e) => setFormData({...formData, daily_hours: parseFloat(e.target.value) || 0})}
                    className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Power (W / TDP)</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.tdp}
                    onChange={(e) => setFormData({...formData, tdp: parseInt(e.target.value) || 0})}
                    className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Energy Rating</label>
                <select
                  value={formData.energy_rating}
                  onChange={(e) => setFormData({...formData, energy_rating: e.target.value})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                >
                  <option value="A">A (Most Efficient)</option>
                  <option value="B">B</option>
                  <option value="C">C</option>
                  <option value="D">D (Least Efficient)</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Postal Code</label>
                <input
                  type="text"
                  value={formData.zip_code}
                  onChange={(e) => setFormData({...formData, zip_code: e.target.value})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg form-field"
                  placeholder="400001"
                  maxLength="6"
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
            <div className="mb-6 p-4 bg-error-container rounded-xl flex items-center gap-3 animate-scale-in">
              <span className="material-symbols-outlined text-on-error-container">error</span>
              <span className="text-sm font-medium text-on-error-container">{error}</span>
              <button
                onClick={handleSubmit}
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
            <div className="space-y-6">
              <div className="bg-surface-container-lowest rounded-xl p-8 animate-scale-in-bounce hover-lift card-shadow">
                <h2 className="text-2xl font-bold text-on-surface mb-6">Environmental Impact Summary</h2>
                <div className="grid grid-cols-2 gap-6">
                  <div className="text-center p-6 bg-surface-container rounded-xl hover:bg-surface-container-high transition-all duration-300 transform hover:scale-105">
                    <p className="text-4xl font-black text-primary">{result.total_tco2e}</p>
                    <p className="text-sm text-on-surface-variant mt-1">Total tCO₂e</p>
                  </div>
                  <div className="text-center p-6 bg-surface-container rounded-xl hover:bg-surface-container-high transition-all duration-300 transform hover:scale-105">
                    <p className="text-4xl font-black text-secondary">{result.trees_planted}</p>
                    <p className="text-sm text-on-surface-variant mt-1">Trees to Offset</p>
                  </div>
                </div>
                <p className="text-center text-sm text-on-surface-variant mt-4">Over {result.lifespan_years}-year lifespan</p>
              </div>

              <div className="bg-surface-container-lowest rounded-xl p-8 animate-fade-in-up hover-lift card-shadow" style={{animationDelay: '0.15s'}}>
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
                <span className="material-symbols-outlined text-6xl text-outline mb-4">calculate</span>
                <p className="text-on-surface-variant">Enter device parameters to calculate carbon footprint</p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default Inventory
