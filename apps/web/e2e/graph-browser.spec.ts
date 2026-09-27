import { expect, test, type Page } from '@playwright/test'
import path from 'node:path'
import type { GraphData } from '../src/shared/api/models'

const errors = new WeakMap<Page, string[]>()

test.beforeEach(async ({ page }, info) => {
  await page.addInitScript(() => localStorage.setItem('pestkg-language', 'zh'))
  if (info.project.name.startsWith('desktop')) await page.setViewportSize({ width: 1440, height: 1000 })
  const messages: string[] = []
  errors.set(page, messages)
  page.on('pageerror', (error) => messages.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') messages.push(message.text()) })
})

test.afterEach(async ({ page }, info) => {
  const expected = info.annotations.some((item) => item.type === 'expected-503')
  expect((errors.get(page) ?? []).filter((message) =>
    !(expected && message.startsWith('Failed to load resource: the server responded with a status of 503')),
  )).toEqual([])
})

async function queryResult(page: Page, action: () => Promise<unknown>): Promise<GraphData> {
  const response = page.waitForResponse((item) => item.url().includes('/api/v1/graph/query') && item.request().method() === 'POST')
  await action()
  const result = await response
  expect(result.ok()).toBe(true)
  return (await result.json()).data
}

async function populated(page: Page) {
  await expect(page.locator('.graph-canvas')).toBeVisible()
  await expect.poll(() => page.locator('.graph-canvas').evaluate((element) => {
    let colored = 0
    for (const canvas of element.querySelectorAll('canvas')) {
      const context = canvas.getContext('2d')
      if (!context || !canvas.width || !canvas.height) continue
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data
      for (let index = 0; index < pixels.length; index += 64) {
        if (pixels[index + 3] > 0 && Math.max(pixels[index], pixels[index + 1], pixels[index + 2]) - Math.min(pixels[index], pixels[index + 1], pixels[index + 2]) > 20) colored++
      }
    }
    return colored
  })).toBeGreaterThan(30)
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
}

async function screenshot(page: Page, name: string, project: string) {
  if (process.env.PESTKG_VISUAL_DIR) {
    await page.screenshot({ path: path.join(process.env.PESTKG_VISUAL_DIR, `${name}-${project}.png`), fullPage: true })
  }
}

test('APVMA business graph, provenance projection, inspector and PNG work', async ({ page }, info) => {
  await page.goto('/graph?scope=source:apvma_pubcris')
  await expect(page.getByRole('heading', { name: '图谱浏览器' })).toBeVisible()
  await expect(page.getByLabel('图谱范围')).toHaveValue('source:apvma_pubcris')
  await populated(page)
  await screenshot(page, 'graph-apvma', info.project.name)

  await page.getByLabel('图谱查询').fill('Frutor Fungicide')
  const graph = await queryResult(page, () => page.getByRole('button', { name: '搜索', exact: true }).click())
  expect(graph.nodes.length).toBeGreaterThan(2)
  expect(graph.edges.some((edge) => edge.predicate === 'FROM_SNAPSHOT' && edge.properties?.stored_fact === false)).toBe(true)
  await populated(page)
  const catalogToggle = page.getByRole('button', { name: '标签与关系', exact: true })
  if (await catalogToggle.isVisible()) await catalogToggle.click()
  await page.locator('.graph-loaded-nodes summary').click()
  await page.locator('.graph-loaded-nodes').getByRole('button', { name: 'Frutor Fungicide', exact: true }).click()
  await expect(page.locator('.graph-inspector h2')).toHaveText('Frutor Fungicide')
  await page.getByRole('button', { name: '固定节点', exact: true }).click()
  await expect(page.getByRole('button', { name: '固定节点', exact: true })).toHaveAttribute('aria-pressed', 'true')
  const expansion = page.waitForResponse((item) => item.url().includes('/api/v1/graph/expand'))
  await page.getByRole('button', { name: '展开邻居', exact: true }).click()
  expect((await expansion).ok()).toBe(true)
  await expect(page.getByRole('button', { name: '展开邻居', exact: true })).toBeEnabled()
  await populated(page)
  await screenshot(page, 'graph-apvma-inspector', info.project.name)

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: '导出 PNG', exact: true }).click()
  const png = await download
  expect(png.suggestedFilename()).toBe('PestKG-source-apvma_pubcris.png')
  expect(await png.failure()).toBeNull()
  await page.getByRole('button', { name: '从视图移除', exact: true }).click()
  await expect(page.locator('.graph-inspector')).toContainText('暂无选中项')
  await expect(page.locator('.graph-loaded-nodes').getByRole('button', { name: 'Frutor Fungicide', exact: true })).toHaveCount(0)
  const without = await queryResult(page, () => page.getByLabel('溯源属性投影').uncheck())
  expect(without.nodes.length).toBeGreaterThan(0)
  expect(without.edges.some((edge) => edge.predicate === 'FROM_SNAPSHOT')).toBe(false)
})

test('Taiwan region and independent ChEBI and AGROVOC graphs remain separate', async ({ page }, info) => {
  await page.goto('/graph?scope=jurisdiction:TW')
  await expect(page.getByLabel('图谱范围')).toHaveValue('jurisdiction:TW')
  await expect(page.getByLabel('图谱范围').locator('option:checked')).toHaveText('TW · 台湾地区')
  await populated(page)
  for (const [scope, term] of [['reference:CHEBI', 'glyphosate'], ['reference:AGROVOC', 'cucumbers']]) {
    await queryResult(page, () => page.getByLabel('图谱范围').selectOption(scope))
    await populated(page)
    await page.getByLabel('图谱查询').fill(term)
    const graph = await queryResult(page, () => page.getByRole('button', { name: '搜索', exact: true }).click())
    expect(graph.nodes.length).toBeGreaterThan(0)
    expect(graph.nodes.every((node) => node.id.startsWith('REF_'))).toBe(true)
    expect(graph.edges.some((edge) => edge.predicate === 'EXACT_CHEMICAL_IDENTITY')).toBe(false)
    await populated(page)
    await expect(page.locator('.graph-scope-status')).toContainText('已审核监管身份连接：0')
    await screenshot(page, scope.slice(10).toLowerCase(), info.project.name)
  }
})

test('graph browser empty queries can be reset', async ({ page }) => {
  await page.goto('/graph')
  await populated(page)
  await page.getByLabel('图谱查询').fill('PESTKG-NONEXISTENT-GRAPH-REGRESSION')
  const graph = await queryResult(page, () => page.getByRole('button', { name: '搜索', exact: true }).click())
  expect(graph.nodes).toEqual([])
  await expect(page.locator('.graph-no-results')).toHaveText('没有符合条件的节点')
  await expect(page.getByRole('button', { name: '导出 PNG', exact: true })).toBeDisabled()
  await page.getByLabel('图谱查询').fill('Frutor Fungicide')
  await queryResult(page, () => page.getByRole('button', { name: '搜索', exact: true }).click())
  await populated(page)
})

test('graph browser request failure is visible', async ({ page }) => {
  test.info().annotations.push({ type: 'expected-503' })
  await page.route('**/api/v1/graph/query', (route) => route.fulfill({
    status: 503, contentType: 'application/json',
    body: JSON.stringify({ error: { code: 'graph_unavailable', message: 'Graph browser is unavailable' } }),
  }))
  await page.goto('/graph')
  await expect(page.getByRole('alert')).toHaveText('Graph browser is unavailable')
})
