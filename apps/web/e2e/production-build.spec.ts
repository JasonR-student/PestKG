import { expect, test } from '@playwright/test'

test('production chart routes boot without runtime errors @production', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.route('**/api/v1/releases', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ data: [] }),
  }))

  await page.goto('/')
  await expect(page.locator('.app-shell')).toBeVisible()
  await page.goto('/compare')
  await expect(page.getByRole('heading', { name: 'Cross-jurisdiction competency questions' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Cross-jurisdiction competency questions' })).toBeVisible()
  expect(errors).toEqual([])
})
