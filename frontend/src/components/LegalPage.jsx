import AnimatedPage from './AnimatedPage'

const PAGES = {
  privacy: {
    eyebrow: 'Data handling',
    title: 'Privacy Notice',
    sections: [
      ['What this application stores', 'Authenticated scan, lifespan, and carbon-calculation records are stored in a local SQLite database on the computer running the application. Records are associated with the Clerk user identifier supplied in the verified session token.'],
      ['Images and filenames', 'Uploaded image bytes are processed in memory for classification and are not intentionally saved by the application. The submitted filename and calculated result may be retained in local history.'],
      ['External services', 'Clerk processes authentication. Open-Meteo and map-tile providers receive ordinary browser network requests when the weather map is displayed. Review those providers’ current notices before operational deployment.'],
      ['Your controls', 'You can clear each category of your own history from the History page. The Windows guide explains where the local database is stored and how to back it up or remove it.'],
    ],
  },
  terms: {
    eyebrow: 'Responsible use',
    title: 'Terms of Use',
    sections: [
      ['Prototype status', 'This application is decision-support software, not a certified inspection service, legal registry, warranty assessment, or completed empirical study.'],
      ['No accuracy guarantee', 'Classifier labels, condition heuristics, lifespan estimates, carbon calculations, and cohort projections depend on models and disclosed assumptions. Verify results before making disposal, procurement, safety, legal, or financial decisions.'],
      ['Safe handling', 'Do not dismantle, transport, or dispose of damaged batteries or hazardous electronics solely on the basis of this application. Use current official CPCB/MPCB guidance and authorized recyclers.'],
      ['Acceptable use', 'Do not upload unlawful material, attempt to access another user’s records, bypass authentication, overload the local service, or represent prototype outputs as certified measurements.'],
    ],
  },
  methodology: {
    eyebrow: 'Transparent assumptions',
    title: 'Methodology',
    sections: [
      ['Image classification', 'A three-stage pipeline applies deterministic image-quality checks, a vision-language electronics gate, and zero-shot scoring across 20 canonical device categories using the selected SigLIP 2 or CLIP preset.'],
      ['Lifespan estimate', 'The default result is a seven-factor weighted formula covering age, usage, temperature, power quality, environment, maintenance, and software/workload. The displayed range is scenario sensitivity, not a calibrated confidence interval.'],
      ['Carbon calculation', 'Embodied profile values are added to deterministic operational electricity estimates using submitted power, hours, rating, units, lifespan, and a postal-code grid-intensity lookup. Results are planning estimates, not certified life-cycle assessments.'],
    ],
  },
}

/** @param {{ page: 'privacy' | 'terms' | 'methodology' }} props */
export default function LegalPage({ page }) {
  const content = PAGES[page]
  return (
    <AnimatedPage>
      <div className="pt-32 pb-20 px-6 sm:px-8 max-w-4xl mx-auto page-transition">
        <header className="mb-10">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary mb-3">{content.eyebrow}</p>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-on-surface mb-4">{content.title}</h1>
          <p className="text-on-surface-variant">Applies to the local E-Waste Management decision-support prototype, version 3.</p>
        </header>
        <div className="space-y-5">
          {content.sections.map(([heading, body]) => (
            <section key={heading} className="bg-surface-container-lowest rounded-xl p-6 card-shadow">
              <h2 className="text-xl font-bold text-on-surface mb-2">{heading}</h2>
              <p className="text-on-surface-variant leading-relaxed">{body}</p>
            </section>
          ))}
        </div>
      </div>
    </AnimatedPage>
  )
}
