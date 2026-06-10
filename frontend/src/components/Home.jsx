import { Link, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import MaharashtraWeatherMap from './MaharashtraWeatherMap'

function Home() {
  const navigate = useNavigate()
  const { isSignedIn, isLoaded } = useAuth()

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      navigate('/dashboard', { replace: true })
    }
  }, [isLoaded, isSignedIn, navigate])

  if (!isLoaded || isSignedIn) {
    return null
  }

  const features = [
    {
      icon: "photo_camera",
      title: "Image Classifier",
      description: "Identify e-waste devices using CLIP/SigLIP zero-shot vision models covering 40+ electronic categories.",
      link: "/scanner"
    },
    {
      icon: "hourglass_empty",
      title: "Lifespan Predictor",
      description: "Predict remaining device life with a transparent weighted-average formula across age, usage, and environment.",
      link: "/lifespan"
    },
    {
      icon: "eco",
      title: "Carbon Calculator",
      description: "Estimate lifetime carbon footprint with grid-intensity-aware operational emissions.",
      link: "/inventory"
    },
    {
      icon: "history",
      title: "Activity History",
      description: "Track every scan and prediction in a chronological audit log.",
      link: "/history"
    }
  ]

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
      <header className="mb-20 animate-fade-in-down">
        <div className="max-w-3xl">
          <h1 className="text-6xl font-extrabold text-on-surface tracking-tight mb-6">
            E-Waste Management for<br />
            <span className="text-primary">Maharashtra Education</span>
          </h1>
          <p className="text-xl text-on-surface-variant mb-8 leading-relaxed">
            Classify, predict, and track the lifecycle of institutional electronics — from IT lab computers to AC units.
          </p>
          <div className="flex gap-4">
            <Link to="/signup" className="bg-primary text-on-primary px-8 py-4 rounded-xl font-bold text-lg hover:opacity-90 transition-all shadow-lg shadow-primary/20 hover:-translate-y-0.5 hover:shadow-xl active:scale-[0.98] btn-ripple">
              Get Started
            </Link>
            <Link to="/login" className="border-2 border-outline text-on-surface px-8 py-4 rounded-xl font-bold text-lg hover:bg-surface-container transition-all hover:-translate-y-0.5 active:scale-[0.98]">
              Sign In
            </Link>
          </div>
        </div>
      </header>

      <section className="mb-20 animate-fade-in-up" style={{animationDelay: '0.15s'}}>
        <MaharashtraWeatherMap />
      </section>

      <section className="mb-20 animate-fade-in-up" style={{animationDelay: '0.2s'}}>
        <h2 className="text-3xl font-bold text-on-surface mb-10">Platform Capabilities</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <Link
              key={index}
              to={feature.link}
              className="bg-surface-container-lowest p-8 rounded-xl hover:shadow-lg transition-all duration-300 group hover-lift card-shadow animate-fade-in-up"
              style={{animationDelay: `${(index + 2) * 0.1}s`}}
            >
              <span className="material-symbols-outlined text-4xl text-primary mb-4 group-hover:text-secondary transition-all duration-300 group-hover:scale-110 inline-block">
                {feature.icon}
              </span>
              <h3 className="text-xl font-bold text-on-surface mb-2 group-hover:text-primary transition-colors duration-300">{feature.title}</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed">{feature.description}</p>
            </Link>
          ))}
        </div>
      </section>

      <section className="mb-20 bg-surface-container-low rounded-xl p-10 animate-fade-in-up" style={{animationDelay: '0.5s'}}>
        <div className="max-w-2xl">
          <h2 className="text-3xl font-bold text-on-surface mb-4">Why E-Waste Management Matters</h2>
          <p className="text-on-surface-variant leading-relaxed mb-6">
            Electronic waste is the fastest-growing waste stream globally. Educational institutions in Maharashtra
            must comply with the E-Waste (Management) Rules, 2022, channeling end-of-life electronics through
            authorized recyclers and maintaining audit-ready disposal records.
          </p>
        </div>
      </section>

      <section className="mb-20 animate-fade-in-up" style={{animationDelay: '0.55s'}}>
        <h2 className="text-3xl font-bold text-on-surface mb-3">Maharashtra Regional Insights</h2>
        <p className="text-on-surface-variant mb-8">E-waste output and recycling capacity across the state's six divisions</p>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[
            { division: 'Konkan', cities: 'Mumbai, Thane, Raigad', share: '38%', tone: 'High', color: 'error' },
            { division: 'Pune', cities: 'Pune, Satara, Sangli', share: '22%', tone: 'High', color: 'error' },
            { division: 'Nashik', cities: 'Nashik, Dhule, Jalgaon', share: '11%', tone: 'Medium', color: 'tertiary' },
            { division: 'Aurangabad', cities: 'Aurangabad, Beed, Latur', share: '9%', tone: 'Medium', color: 'tertiary' },
            { division: 'Nagpur', cities: 'Nagpur, Wardha, Chandrapur', share: '14%', tone: 'High', color: 'error' },
            { division: 'Amravati', cities: 'Amravati, Akola, Buldhana', share: '6%', tone: 'Low', color: 'primary' },
          ].map((d, i) => (
            <div key={d.division} className="bg-surface-container-lowest rounded-xl p-6 hover-lift card-shadow animate-fade-in-up" style={{animationDelay: `${0.6 + i * 0.05}s`}}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-lg font-bold text-on-surface">{d.division} Division</h3>
                  <p className="text-xs text-on-surface-variant mt-1">{d.cities}</p>
                </div>
                <span className={`text-xs font-bold uppercase tracking-wider px-2 py-1 rounded-full bg-${d.color}/10 text-${d.color}`} style={{
                  backgroundColor: d.color === 'error' ? 'rgba(186, 26, 26, 0.1)' : d.color === 'tertiary' ? 'rgba(125, 82, 96, 0.1)' : 'rgba(46, 125, 50, 0.1)',
                  color: d.color === 'error' ? 'var(--error)' : d.color === 'tertiary' ? 'var(--tertiary)' : 'var(--primary)'
                }}>
                  {d.tone}
                </span>
              </div>
              <div className="flex items-baseline gap-2 mt-4">
                <span className="text-3xl font-black text-on-surface">{d.share}</span>
                <span className="text-sm text-on-surface-variant">of state e-waste</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-20 animate-fade-in-up" style={{animationDelay: '0.65s'}}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-tertiary/5 border-l-4 border-tertiary rounded-xl p-8 hover-lift card-shadow">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-3xl text-tertiary">water_drop</span>
              <h3 className="text-xl font-bold text-on-surface">Monsoon Advisory</h3>
            </div>
            <p className="text-on-surface-variant leading-relaxed text-sm">
              Maharashtra's monsoon (June–September) brings humidity above 80% in coastal Konkan and ghat regions.
              Store IT lab spares in sealed bins with silica gel. Servers and switches need consistent AC; condensation on PCBs
              shortens lifespan by up to 30%.
            </p>
          </div>
          <div className="bg-primary/5 border-l-4 border-primary rounded-xl p-8 hover-lift card-shadow">
            <div className="flex items-center gap-3 mb-4">
              <span className="material-symbols-outlined text-3xl text-primary">gavel</span>
              <h3 className="text-xl font-bold text-on-surface">EPR Compliance Reminder</h3>
            </div>
            <p className="text-on-surface-variant leading-relaxed text-sm">
              Under E-Waste Rules 2022, educational institutions must dispose of end-of-life electronics only through
              MPCB-authorized recyclers. Maintain manifest records for 5 years. Annual filing due 30 June each financial year.
            </p>
          </div>
        </div>
      </section>

      <section className="mb-20 animate-fade-in-up" style={{animationDelay: '0.7s'}}>
        <h2 className="text-3xl font-bold text-on-surface mb-3">Authorized Recyclers in Maharashtra</h2>
        <p className="text-on-surface-variant mb-8">MPCB-listed e-waste handlers serving educational institutions</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { name: 'Eco Recycling Ltd (Ecoreco)', city: 'Mumbai', cap: '7,200 TPA', accent: 'primary' },
            { name: 'Attero Recycling Pvt Ltd', city: 'Pune', cap: '4,800 TPA', accent: 'secondary' },
            { name: 'Greenscape Eco Management', city: 'Nashik', cap: '2,400 TPA', accent: 'tertiary' },
            { name: 'Trishyiraya Recycling', city: 'Nagpur', cap: '3,000 TPA', accent: 'primary' },
          ].map((r, i) => (
            <div key={r.name} className="bg-surface-container-lowest rounded-xl p-5 flex items-center gap-4 hover-lift card-shadow animate-fade-in-up" style={{animationDelay: `${0.75 + i * 0.05}s`}}>
              <div className="w-12 h-12 rounded-lg bg-primary-container flex items-center justify-center shrink-0">
                <span className="material-symbols-outlined text-primary">recycling</span>
              </div>
              <div className="flex-grow min-w-0">
                <p className="font-bold text-on-surface truncate">{r.name}</p>
                <p className="text-sm text-on-surface-variant">{r.city} · Capacity: {r.cap}</p>
              </div>
              <span className="material-symbols-outlined text-outline">verified</span>
            </div>
          ))}
        </div>
      </section>

      <section className="animate-fade-in-up" style={{animationDelay: '0.6s'}}>
        <div className="bg-primary/5 border border-primary/20 rounded-xl p-10 text-center">
          <h2 className="text-3xl font-bold text-on-surface mb-4">Ready to Start?</h2>
          <p className="text-on-surface-variant mb-6 max-w-xl mx-auto">
            Sign up to access the classifier, lifespan predictor, and carbon calculator.
          </p>
          <Link to="/signup" className="inline-block bg-primary text-on-primary px-8 py-3 rounded-xl font-bold hover:opacity-90 transition-all hover:-translate-y-0.5 hover:shadow-xl active:scale-[0.98] btn-ripple">
            Create an Account
          </Link>
        </div>
      </section>
    </div>
  )
}

export default Home
