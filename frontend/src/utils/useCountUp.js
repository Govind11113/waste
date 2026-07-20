import { useEffect, useState } from 'react'
import { useReducedMotion } from 'framer-motion'

/** @param {number} target @param {number} [duration] */
export function useCountUp(target, duration = 1000) {
  const reduce = useReducedMotion()
  const [value, setValue] = useState(reduce ? target : 0)
  useEffect(() => {
    if (reduce) {
      setValue(target)
      return undefined
    }
    let raf = 0
    let start
    /** @param {number} timestamp */
    const tick = (timestamp) => {
      start ??= timestamp
      const progress = Math.min((timestamp - start) / duration, 1)
      setValue(target * (1 - Math.pow(1 - progress, 3)))
      if (progress < 1) raf = window.requestAnimationFrame(tick)
    }
    raf = window.requestAnimationFrame(tick)
    return () => window.cancelAnimationFrame(raf)
  }, [target, duration, reduce])
  return value
}
