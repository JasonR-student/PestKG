import { expect, test, type Page } from '@playwright/test'

const browserErrors = new WeakMap<Page, string[]>()
let releaseId: string

test.beforeAll(async ({ request }) => {
  const response = await request.get('/api/v1/releases/active')
  expect(response.ok()).toBe(true)
  releaseId = (await response.json()).data.release_id
})

test.beforeEach(async ({ page }) => {
  const errors: string[] = []
  browserErrors.set(page, errors)
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
})

test.afterEach(async ({ page }, testInfo) => {
  const expectedStatuses = testInfo.annotations
    .filter((annotation) => annotation.type === 'expected-http-status')
    .map((annotation) => annotation.description)
  const unexpected = (browserErrors.get(page) ?? []).filter((message) =>
    !expectedStatuses.some((status) => message.startsWith(`Failed to load resource: the server responded with a status of ${status}`)),
  )
  expect(unexpected).toEqual([])
})

test('overview map opens a filtered exploration flow', async ({ page }) => {
  const overviewRequest = page.waitForRequest((request) => request.url().includes('/api/v1/stats/overview'))
  await page.goto('/')
  const request = await overviewRequest
  expect(request.headers()['x-pestkg-release']).toBe(releaseId)
  await expect(page).toHaveURL(new RegExp(`release=${releaseId}`))
  await expect(page.getByLabel(/数据版本|Data release/)).toHaveValue(releaseId)
  await expect(page).toHaveTitle(/PestKG|Pesticide/i)
  await expect(page.getByRole('heading', { name: /多国农药登记知识图谱|Multicountry pesticide/ })).toBeVisible()
  await expect(page.locator('.metric-item strong')).toHaveCount(5)
  await expect(page.locator('.data-mode')).toHaveText(/全量数据模式|Full release/)
  await expect(page.getByText(/暂未公开发布|Distribution blocked/)).toBeVisible()

  await page.getByRole('button', { name: /Australia: .* nodes/ }).click()
  await expect(page).toHaveURL(/\/explore\?.*jurisdiction=AU/)
  await expect(page).toHaveURL(new RegExp(`release=${releaseId}`))
  await expect(page.getByRole('heading', { name: /登记使用数据探索|Registration-use explorer/ })).toBeVisible()
  await expect(page.getByRole('table')).toBeVisible()
  await expect(page.locator('tbody .jurisdiction-code').first()).toHaveText('AU')
})

test('mobile workspace has no horizontal page overflow', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile'))
  for (const route of ['/', '/explore?jurisdiction=AU', '/downloads', '/compare']) {
    await page.goto(route)
    await expect(page.locator('main h1')).toBeVisible()
    if (route.startsWith('/explore') || route === '/compare') {
      await expect(page.getByRole('table')).toBeVisible()
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
    expect(overflow, route).toBe(false)
    await expect(page.getByLabel(/数据版本|Data release/)).toBeVisible()
  }
})

test('opens the versioned download catalog', async ({ page, request }) => {
  await page.goto('/downloads')
  await expect(page.getByRole('heading', { name: /数据发布与引用|Data releases and citation/ })).toBeVisible()
  const indexPath = `/downloads/${releaseId}/index.json`
  await expect(page.getByRole('link', { name: 'INDEX' })).toHaveAttribute('href', indexPath)
  const response = await request.get(indexPath)
  expect(response.ok()).toBe(true)
  const index = await response.json()
  expect(index.release_id).toBe(releaseId)
  expect(index.artifacts.length).toBeGreaterThan(0)
  await expect(page.getByText('canonical/entities.parquet', { exact: true })).toBeVisible()
  await expect(page.locator('.direct-download-row')).toHaveCount(Math.min(index.artifacts.length, 24))
  const sums = await request.get(`/downloads/${releaseId}/SHA256SUMS`)
  expect(sums.ok()).toBe(true)
  expect(await sums.text()).toMatch(/[0-9a-f]{64}  canonical\/entities\.parquet/)
})

test('filters registration uses and renders a local graph', async ({ page }) => {
  await page.goto('/explore?jurisdiction=AU')
  const country = page.getByLabel(/司法辖区|Jurisdiction/)
  await expect(country).toHaveValue('AU')
  await page.getByLabel(/任意字段|Any field/).fill('Frutor Fungicide')
  await page.getByLabel(/有效成分|Active ingredient/).fill('FENHEXAMID')
  await page.getByRole('button', { name: /应用筛选|Apply filters/ }).click()
  const product = page.getByRole('table').getByText('Frutor Fungicide', { exact: true })
  await expect(product).toBeVisible()
  await product.click()
  await expect(page.locator('.graph-canvas')).toBeVisible()
  await expect(page.locator('.graph-counts')).toContainText(/\d+ nodes/)
  await page.getByRole('button', { name: '2 hop' }).click()
  await expect(page.getByRole('button', { name: '2 hop' })).toHaveClass('is-active')
  await expect(page.locator('.graph-canvas')).toBeVisible()
})

