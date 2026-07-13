import { expect, type Page } from '@playwright/test'

export async function openWorkbench(page: Page) {
  const topicsResponse = page.waitForResponse((response) => {
    const url = new URL(response.url())
    return response.request().method() === 'GET' && url.pathname === '/api/topics'
  })
  await page.goto('/')
  await topicsResponse
  await switchToWorkbench(page)
}

export async function switchToWorkbench(page: Page) {
  await page.getByRole('button', { name: '事件分析台' }).click()
  await expect(page.locator('h1')).toHaveText('事件搜索与发展时间轴')
  // 工作台默认不预选专题，调用本 helper 的用例必须提供至少一个专题；
  // 空状态测试应直接导航，不应调用这个自动选题 helper。
  await selectFirstTopic(page)
}

export async function selectFirstTopic(page: Page) {
  const select = page.locator('select.topic-select')
  // 专题列表是 onMounted 异步加载的，先等第一个非禁用选项出现（占位项 disabled，真专题在其后）。
  const firstTopic = select.locator('option:not([disabled])').first()
  await firstTopic.waitFor({ state: 'attached', timeout: 10_000 })
  // index 0 = 禁用占位「选择已有专题…」，index 1 = 第一个专题；按 index 选，Vue 回读数字 value。
  await select.selectOption({ index: 1 })
}
