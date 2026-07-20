import { describe, expect, it } from 'vitest'
import { statAccentClass } from './History'

describe('history statistic styles', () => {
  it('uses complete static Tailwind class names for production extraction', () => {
    expect(statAccentClass('primary')).toBe('text-primary')
    expect(statAccentClass('emerald-600')).toBe('text-emerald-600')
    expect(statAccentClass('green-600')).toBe('text-green-600')
  })
})
