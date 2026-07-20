import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { fadeInUp } from '../utils/motion'

function Footer() {
  return (
    <motion.footer className="w-full py-12 border-t-0 bg-surface mt-auto" variants={fadeInUp} initial="hidden" animate="visible">
      <div className="flex flex-col md:flex-row justify-between items-center px-8 max-w-7xl mx-auto">
        <div className="mb-6 md:mb-0">
          <span className="font-headline font-bold text-primary text-xl">E-Waste Management</span>
        </div>
        <div className="flex flex-col md:flex-row items-center gap-8 mb-6 md:mb-0">
          <Link to="/privacy" className="font-body text-xs uppercase tracking-widest text-on-surface-variant opacity-70 hover:text-primary transition-colors">
            Privacy Notice
          </Link>
          <Link to="/terms" className="font-body text-xs uppercase tracking-widest text-on-surface-variant opacity-70 hover:text-primary transition-colors">
            Terms of Use
          </Link>
          <Link to="/methodology" className="font-body text-xs uppercase tracking-widest text-on-surface-variant opacity-70 hover:text-primary transition-colors">
            Methodology
          </Link>
        </div>
        <p className="font-body text-xs uppercase tracking-widest text-on-surface-variant opacity-70">
          {new Date().getFullYear()} E-Waste Management. Preserving the digital ecosystem.
        </p>
      </div>
    </motion.footer>
  )
}

export default Footer
