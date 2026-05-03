import { Link } from 'react-router-dom'

function Home() {
  const stats = [
    { label: "Global E-Waste", value: "62M Tons", subtext: "Generated annually" },
    { label: "Maharashtra Output", value: "450K Tons", subtext: "State contribution" },
    { label: "Recovery Rate", value: "17.4%", subtext: "Only 10.8M tons" },
    { label: "Platform Efficiency", value: "98.5%", subtext: "Classification accuracy" }
  ]

  const features = [
    {
      icon: "photo_camera",
      title: "Classification",
      description: "Instant e-waste identification using H200-trained ResNet50 model",
      link: "/scanner"
    },
    {
      icon: "hourglass_empty",
      title: "Lifespan Prediction",
      description: "Statistical model predicting remaining device life using environmental factors",
      link: "/lifespan"
    },
    {
      icon: "eco",
      title: "Carbon Calculator",
      description: "Precise CO2 footprint calculations with grid intensity integration",
      link: "/inventory"
    },
    {
      icon: "history",
      title: "History Tracking",
      description: "Complete audit trail of all scans and calculations for compliance",
      link: "/history"
    }
  ]

  return (
    <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto">
      {/* Hero Section */}
      <header className="mb-20">
        <div className="max-w-3xl">
          <h1 className="text-6xl font-extrabold text-on-surface tracking-tight mb-6">
            Precision E-Waste<br />Management for<br />
            <span className="text-primary">Maharashtra Education</span>
          </h1>
          <p className="text-xl text-on-surface-variant mb-8 leading-relaxed">
            Transforming institutional electronics sustainability through classification,
            predictive analytics, and carbon tracking.
          </p>
          <div className="flex gap-4">
            <Link to="/scanner" className="bg-primary text-on-primary px-8 py-4 rounded-xl font-bold text-lg hover:opacity-90 transition-all shadow-lg shadow-primary/20">
              Start Classification
            </Link>
            <Link to="/dashboard" className="border-2 border-outline text-on-surface px-8 py-4 rounded-xl font-bold text-lg hover:bg-surface-container transition-all">
              View Dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Stats Ticker */}
      <section className="mb-20 grid grid-cols-2 md:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <div key={index} className="bg-surface-container-lowest p-6 rounded-xl shadow-sm">
            <p className="text-3xl font-black text-on-surface tracking-tight">{stat.value}</p>
            <p className="text-sm font-semibold text-on-surface-variant">{stat.label}</p>
            <p className="text-xs text-outline mt-1">{stat.subtext}</p>
          </div>
        ))}
      </section>

      {/* Feature Cards */}
      <section className="mb-20">
        <h2 className="text-3xl font-bold text-on-surface mb-10">Platform Capabilities</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <Link
              key={index}
              to={feature.link}
              className="bg-surface-container-lowest p-8 rounded-xl hover:shadow-lg transition-all duration-300 group"
            >
              <span className="material-symbols-outlined text-4xl text-primary mb-4 group-hover:text-secondary transition-colors">
                {feature.icon}
              </span>
              <h3 className="text-xl font-bold text-on-surface mb-2">{feature.title}</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed">{feature.description}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Urgency Section */}
      <section className="mb-20 bg-surface-container-low rounded-xl p-10">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-bold text-on-surface mb-4">Why E-Waste Management Matters</h2>
          <p className="text-on-surface-variant leading-relaxed mb-6">
            Electronic waste is the fastest-growing waste stream globally. In Maharashtra alone,
            educational institutions generate an estimated 45,000 tons of e-waste annually. Proper
            management is critical for environmental compliance and resource recovery.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-surface-container-lowest p-4 rounded-lg">
              <span className="text-2xl font-bold text-primary">70%</span>
              <p className="text-sm text-on-surface-variant">Total toxic waste from electronics</p>
            </div>
            <div className="bg-surface-container-lowest p-4 rounded-lg">
              <span className="text-2xl font-bold text-secondary">$62.5B</span>
              <p className="text-sm text-on-surface-variant">Value of recoverable materials</p>
            </div>
          </div>
        </div>
      </section>

      {/* Impact Bento Grid */}
      <section className="mb-20">
        <h2 className="text-3xl font-bold text-on-surface mb-10">Environmental Impact</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-primary-container p-8 rounded-xl text-on-primary-container">
            <span className="material-symbols-outlined text-4xl mb-4">cloud_off</span>
            <p className="text-4xl font-black mb-2">2,450</p>
            <p className="text-sm font-semibold">Tons CO2 Averted</p>
          </div>
          <div className="bg-secondary-container p-8 rounded-xl text-on-secondary-container">
            <span className="material-symbols-outlined text-4xl mb-4">recycling</span>
            <p className="text-4xl font-black mb-2">89%</p>
            <p className="text-sm font-semibold">Recovery Rate</p>
          </div>
          <div className="bg-tertiary-container p-8 rounded-xl text-on-tertiary-container">
            <span className="material-symbols-outlined text-4xl mb-4">forest</span>
            <p className="text-4xl font-black mb-2">12,800</p>
            <p className="text-sm font-semibold">Trees Equivalent</p>
          </div>
        </div>
      </section>

      {/* News Section */}
      <section>
        <h2 className="text-3xl font-bold text-on-surface mb-10">Maharashtra E-Waste Updates</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-surface-container-lowest p-6 rounded-xl">
            <p className="text-xs font-bold uppercase tracking-widest text-secondary mb-2">Policy</p>
            <h3 className="text-lg font-bold text-on-surface mb-2">New EPR Guidelines 2024</h3>
            <p className="text-sm text-on-surface-variant">Extended Producer Responsibility mandates updated for educational institutions.</p>
          </div>
          <div className="bg-surface-container-lowest p-6 rounded-xl">
            <p className="text-xs font-bold uppercase tracking-widest text-primary mb-2">Technology</p>
            <h3 className="text-lg font-bold text-on-surface mb-2">Classification Rollout</h3>
            <p className="text-sm text-on-surface-variant">Automated e-waste sorting systems deployed across 150+ institutions.</p>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Home
