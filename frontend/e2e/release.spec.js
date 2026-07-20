import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

const configuredRelease = Boolean(process.env.EWASTE_E2E_BASE_URL)
const authenticated = Boolean(process.env.EWASTE_E2E_AUTH_STATE)

test.describe('configured single-origin release', () => {
  test.skip(!configuredRelease, 'Set EWASTE_E2E_BASE_URL to a running configured release.')

  test('serves liveness, deep links, and accessible policy content', async ({ page, request }) => {
    const liveness = await request.get('/health/live')
    expect(liveness.ok()).toBeTruthy()
    await expect(liveness.json()).resolves.toMatchObject({ status: 'online' })

    for (const [path, heading] of [
      ['/privacy', 'Privacy Notice'],
      ['/terms', 'Terms of Use'],
      ['/methodology', 'Methodology'],
    ]) {
      await page.goto(path)
      await expect(page.getByRole('heading', { name: heading, level: 1 })).toBeVisible()
    }

    const results = await new AxeBuilder({ page }).analyze()
    expect(results.violations).toEqual([])
  })

  test.describe('authenticated workflow pages', () => {
    test.skip(!authenticated, 'Set EWASTE_E2E_AUTH_STATE to a Clerk development-session storage state.')

    for (const [path, heading] of [
      ['/dashboard', 'Dashboard'],
      ['/scanner', 'E-Waste Classifier'],
      ['/lifespan', 'Lifespan Estimator'],
      ['/inventory', 'Carbon Calculator'],
      ['/generation', 'E-Waste Generation Forecast'],
      ['/history', 'Activity History'],
    ]) {
      test(`${path} loads from an authenticated deep link`, async ({ page }) => {
        await page.goto(path)
        await expect(page.getByRole('heading', { name: heading, level: 1 })).toBeVisible()
        await expect(page).not.toHaveURL(/\/login/)
      })
    }
  })
})
