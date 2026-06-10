function Footer() {
  return (
    <footer className="w-full py-12 border-t-0 bg-surface mt-auto">
      <div className="flex flex-col md:flex-row justify-between items-center px-8 max-w-7xl mx-auto">
        <div className="mb-6 md:mb-0">
          <span className="font-headline font-bold text-primary text-xl">E-Waste Management</span>
        </div>
        <div className="flex flex-col md:flex-row items-center gap-8 mb-6 md:mb-0">
          <a href="#" className="font-body text-xs uppercase tracking-widest text-on-surface-variant opacity-70 hover:text-primary transition-colors">
            Privacy Policy
          </a>
          <a href="#" className="font-body text-xs uppercase tracking-widest text-on-surface-variant opacity-70 hover:text-primary transition-colors">
            Terms of Service
          </a>
          <a href="#" className="font-body text-xs uppercase tracking-widest text-on-surface-variant opacity-70 hover:text-primary transition-colors">
            Methodology
          </a>
        </div>
        <p className="font-body text-xs uppercase tracking-widest text-on-surface-variant opacity-70">
          2025 E-Waste Management. Preserving the digital ecosystem.
        </p>
      </div>
    </footer>
  )
}

export default Footer
