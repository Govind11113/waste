import { motion, useReducedMotion } from 'framer-motion'
import { pageTransition } from '../utils/motion'

/** @param {{ children: import('react').ReactNode, className?: string }} props */
export default function AnimatedPage({ children, className = '' }) {
  const reduce = useReducedMotion()
  const variants = reduce
    ? { initial: { opacity: 1 }, animate: { opacity: 1 }, exit: { opacity: 1 } }
    : pageTransition
  return (
    <motion.div
      className={className}
      variants={variants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      {children}
    </motion.div>
  )
}
