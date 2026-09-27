import { expect, test, type Page } from '@playwright/test'
import path from 'node:path'

const errors = new WeakMap<Page, string[]>()
test.beforeEach(({ page }) => {
  const messages: string[] = []
  errors.set(page, messages)
  page.on('pageerror', (error) => messages.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') messages.push(message.text()) })
})
test.afterEach(({ page }) => expect(errors.get(page)).toEqual([]))

async function query(page: Page, action: () => Promise<unknown>, type: string, scope = 'jurisdiction:AU') {
  const pending = page.waitForResponse((response) => {
    if (!response.url().includes('/api/v1/graph/query') || response.request().method() !== 'POST') return false
    const body = response.request().postDataJSON()
    return body.scope === scope && body.type === type && body.query === ''
  })
  await action()
  const response = await pending
  expect(response.ok()).toBe(true)
  expect(response.request().postDataJSON()).toMatchObject({ scope, type, query: '' })
  const graph = (await response.json()).data
  expect(graph.nodes.some((node: { type: string }) => node.type === type)).toBe(true)
  await expect(page.getByLabel('Category', { exact: true })).toHaveValue(type)
  await expect(page.locator('.graph-canvas')).toBeVisible()
}

test('category keywords run structured queries and names remain searchable', async ({ page }) => {
  await page.goto('/graph')
  await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeEnabled()
  await page.getByLabel('Graph query').fill('products')
  await query(page, () => page.getByRole('button', { name: 'Search', exact: true }).click(), 'PesticideProduct')
  await page.getByLabel('Graph query').fill('Frutor Fungicide')
  const response = page.waitForResponse((item) => item.url().includes('/api/v1/graph/query'))
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  const result = await response
  expect(result.request().postDataJSON()).toMatchObject({ type: 'PesticideProduct', query: 'Frutor Fungicide' })
  expect((await result.json()).data.nodes.length).toBeGreaterThan(0)
})

test('sidebar categories filter, reset, and follow jurisdiction and website scopes', async ({ page }, info) => {
  if (info.project.name.startsWith('desktop')) await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/graph')
  await expect(page.getByRole('heading', { name: 'Graph browser', exact: true })).toBeVisible()
  const toggle = page.getByRole('button', { name: 'Labels and relationships', exact: true })
  if (await toggle.isVisible()) await toggle.click()
  const search = page.getByLabel('Search categories', { exact: true })
  await search.fill('cro')
  const category = page.locator('.graph-label-row[title="CropTerm"]')
  await expect(category).toBeVisible()
  await expect(page.locator('.graph-label-row[title="PesticideProduct"]')).toHaveCount(0)
  await query(page, () => category.click(), 'CropTerm')
  await expect(category).toHaveAttribute('aria-pressed', 'true')
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  if (process.env.PESTKG_VISUAL_DIR) {
    await page.screenshot({ path: path.join(process.env.PESTKG_VISUAL_DIR, `categories-${info.project.name}.png`), fullPage: true })
  }
  await search.fill('no-such-category')
  await expect(page.getByRole('status').filter({ hasText: 'No matching categories' })).toBeVisible()
  await page.locator('.graph-label-row').getByText('All categories', { exact: true }).click()
  await expect(page.getByLabel('Category', { exact: true })).toHaveValue('')
  await page.getByLabel('Graph scope', { exact: true }).selectOption('reference:CHEBI')
  await expect(search).toHaveValue('')
  await expect(page.getByLabel('Category', { exact: true }).locator('option[value="PesticideProduct"]')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeEnabled()
  await page.getByLabel('Graph query').fill('chebi')
  await query(page, () => page.getByRole('button', { name: 'Search', exact: true }).click(), 'ChEBITerm', 'reference:CHEBI')
})

test('all loaded scopes expose categories without double-counting scope totals', async ({ page }) => {
  await page.goto('/graph?scope=all')
  await expect(page.getByRole('heading', { name: 'Graph browser', exact: true })).toBeVisible()
  const toggle = page.getByRole('button', { name: 'Labels and relationships', exact: true })
  if (await toggle.isVisible()) await toggle.click()
  await expect(page.getByLabel('Category', { exact: true }).locator('option[value="CropTerm"]')).toHaveCount(1)
  await expect(page.getByLabel('Category', { exact: true }).locator('option[value="ChEBITerm"]')).toHaveCount(1)
  await expect(page.locator('.graph-label-row[title="CropTerm"] small')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Search', exact: true })).toBeEnabled()
  await page.getByLabel('Graph query').fill('作物')
  await query(page, () => page.getByRole('button', { name: 'Search', exact: true }).click(), 'CropTerm', 'all')
})

test('category controls fit a narrow viewport', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 })
  await page.goto('/graph')
  await expect(page.getByLabel('Category', { exact: true })).toBeVisible()
  await query(page, () => page.getByLabel('Category', { exact: true }).selectOption('RegulatoryOrganization'), 'RegulatoryOrganization')
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
})
