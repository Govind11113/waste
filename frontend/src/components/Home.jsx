import { Link, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuth } from '@clerk/clerk-react'
import { motion } from 'framer-motion'
import MaharashtraWeatherMap from './MaharashtraWeatherMap'
import AnimatedPage from './AnimatedPage'
import { fadeInUp, stagger } from '../utils/motion'

const MotionLink = motion(Link)

function Home() {
  const navigate = useNavigate()
  const { isSignedIn, isLoaded } = useAuth()

  useEffect(() => {
    if (isLoaded && isSignedIn) navigate('/dashboard', { replace: true })
  }, [isLoaded, isSignedIn, navigate])

  if (!isLoaded || isSignedIn) return null

  const features = [
    {
      icon: 'photo_camera',
      title: 'Image Classifier',
      description: 'Classify images into 20 canonical device categories with a pre-trained SigLIP 2 or CLIP zero-shot model and explicit rejection gates.',
      link: '/scanner',
    },
    {
      icon: 'hourglass_empty',
      title: 'Lifespan Estimator',
      description: 'Calculate a remaining-life planning estimate with a transparent seven-factor weighted formula.',
      link: '/lifespan',
    },
    {
      icon: 'eco',
      title: 'Carbon Calculator',
      description: 'Calculate deterministic embodied-plus-operational scenarios from profile and user inputs.',
      link: '/inventory',
    },
    {
      icon: 'timeline',
      title: 'Cohort Forecast',
      description: 'Project submitted in-service cohorts with a disclosed, uncalibrated conditional Weibull curve.',
      link: '/generation',
    },
    {
      icon: 'history',
      title: 'Activity History',
      description: 'Review your authenticated scan, lifespan, and carbon calculation records.',
      link: '/history',
    },
  ]

  return (
    <AnimatedPage>
      <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto page-transition">
        <motion.header className="mb-20 animate-fade-in-down" variants={fadeInUp} initial="hidden" animate="visible">
          <div className="max-w-3xl">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-4">Decision-support prototype</p>
            <h1 className="text-5xl sm:text-6xl font-extrabold text-on-surface tracking-tight mb-6">
              E-Waste Planning for<br />
              <span className="text-primary">Maharashtra Education</span>
            </h1>
            <p className="text-xl text-on-surface-variant mb-8 leading-relaxed">
              Explore transparent workflows for classifying device images, estimating lifespan and carbon scenarios, and projecting submitted inventory cohorts.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link to="/signup" className="bg-primary text-on-primary px-8 py-4 rounded-xl font-bold text-lg hover:opacity-90 transition-all shadow-lg shadow-primary/20 hover:-translate-y-0.5 hover:shadow-xl active:scale-[0.98] btn-ripple">
                Get Started
              </Link>
              <Link to="/login" className="border-2 border-outline text-on-surface px-8 py-4 rounded-xl font-bold text-lg hover:bg-surface-container transition-all hover:-translate-y-0.5 active:scale-[0.98]">
                Sign In
              </Link>
            </div>
          </div>
        </motion.header>

        <section className="mb-20 animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
          <MaharashtraWeatherMap />
        </section>

        <section className="mb-20 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          <h2 className="text-3xl font-bold text-on-surface mb-3">Implemented Capabilities</h2>
          <p className="text-on-surface-variant mb-10">Each workflow labels its assumptions and keeps calculated outputs separate from observed evidence.</p>
          <motion.div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-6" variants={stagger} initial="hidden" animate="visible">
            {features.map((feature, index) => (
              <MotionLink
                key={feature.title}
                to={feature.link}
                variants={fadeInUp}
                className="bg-surface-container-lowest p-7 rounded-xl hover:shadow-lg transition-all duration-300 group hover-lift card-shadow animate-fade-in-up"
                style={{ animationDelay: `${(index + 2) * 0.1}s` }}
              >
                <span className="material-symbols-outlined text-4xl text-primary mb-4 group-hover:text-secondary transition-all duration-300 group-hover:scale-110 inline-block" aria-hidden="true">
                  {feature.icon}
                </span>
                <h3 className="text-xl font-bold text-on-surface mb-2 group-hover:text-primary transition-colors duration-300">{feature.title}</h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">{feature.description}</p>
              </MotionLink>
            ))}
          </motion.div>
        </section>

        <section className="mb-20 bg-surface-container-low rounded-xl p-8 sm:p-10 animate-fade-in-up" style={{ animationDelay: '0.5s' }} aria-labelledby="evidence-boundary-heading">
          <h2 id="evidence-boundary-heading" className="text-3xl font-bold text-on-surface mb-4">Evidence Boundary</h2>
          <p className="text-on-surface-variant leading-relaxed max-w-4xl">
            This repository demonstrates working software, not a completed institutional study. It contains no committed representative real-image benchmark, observed retirement or disposal series, or expert survey responses. Carbon values, profile lifespans, and cohort curves are planning assumptions rather than measured Maharashtra-wide outcomes.
          </p>
        </section>

        <section className="mb-20 animate-fade-in-up" style={{ animationDelay: '0.6s' }}>
          <h2 className="text-3xl font-bold text-on-surface mb-8">Use the Prototype Responsibly</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-surface-container-lowest rounded-xl p-7 card-shadow">
              <span className="material-symbols-outlined text-3xl text-primary mb-3" aria-hidden="true">inventory_2</span>
              <h3 className="text-lg font-bold text-on-surface mb-2">Supply real inventory inputs</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed">Forecasts describe only the cohorts submitted by the user. They do not estimate a statewide total or add future purchases.</p>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-7 card-shadow">
              <span className="material-symbols-outlined text-3xl text-secondary mb-3" aria-hidden="true">science</span>
              <h3 className="text-lg font-bold text-on-surface mb-2">Validate before research claims</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed">Classifier, lifespan, carbon, and cohort outputs require appropriate real data before accuracy or impact claims can be made.</p>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-7 card-shadow">
              <span className="material-symbols-outlined text-3xl text-tertiary mb-3" aria-hidden="true">fact_check</span>
              <h3 className="text-lg font-bold text-on-surface mb-2">Verify current requirements</h3>
              <p className="text-sm text-on-surface-variant leading-relaxed">Confirm current CPCB/MPCB rules and recycler authorization in official registers. This prototype is not a legal or recycler registry.</p>
            </div>
          </div>
        </section>

        <section className="animate-fade-in-up">
          <div className="bg-primary/5 border border-primary/20 rounded-xl p-10 text-center">
            <h2 className="text-3xl font-bold text-on-surface mb-4">Explore the Workflows</h2>
            <p className="text-on-surface-variant mb-6 max-w-xl mx-auto">Create an account to use the protected tools and keep per-user activity history.</p>
            <Link to="/signup" className="inline-block bg-primary text-on-primary px-8 py-3 rounded-xl font-bold hover:opacity-90 transition-all hover:-translate-y-0.5 hover:shadow-xl active:scale-[0.98] btn-ripple">
              Create an Account
            </Link>
          </div>
        </section>
      </div>
    </AnimatedPage>
  )
}

export default Home
