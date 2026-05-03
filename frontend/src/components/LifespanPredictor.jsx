import { useState, useEffect, useRef } from 'react'
import html2pdf from 'html2pdf.js'

const brandsData = {
  "Motherboard": {
    "Asus": ["ROG Strix Z790-E", "TUF Gaming B650", "Prime H610M-A", "ProArt X670E"],
    "Gigabyte": ["AORUS Elite AX", "UD AX", "Aero G", "Gaming X"],
    "MSI": ["MAG Tomahawk", "PRO B660M", "MPG Carbon", "MEG ACE"],
    "Intel / Generic": ["OEM H81", "OEM H110"]
  },
  "Hard Disk / SSD": {
    "Western Digital (WD)": ["Blue SN570 NVMe", "Black SN850X", "Red Plus NAS HDD", "Purple SATA"],
    "Seagate": ["BarraCuda", "FireCuda 530", "IronWolf", "SkyHawk"],
    "Samsung": ["980 PRO", "990 PRO", "870 EVO", "870 QVO SATA"],
    "Crucial": ["MX500", "P3 Plus", "P5", "X8 Portable"]
  },
  "Monitor": {
    "Dell": ["UltraSharp U2723QE", "P2419H Professional", "Alienware AW3423DW", "E2222H Essential"],
    "LG": ["UltraGear 27GP850", "UltraFine 4K", "24MP60G", "34WN80C UltraWide"],
    "BenQ": ["GW2480", "PD2700U DesignVue", "Mobiuz EX2710S", "Zowie XL2411K"],
    "Samsung": ["Odyssey G7", "Smart Monitor M8", "UR55 4K", "F390 Series"]
  },
  "Mouse": {
    "Logitech": ["MX Master 3S", "G Pro X Superlight", "G502 Hero", "M330 Silent Plus"],
    "Razer": ["DeathAdder V2", "Viper Ultimate", "Basilisk V3"],
    "HP": ["X3000", "Z3700 Wireless", "Omen Vector"],
    "Dell": ["MS116", "Mobile Pro MS5120W", "Alienware AW610M"]
  },
  "Keyboard": {
    "Logitech": ["MX Keys", "K120", "K380", "G915 TKL"],
    "Dell": ["KB216", "KM7120W Multi-Device", "Alienware AW410K"],
    "TVS": ["Gold Pro Mechanical", "Champ USB"],
    "HP": ["K1500", "Pavilion Gaming 500", "Wireless K2500"]
  },
  "Smartphone": {
    "Apple": ["iPhone 13", "iPhone 14", "iPhone 15 Pro", "iPhone SE (3rd Gen)"],
    "Samsung": ["Galaxy S23 Ultra", "Galaxy A54", "Galaxy M34", "Galaxy Z Fold 5"],
    "OnePlus": ["Nord CE 3", "11R 5G", "Open"],
    "Xiaomi / Redmi": ["Redmi Note 12", "Xiaomi 13 Pro", "Poco X5"]
  },
  "Computer": {
    "Dell": ["OptiPlex 7000 Micro", "OptiPlex 3090 Tower", "Inspiron 24 All-in-One", "Precision 3660"],
    "HP": ["ProDesk 400 G7", "EliteDesk 800", "Pavilion TP01", "Z2 Tower G9"],
    "Lenovo": ["ThinkCentre M70q", "ThinkCentre neo 50s", "IdeaCentre 3"],
    "Assembled": ["Custom Intel Core i5", "Custom AMD Ryzen 5", "Custom i3 Lab Build"]
  },
  "Printer": {
    "HP": ["LaserJet Pro M15w", "Neverstop Laser 1000w", "DeskJet 2331", "OfficeJet Pro 9015"],
    "Epson": ["EcoTank L3250", "EcoTank L3110", "WorkForce Pro WF-4820", "L1800"],
    "Canon": ["PIXMA G3000", "imageCLASS MF244dw", "PIXMA TS3370", "LBP2900B"],
    "Brother": ["DCP-T420W", "HL-L2321D Laser", "MFC-L2701DW"]
  },
  "Projector": {
    "Epson": ["EB-E01 XGA", "CO-W01 WXGA", "Home Cinema 2250", "PowerLite 1781W"],
    "BenQ": ["MS560 SVGA", "MW560 WXGA", "TK850 4K", "TH585"],
    "Sony": ["VPL-VW295ES", "VPL-PHZ10 Laser"],
    "ViewSonic": ["PA503S", "PX701-4K", "M1 Mini Plus"]
  },
  "Router / Switch": {
    "Cisco": ["Catalyst 9200", "RV340 VPN", "Meraki MR44", "Catalyst 2960-X"],
    "TP-Link": ["Archer AX73", "Archer C6", "TL-SG108 Switch", "Deco M4"],
    "D-Link": ["DIR-822", "DES-1008A Switch", "DIR-615", "DGS-1024D"],
    "Netgear": ["Nighthawk AX8", "R6220", "GS308 Switch"]
  }
}

