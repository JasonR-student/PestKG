import { expect, test } from '@playwright/test'

test('first visit defaults to English regardless of browser locale', async ({ page }) => {
  await page.goto('/graph')
  await expect(page.getByRole('heading', { name: 'Graph browser', exact: true })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page).toHaveTitle('PestKG | Cross-Jurisdiction Pesticide Knowledge Graph')
  await expect(page.getByLabel('Graph scope', { exact: true })).toHaveValue('jurisdiction:AU')
})

test('manual language choices persist and update the document language', async ({ page }) => {
  await page.goto('/')
  const menu = page.getByRole('button', { name: 'Open menu', exact: true })
  if (await menu.isVisible()) await menu.click()
  await page.getByRole('button', { name: '中', exact: true }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN')
  await page.reload()
  await expect(page.getByRole('heading', { name: '多辖区农药登记知识图谱', exact: true })).toBeVisible()
  await expect(page).toHaveTitle('PestKG | 多辖区农药知识图谱')
  if (await menu.isVisible()) await menu.click()
  await page.getByRole('button', { name: 'EN', exact: true }).click()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Cross-jurisdiction pesticide registration knowledge graph', exact: true })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
})