test('searches entities, follows cursors, and exports filtered CSV', async ({ page }) => {
  await page.goto('/explore?jurisdiction=AU')
  const table = page.getByRole('table')
  await expect(table.locator('tbody tr')).toHaveCount(20)
  const loadMore = page.getByRole('button', { name: /加载更多|Load more/ })
  await expect(loadMore).toBeVisible()
  await loadMore.click()
  await expect(table.locator('tbody tr')).toHaveCount(40)

  await page.getByLabel(/司法辖区|Jurisdiction/).selectOption('AU')
  await page.getByLabel(/任意字段|Any field/).fill('Frutor Fungicide')
  await page.getByRole('button', { name: /应用筛选|Apply filters/ }).click()
  await expect(table.locator('tbody tr')).toHaveCount(1)
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /导出筛选 CSV|Export filtered CSV/ }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe(`registration-uses-${releaseId}.csv`)
  expect(await download.failure()).toBeNull()

  const search = page.getByLabel(/搜索实体|Search entities/)
  await search.fill('Frutor Fungicide')
  const result = page.getByRole('button', { name: /Frutor Fungicide/i }).first()
  await expect(result).toBeVisible()
  await result.click()
  await expect(page).toHaveURL(/\/entity\//)
  await expect(page.getByRole('heading', { name: 'Frutor Fungicide', exact: true })).toBeVisible()
})

test('switches to English and opens competency questions', async ({ page }) => {
  await page.goto('/')
  const menuButton = page.getByRole('button', { name: 'Open menu' })
  if (await menuButton.isVisible()) {
    await menuButton.click()
  }
  const englishButton = page.getByRole('button', { name: 'EN', exact: true })
  await englishButton.click()
  await expect(page.getByRole('link', { name: 'Compare' })).toBeVisible()
  await page.getByRole('link', { name: 'Compare' }).click()
  await expect(page.getByRole('heading', { name: 'Cross-country competency questions' })).toBeVisible()
  await expect(page.getByRole('table')).toBeVisible()
  await page.getByRole('tab', { name: /Q5/ }).click()
  await expect(page.getByRole('heading', { name: 'Country use profiles', exact: true })).toBeVisible()
  await expect(page.getByText(/Chart shows top \d+ of \d+; table shows first \d+\./)).toBeVisible()
  await expect(page.getByRole('table')).toBeVisible()
  await page.getByLabel('Jurisdiction').selectOption('AU')
  await expect(page.getByRole('table').locator('tbody tr').first()).toContainText('AU')
})

test('empty filters can be reset to populated results', async ({ page }) => {
  await page.goto('/explore?jurisdiction=AU')
  await expect(page.getByRole('table')).toBeVisible()
  await page.getByLabel(/任意字段|Any field/).fill('PESTKG-NONEXISTENT-PRODUCT-REGRESSION')
  await page.getByRole('button', { name: /应用筛选|Apply filters/ }).click()
  await expect(page.locator('.empty-table')).toBeVisible()
  await expect(page.getByRole('table')).toHaveCount(0)
  await page.getByRole('button', { name: /重置|Reset/ }).click()
  await expect(page.getByRole('table')).toBeVisible()
})

test('export rejection is visible without an unhandled runtime error', async ({ page }) => {
  test.info().annotations.push({ type: 'expected-http-status', description: '422' })
  await page.route('**/api/v1/exports/registration-uses', (route) => route.fulfill({
    status: 422,
    contentType: 'application/json',
    body: JSON.stringify({ error: { code: 'export_too_large', message: 'Export exceeds the synchronous row limit' } }),
  }))
  await page.goto('/explore?jurisdiction=AU')
  await expect(page.getByRole('table')).toBeVisible()
  const exportButton = page.getByRole('button', { name: /导出筛选 CSV|Export filtered CSV/ })
  await exportButton.click()
  await expect(page.getByRole('alert')).toHaveText('Export exceeds the synchronous row limit')
  await expect(exportButton).toBeEnabled()
})

test('graph request failure is visible instead of an empty graph', async ({ page }) => {
  test.info().annotations.push({ type: 'expected-http-status', description: '503' })
  await page.route('**/api/v1/graph/neighborhood?*', (route) => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ error: { code: 'dataset_unavailable', message: 'Graph is unavailable' } }),
  }))
  await page.goto('/explore?jurisdiction=AU')
  await expect(page.getByRole('table')).toBeVisible()
  await expect(page.locator('.graph-panel').getByRole('alert')).toHaveText('Graph is unavailable')
})
