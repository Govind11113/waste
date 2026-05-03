import { useState, useRef, useEffect } from 'react'

function Inventory() {
  const [formData, setFormData] = useState({
    units: 1,
    deviceType: 'laptop',
    dailyHours: 8,
    tdp: 65,
    screenSize: 15.6,
    energyRating: 'A',
    zipCode: '400001'
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const chartRef = useRef(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

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
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto">
      <header className="mb-12">
        <h1 className="text-5xl font-extrabold text-on-surface tracking-tight mb-4">Carbon Calculator</h1>
        <p className="text-xl text-on-surface-variant max-w-2xl">Calculate the carbon footprint of institutional electronics with precision grid intensity mapping.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Input Form */}
        <section className="lg:col-span-5">
          <form onSubmit={handleSubmit} className="bg-surface-container-lowest rounded-xl p-8 space-y-6">
            <div className="flex items-center gap-3 mb-6">
              <span className="material-symbols-outlined text-primary">eco</span>
              <h2 className="text-2xl font-bold text-on-surface">Device Parameters</h2>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Number of Units</label>
                <input
                  type="number"
                  min="1"
                  value={formData.units}
                  onChange={(e) => setFormData({...formData, units: parseInt(e.target.value)})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg"
                  required
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Device Type</label>
                <select
                  value={formData.deviceType}
                  onChange={(e) => setFormData({...formData, deviceType: e.target.value})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg"
                >
                  <option value="laptop">Laptop</option>
                  <option value="desktop">Desktop PC</option>
                  <option value="server">Server</option>
                  <option value="smartphone">Smartphone</option>
                  <option value="monitor">Monitor</option>
                  <option value="printer">Printer</option>
                  <option value="router">Router</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Daily Usage (Hours)</label>
                <input
                  type="number"
                  min="0"
                  max="24"
                  value={formData.dailyHours}
                  onChange={(e) => setFormData({...formData, dailyHours: parseFloat(e.target.value)})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Processor TDP (Watts)</label>
                <input
                  type="number"
                  value={formData.tdp}
                  onChange={(e) => setFormData({...formData, tdp: parseInt(e.target.value)})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Energy Rating</label>
                <select
                  value={formData.energyRating}
                  onChange={(e) => setFormData({...formData, energyRating: e.target.value})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg"
                >
                  <option value="A">A (Most Efficient)</option>
                  <option value="B">B</option>
                  <option value="C">C</option>
                  <option value="D">D (Least Efficient)</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Location Zip Code</label>
                <input
                  type="text"
                  value={formData.zipCode}
                  onChange={(e) => setFormData({...formData, zipCode: e.target.value})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg"
                  placeholder="400001"
                  maxLength="6"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-8 bg-primary text-on-primary py-4 rounded-xl font-bold text-lg hover:opacity-90 transition-all active:scale-[0.98] shadow-lg shadow-primary/20 disabled:opacity-50"
            >
              {loading ? 'Calculating...' : 'Calculate Carbon Footprint'}
            </button>
          </form>
        </section>

        {/* Results */}
        <section className="lg:col-span-7">
          {result ? (
            <div className="space-y-6">
              {/* Summary Card */}
              <div className="bg-surface-container-lowest rounded-xl p-8">
                <h2 className="text-2xl font-bold text-on-surface mb-6">Environmental Impact Summary</h2>
                <div className="grid grid-cols-2 gap-6">
                  <div className="text-center p-6 bg-surface-container rounded-xl">
                    <p className="text-4xl font-black text-primary">{result.total_tco2e}</p>
                    <p className="text-sm text-on-surface-variant mt-1">Total tCO2e</p>
                  </div>
                  <div className="text-center p-6 bg-surface-container rounded-xl">
                    <p className="text-4xl font-black text-secondary">{result.trees_planted}</p>
                    <p className="text-sm text-on-surface-variant mt-1">Trees Equivalent</p>
                  </div>
                </div>
              </div>

              {/* Breakdown */}
              <div className="bg-surface-container-lowest rounded-xl p-8">
                <h3 className="text-lg font-bold text-on-surface mb-4">Emissions Breakdown</h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-on-surface-variant">Embodied Carbon</span>
                      <span className="font-semibold">{result.embodied_kg} kg CO2</span>
                    </div>
                    <div className="w-full bg-surface-container rounded-full h-3">
                      <div className="bg-primary h-3 rounded-full" style={{width: '60%'}}></div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-on-surface-variant">Operational Carbon</span>
                      <span className="font-semibold">{result.operational_kg} kg CO2</span>
                    </div>
                    <div className="w-full bg-surface-container rounded-full h-3">
                      <div className="bg-secondary h-3 rounded-full" style={{width: '40%'}}></div>
                    </div>
                  </div>
                </div>
                <div className="mt-6 pt-6 border-t border-outline-variant">
                  <div className="flex justify-between items-center">
                    <span className="text-on-surface-variant">Grid Intensity</span>
                    <span className="font-bold text-on-surface">{result.grid_intensity} kg/MWh</span>
                  </div>
                </div>
              </div>

              <button className="w-full border-2 border-secondary text-secondary py-3 rounded-xl font-bold hover:bg-secondary/5 transition-all flex items-center justify-center gap-2">
                <span className="material-symbols-outlined text-lg">download</span>
                Download PDF Report
              </button>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center bg-surface-container-lowest rounded-xl">
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
