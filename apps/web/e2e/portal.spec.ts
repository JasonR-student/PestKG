import { expect, test, type Page } from '@playwright/test'

const browserErrors = new WeakMap<Page, string[]>()

test.beforeEach(async ({ page }) => {
  const errors: string[] = []
  browserErrors.set(page, errors)
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
})

test.afterEach(async ({ page }) => {
  expect(browserErrors.get(page) ?? []).toEqual([])
})

test('overview map opens a filtered exploration flow', async ({ page }) => {
  const overviewRequest = page.waitForRequest((request) => request.url().includes('/api/v1/stats/overview'))
  await page.goto('/')
  const request = await overviewRequest
  expect(request.headers()['x-pestkg-release']).toBe('2026.08.3_federated')
  await expect(page).toHaveURL(/release=2026\.08\.3_federated/)
  await expect(page.getByLabel(/数据版本|Data release/)).toHaveValue('2026.08.3_federated')
  await expect(page).toHaveTitle(/PestKG|Pesticide/i)
  await expect(page.getByRole('heading', { name: /多国农药登记知识图谱|Multicountry pesticide/ })).toBeVisible()
  await expect(page.getByText('1.2M', { exact: false }).first()).toBeVisible()
  await expect(page.getByText(/暂未公开发布|Distribution blocked/)).toBeVisible()

  await page.getByRole('button', { name: /Australia: .* nodes/ }).click()
  await expect(page).toHaveURL(/\/explore\?.*jurisdiction=AU/)
  await expect(page).toHaveURL(/release=2026\.08\.3_federated/)
  await expect(page.getByRole('heading', { name: /登记使用数据探索|Registration-use explorer/ })).toBeVisible()
  await expect(page.getByRole('table')).toBeVisible()
})

test('mobile workspace has no horizontal page overflow', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.startsWith('mobile'))
  await page.goto('/explore?jurisdiction=AU')
  await expect(page.getByRole('heading', { name: /登记使用数据探索|Registration-use explorer/ })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  expect(overflow).toBe(false)
  await expect(page.getByLabel(/数据版本|Data release/)).toBeVisible()
})

test('opens the versioned download catalog', async ({ page }) => {
  await page.goto('/downloads')
  await expect(page.getByRole('heading', { name: /数据发布与引用|Data releases and citation/ })).toBeVisible()
  const indexLink = page.getByRole('link', { name: 'INDEX' })
  await expect(indexLink).toHaveAttribute('href', /\/downloads\/2026\.08\.3_federated\/index\.json/)
  await expect(page.getByText(/pestkg-sample\.jsonld/)).toBeVisible()
  await expect(page.getByText(/当前目录提供 6 个带校验值的文件|6 checksummed files/)).toBeVisible()
})

test('filters registration uses and renders a local graph', async ({ page }) => {
  await page.goto('/explore?jurisdiction=AU')
  const country = page.getByLabel(/司法辖区|Jurisdiction/)
  await expect(country).toHaveValue('AU')
  await page.getByLabel(/有效成分|Active ingredient/).fill('GLYPHOSATE')
  await page.getByRole('button', { name: /应用筛选|Apply filters/ }).click()
  await expect(page.getByText(/Fortin Herbicide/i)).toBeVisible()
  await page.getByText(/Fortin Herbicide/i).click()
  await expect(page.locator('.graph-canvas')).toBeVisible()
})

test('searches entities, follows cursors, and exports filtered CSV', async ({ page }) => {
  await page.goto('/explore')
  const table = page.getByRole('table')
  const initialRows = await table.getByRole('row').count()
  const loadMore = page.getByRole('button', { name: /加载更多|Load more/ })
  await expect(loadMore).toBeVisible()
  await loadMore.click()
  await expect.poll(() => table.getByRole('row').count()).toBeGreaterThan(initialRows)

  await page.getByLabel(/司法辖区|Jurisdiction/).selectOption('AU')
  await page.getByLabel(/有效成分|Active ingredient/).fill('GLYPHOSATE')
  await page.getByRole('button', { name: /应用筛选|Apply filters/ }).click()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /导出筛选 CSV|Export filtered CSV/ }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('registration-uses-2026.08.3_federated.csv')

  const search = page.getByLabel(/搜索实体|Search entities/)
  await search.fill('Fortin')
  const result = page.getByRole('button', { name: /Fortin Herbicide/i }).first()
  await expect(result).toBeVisible()
  await result.click()
  await expect(page).toHaveURL(/\/entity\//)
  await expect(page.getByRole('heading', { name: /Fortin Herbicide/i })).toBeVisible()
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
  await page.getByRole('tab', { name: /Q5/ }).click()
  await expect(page.getByText(/Country use profiles/)).toBeVisible()
  await expect(page.getByText('Chart shows top 12 of 200; table shows first 100.')).toBeVisible()
  await expect(page.getByRole('table')).toBeVisible()
})
