// Shared Framer Motion variants and micro-interaction presets.
// Pure data module — no component logic or layout here.
// See design §10 (Requirements 8.1, 8.9).

export const fadeInUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
}

export const stagger = {
  visible: { transition: { staggerChildren: 0.08 } },
}

export const pageTransition = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.2 } },
}

export const scaleReveal = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.35, ease: 'easeOut' } },
}

// Micro-interaction presets for whileHover / whileTap
export const hoverLift = { y: -2, transition: { duration: 0.15 } }
export const tapShrink = { scale: 0.98 }