function LifespanPredictor() {
  const [formData, setFormData] = useState({
    institution: '',
    deviceType: 'Computer',
    brand: 'Dell',
    deviceModel: 'OptiPlex 7000 Micro',
    region: 'Pune/Nashik',
    year: 2020,
    humidity: 45,
    dust: 0.5,
    tempStress: 0.5,
    usage: 8,
    powerQuality: 'Medium',
    maintenance: 'Annual',
    diagnostics: []
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingWeather, setLoadingWeather] = useState(false)
  const [error, setError] = useState(null)
  const reportRef = useRef(null)

  const handleDownloadPDF = () => {
    if (!result) return;
    
    const element = document.createElement('div');
    element.innerHTML = `
      <div style="padding: 40px; font-family: sans-serif; color: #1a1c18;">
        <h1 style="color: #00629e; margin-bottom: 5px;">E-Waste Management System</h1>
        <p style="color: #444; font-size: 14px; margin-bottom: 30px;">Maharashtra Educational Sector - Sustainability Report</p>
        
        <hr style="border: 0; border-top: 1px solid #eee; margin-bottom: 30px;">
        
        <div style="display: grid; grid-template-cols: 1fr 1fr; gap: 20px; margin-bottom: 40px;">
          <div>
            <h3 style="color: #555; font-size: 12px; text-transform: uppercase;">Institution Details</h3>
            <p><strong>Name:</strong> ${formData.institution || 'N/A'}</p>
            <p><strong>Region:</strong> ${formData.region}</p>
          </div>
          <div>
            <h3 style="color: #555; font-size: 12px; text-transform: uppercase;">Device Details</h3>
            <p><strong>Type:</strong> ${formData.deviceType}</p>
            <p><strong>Brand:</strong> ${formData.brand}</p>
            <p><strong>Age:</strong> ${result.age} Years</p>
          </div>
        </div>

        <div style="background: #f0f4f8; padding: 30px; border-radius: 12px; margin-bottom: 30px; text-align: center;">
          <h2 style="margin-top: 0;">Lifespan Prediction</h2>
          <div style="font-size: 48px; font-weight: 900; color: #00629e;">${result.remaining_years} Years</div>
          <p style="color: #666;">Remaining Useful Life Result</p>
          <div style="margin-top: 15px; background: #e2e8f0; height: 10px; border-radius: 5px; overflow: hidden;">
            <div style="background: #00629e; width: ${result.health_percentage}%; height: 100%;"></div>
          </div>
          <p style="font-size: 14px; margin-top: 10px;">Device Health: ${result.health_percentage}%</p>
        </div>

        <div style="margin-bottom: 30px;">
          <h3 style="color: #00629e;">Environmental Impact</h3>
          <p>By extending this device's life by ${result.remaining_years} years, the institution avoids <strong>${result.co2_avoided} kg</strong> of embodied CO2 emissions.</p>
        </div>

        <div style="padding: 20px; border: 1px solid #00629e; border-radius: 12px;">
          <h3 style="color: #00629e; margin-top: 0;">Financial Analysis (Repair vs. Replace)</h3>
          <p>Estimated Cost for New Device: <strong>₹${result.replace_cost?.toLocaleString()}</strong></p>
          <p>Average Cost of Repair: <strong>₹${result.repair_cost?.toLocaleString()}</strong></p>
          <p style="font-size: 18px; color: #1a1c18; margin-top: 15px;">
            Potential Savings: <span style="color: #00629e; font-weight: bold;">₹${((result.replace_cost || 0) - (result.repair_cost || 0)).toLocaleString()}</span>
          </p>
        </div>

        <div style="margin-top: 50px; font-size: 10px; color: #999; text-align: center;">
          Report generated on ${new Date().toLocaleDateString()} | XGBoost High-Precision Prognosis
        </div>
      </div>
    `;

    const opt = {
      margin: 0.5,
      filename: `${formData.institution || 'E-Waste'}_Report.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2 },
      jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    };

    html2pdf().from(element).set(opt).save();
  };

  const handleDeviceChange = (e) => {
    const newType = e.target.value;
    const availableBrands = Object.keys(brandsData[newType] || {});
    const firstBrand = availableBrands[0] || 'Generic';
    
    setFormData({
      ...formData, 
      deviceType: newType,
      brand: firstBrand,
      diagnostics: []
    })
  }

  const handleBrandChange = (e) => {
    const newBrand = e.target.value;
    setFormData({
      ...formData,
      brand: newBrand
    })
  }

  useEffect(() => {
    const fetchWeather = async () => {
      setLoadingWeather(true)
      let lat = 18.5204, lon = 73.8567 // Default Pune
      if (formData.region === 'Konkan/Mumbai') {
        lat = 19.0760; lon = 72.8777 // Mumbai
      } else if (formData.region === 'Vidarbha/Marathwada') {
        lat = 21.1458; lon = 79.0882 // Nagpur
      }

      try {
        const weatherRes = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m`)
        const weatherData = await weatherRes.json()
        const humidity = weatherData.current?.relative_humidity_2m || 50
        const temp = weatherData.current?.temperature_2m || 30
        
        const aqiRes = await fetch(`https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=pm10`)
        const aqiData = await aqiRes.json()
        const pm10 = aqiData.current?.pm10 || 20

        let tStress = 0.5
        if (temp > 35) tStress = 0.9; else if (temp > 30) tStress = 0.7; else if (temp < 25) tStress = 0.2

        let dIndex = 0.5
        if (pm10 > 100) dIndex = 0.9; else if (pm10 > 50) dIndex = 0.7; else if (pm10 < 20) dIndex = 0.2

        setFormData(prev => ({
          ...prev,
          humidity: Math.round(humidity),
          tempStress: tStress,
          dust: dIndex
        }))
      } catch (err) {
        console.error("Failed to fetch live weather", err)
      } finally {
        setLoadingWeather(false)
      }
    }
    fetchWeather()
  }, [formData.region])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/v1/predict/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          device_type: formData.deviceType,
          region: formData.region,
          manufacturing_year: formData.year,
          usage_hours_per_day: formData.usage,
          dust_index: formData.dust,
          humidity_index: formData.humidity / 100,
          temperature_stress: formData.tempStress,
          power_outage_freq: formData.powerQuality,
          maintenance_frequency: formData.maintenance
        })
      })

      if (!response.ok) {
        throw new Error('Prediction failed')
      }

      const data = await response.json()
      
      // Apply Deep Diagnostic Penalties
      let penaltyMultiplier = 1.0;
      const numIssues = formData.diagnostics.length;
      if (numIssues === 1) penaltyMultiplier = 0.8; // 20% drop
      if (numIssues === 2) penaltyMultiplier = 0.6; // 40% drop
      if (numIssues >= 3) penaltyMultiplier = 0.3;  // 70% drop

      const penalizedRUL = Math.max(0.1, data.remaining_years * penaltyMultiplier);
      const penalizedHealth = Math.max(5.0, data.health_percentage * penaltyMultiplier);
      
      setResult({
        ...data,
        remaining_years: Number(penalizedRUL.toFixed(1)),
        health_percentage: Number(penalizedHealth.toFixed(1))
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto">
      <header className="mb-16">
        <h1 className="text-5xl font-extrabold text-on-surface-variant tracking-tight mb-4">
          Device Lifespan Predictor
        </h1>
        <p className="text-on-surface-variant/80 text-xl max-w-2xl font-medium">
          Calculate the remaining useful life of educational institutional devices using XGBoost & Random Forest Ensembles trained on Maharashtra environmental data.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <section className="lg:col-span-7 bg-surface-container-lowest rounded-xl p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="flex items-center gap-3 mb-8">
            <span className="material-symbols-outlined text-primary">analytics</span>
            <h2 className="text-2xl font-bold text-on-surface">Device Inventory Data</h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Institution Name</label>
                <input
                  type="text"
                  value={formData.institution}
                  onChange={(e) => setFormData({...formData, institution: e.target.value})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg transition-all"
                  placeholder="e.g., Valia College"
                  required
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Device Type</label>
                <select
                  value={formData.deviceType}
                  onChange={handleDeviceChange}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg transition-all"
                >
                  <option>Motherboard</option>
                  <option>Hard Disk / SSD</option>
                  <option>Monitor</option>
                  <option>Mouse</option>
                  <option>Keyboard</option>
                  <option>Smartphone</option>
                  <option>Computer</option>
                  <option>Printer</option>
                  <option>Projector</option>
                  <option>Router / Switch</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Brand</label>
                <select
                  value={formData.brand}
                  onChange={handleBrandChange}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg transition-all"
                >
                  {Object.keys(brandsData[formData.deviceType] || {}).map(b => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Maharashtra Region</label>
                <select
                  value={formData.region}
                  onChange={(e) => setFormData({...formData, region: e.target.value})}
                  className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg transition-all"
                >
                  <option>Pune/Nashik</option>
                  <option>Konkan/Mumbai</option>
                  <option>Vidarbha/Marathwada</option>
                </select>
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-outline-variant/30">
              <label className="text-sm font-bold uppercase tracking-widest text-on-surface-variant mb-4 block">Deep Diagnostic Assessment</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {['Physical Damage / Cracked Component', 'Frequent Overheating', 'Unusual Noise / Fan Failure', 'Power Surges / Frequent Reboots', 'Software / OS Severe Lag', 'Water / Liquid Exposure'].map(symptom => (
                  <label key={symptom} className="flex items-center gap-3 p-3 bg-surface-container-low rounded-lg border border-outline-variant/30 cursor-pointer hover:bg-surface-container-highest transition-colors">
                    <input 
                      type="checkbox" 
                      className="w-5 h-5 rounded border-outline-variant text-primary focus:ring-primary accent-primary"
                      checked={formData.diagnostics.includes(symptom)}
                      onChange={(e) => {
                        const newDiag = e.target.checked 
                          ? [...formData.diagnostics, symptom]
                          : formData.diagnostics.filter(d => d !== symptom);
                        setFormData({...formData, diagnostics: newDiag});
                      }}
                    />
                    <span className="text-sm text-on-surface font-medium">{symptom}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Manufacturing Year</label>
              <input
                type="number"
                value={formData.year}
                onChange={(e) => setFormData({...formData, year: parseInt(e.target.value)})}
                className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg transition-all"
                placeholder="2020"
                min="2000"
                max={new Date().getFullYear()}
                required
              />
            </div>

            <div className="space-y-4 pt-4">
              <div className="flex justify-between items-center">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Environment Humidity (%)</label>
                <span className="text-secondary font-bold">{formData.humidity}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={formData.humidity}
                onChange={(e) => setFormData({...formData, humidity: parseInt(e.target.value)})}
                className="w-full h-1 range-slider accent-secondary appearance-none"
              />
            </div>

            <div className="space-y-4 pt-4">
              <div className="flex justify-between items-center">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Daily Usage Intensity (Hours)</label>
                <span className="text-secondary font-bold">{formData.usage} hrs</span>
              </div>
              <input
                type="range"
                min="0"
                max="24"
                value={formData.usage}
                onChange={(e) => setFormData({...formData, usage: parseInt(e.target.value)})}
                className="w-full h-1 range-slider accent-secondary appearance-none"
              />
            </div>

            <div className="space-y-2 pt-4">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Power Supply Quality</label>
              <select
                value={formData.powerQuality}
                onChange={(e) => setFormData({...formData, powerQuality: e.target.value})}
                className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg transition-all"
              >
                <option>UPS Protected</option>
                <option>Direct Grid</option>
                <option>Frequent Outages</option>
              </select>
            </div>

            <div className="space-y-2 pt-4">
              <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant">Maintenance Schedule</label>
              <select
                value={formData.maintenance}
                onChange={(e) => setFormData({...formData, maintenance: e.target.value})}
                className="w-full bg-surface-container-highest border-0 border-b-2 border-transparent focus:border-primary focus:ring-0 px-4 py-3 rounded-t-lg transition-all"
              >
                <option>Regular</option>
                <option>Occasional</option>
                <option>None</option>
              </select>
            </div>

            {error && (
              <div className="p-4 bg-error-container text-error rounded-lg">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-8 bg-primary text-on-primary py-4 rounded-xl font-bold text-lg hover:opacity-90 transition-all active:scale-[0.98] shadow-lg shadow-primary/20 disabled:opacity-50"
            >
              {loading ? 'Calculating...' : 'Calculate Predicted Lifespan'}
            </button>
          </form>
        </section>

        <section className="lg:col-span-5 space-y-8">
          {result ? (
            <>
              <div className="bg-surface-container-lowest rounded-xl p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-secondary-container/10 rounded-bl-full -mr-8 -mt-8"></div>
                <h2 className="text-2xl font-bold text-on-surface mb-8">Prediction Analysis</h2>

                <div className="mb-10 text-center">
                  <p className="text-on-surface-variant/70 font-semibold text-sm uppercase tracking-widest mb-2">Predicted Remaining Life</p>
                  <div className="text-6xl font-black text-secondary tracking-tighter">
                    {result.remaining_years} <span className="text-2xl font-bold">Years</span>
                  </div>
                  <p className="text-xs font-medium text-outline mt-2">Calculated via {result.model_used}</p>
                </div>

                <div className="flex justify-center mb-8">
                  <div className="relative w-32 h-32">
                    <svg className="w-full h-full" viewBox="0 0 100 100">
                      <circle cx="50" cy="50" r="40" fill="none" stroke="#c4c8ba" strokeWidth="8"/>
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="none"
                        stroke="#00629e"
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeDasharray={`${result.health_percentage * 2.51} 251`}
                        transform="rotate(-90 50 50)"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-lg font-bold text-on-surface">{result.health_percentage}%</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <p className="text-center text-xs font-bold text-on-surface-variant/60 uppercase tracking-widest">Device Health Degradation Over Time</p>
                  <div className="flex justify-between items-end h-40 gap-2 mb-2 px-4">
                    {[100, 75, 50, 25, 10].map((height, i) => (
                      <div key={i} className="w-full bg-secondary-container/20 rounded-t-lg relative" style={{height: '100%'}}>
                        <div
                          className="absolute bottom-0 w-full bg-secondary rounded-t-lg transition-all duration-500"
                          style={{height: `${height * (result.health_percentage / 100)}%`, opacity: 1 - i * 0.15}}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <button 
                  onClick={handleDownloadPDF}
                  className="w-full mt-10 border-2 border-secondary text-secondary py-3 rounded-xl font-bold hover:bg-secondary/5 transition-all flex items-center justify-center gap-2"
                >
                  <span className="material-symbols-outlined text-lg">download</span>
                  Download Detailed PDF Report
                </button>
              </div>

              <div className="bg-primary/5 rounded-xl p-6 flex items-start gap-4 border-l-4 border-primary">
                <span className="material-symbols-outlined text-primary mt-1">eco</span>
                <div>
                  <h4 className="font-bold text-on-surface">Environmental Impact</h4>
                  <p className="text-sm text-on-surface-variant mt-1 leading-relaxed">
                    Extending this device's life by {result.remaining_years} years avoids approximately {result.co2_avoided}kg of CO2 emissions from new manufacturing.
                  </p>
                </div>
              </div>

              <div className="bg-surface-container-low rounded-xl p-6 border border-outline-variant">
                <h4 className="font-bold text-on-surface mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-secondary">account_balance_wallet</span>
                  Repair vs. Replace Analyzer
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-surface-container-highest rounded-lg text-center border-t-4 border-error">
                    <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-1">Est. New Cost</p>
                    <p className="text-2xl font-black text-on-surface">₹{result.replace_cost?.toLocaleString() || "0"}</p>
                  </div>
                  <div className="p-4 bg-surface-container-highest rounded-lg text-center border-t-4 border-primary">
                    <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-1">Avg Repair Cost</p>
                    <p className="text-2xl font-black text-primary">₹{result.repair_cost?.toLocaleString() || "0"}</p>
                  </div>
                </div>
                <p className="text-sm text-on-surface-variant mt-4 text-center">
                  Repairing saves <span className="font-bold text-on-surface">₹{((result.replace_cost || 0) - (result.repair_cost || 0)).toLocaleString()}</span> and extends device life, making it the most sustainable choice for {formData.institution || 'your institution'}.
                </p>
              </div>
            </>
          ) : (
            <div className="bg-surface-container-lowest rounded-xl p-8 text-center">
              <span className="material-symbols-outlined text-6xl text-outline mb-4">analytics</span>
              <p className="text-on-surface-variant">Enter device details to see lifespan prediction</p>
            </div>
          )}
        </section>
      </div>

      <section className="mt-12 bg-surface-container-low rounded-xl p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-xl">
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-on-surface-variant">terminal</span>
              <h3 className="font-bold text-on-surface">Algorithm Context</h3>
            </div>
            <p className="text-on-surface-variant text-sm leading-relaxed">
              Prediction Model: Random Forest Aggregation. Our ensemble learning method utilizes multiple decision trees to produce more accurate lifespan forecasts by mapping historical environmental telemetry to hardware failure patterns.
            </p>
          </div>
          <div className="bg-surface-container-lowest p-6 rounded-lg font-mono text-secondary font-bold text-lg border border-outline-variant/30 shadow-sm">
            L = (1/N) * Σ f_i(M, T, E, U, P, S)
          </div>
        </div>
      </section>
    </div>
  )
}

export default LifespanPredictor
