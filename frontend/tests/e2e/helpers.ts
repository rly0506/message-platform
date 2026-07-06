import { expect, type Page } from '@playwright/test'

export async function openWorkbench(page: Page) {
  await page.goto('/')
  await switchToWorkbench(page)
}

export async function switchToWorkbench(page: Page) {
  await page.getByRole('button', { name: '事件分析台' }).click()
  await expect(page.locator('h1')).toHaveText('事件搜索与发展时间轴')
}
