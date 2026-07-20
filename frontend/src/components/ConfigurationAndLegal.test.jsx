import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ConfigurationError from './ConfigurationError'
import LegalPage from './LegalPage'

vi.mock('./AnimatedPage', () => ({
  /** @param {{ children: import('react').ReactNode }} props */
  default: ({ children }) => <>{children}</>,
}))

/** @type {Array<['privacy' | 'terms' | 'methodology', string, string]>} */
const policyCases = [
  ['privacy', 'Privacy Notice', 'local SQLite database'],
  ['terms', 'Terms of Use', 'decision-support software'],
  ['methodology', 'Methodology', 'seven-factor weighted formula'],
]

describe('configuration and policy pages', () => {
  it('shows actionable Windows setup guidance instead of a blank page', () => {
    render(<ConfigurationError message="Missing public authentication configuration" />)

    expect(screen.getByRole('alert')).toHaveTextContent('not configured yet')
    expect(screen.getByRole('alert')).toHaveTextContent('Configure E-Waste.cmd')
    expect(screen.getByRole('alert')).toHaveTextContent('pk_test_')
    expect(screen.getByRole('button', { name: 'Retry configuration' })).toBeEnabled()
  })

  it.each(policyCases)('renders the %s page with its evidence boundary', (page, title, evidence) => {
    render(<LegalPage page={page} />)

    expect(screen.getByRole('heading', { name: title, level: 1 })).toBeVisible()
    expect(screen.getByText(new RegExp(evidence, 'i'))).toBeVisible()
  })
})
