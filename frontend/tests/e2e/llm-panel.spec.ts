import { expect, type Page, test } from '@playwright/test'

const topic = {
  id: 404,
  name: 'No LLM boundary',
  description: 'mock topic',
  queries: ['No LLM boundary'],
  status: 'active',
  created_at: '2026-07-02T00:00:00',
  article_count: 2,
  source_count: 2,
  enriched_count: 0,
  relevant_count: 2,
  latest_published_at: '2026-07-02T01:00:00',
}

const localEvents = {
  events: [],
  framing: [],
  analysis_md: '本地规则已经根据标题、摘要、来源和时间生成基础判断。',
  stance_evolution: [],
  keywords: [],
  entities: [],
  entity_groups: [],
  criteria: [],
}

async function mockApi(page: Page) {
  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: [topic] })
  })
  await page.route('**/api/topics/404', async (route) => {
    await route.fulfill({ json: { ...topic, timeline: [], framing: [], analysis: null } })
  })
  await page.route('**/api/topics/404/articles**', async (route) => {
    await route.fulfill({ json: { total: 0, items: [] } })
  })
  await page.route('**/api/topics/404/local-events', async (route) => {
    await route.fulfill({ json: localEvents })
  })
  await page.route('**/api/cognition/marks?**', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/cognition/marks/summary', async (route) => {
    await route.fulfill({ json: { counts: {}, recent: [], unfamiliar_topics: [] } })
  })
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('explains local capability boundaries before LLM analysis exists', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('专题视图导航').getByRole('button', { name: 'LLM 深度分析' }).click()

  const note = page.locator('.local-capability-note')
  await expect(note).toContainText('本地可用')
  await expect(note).toContainText('LLM 增强')
  await expect(note).toContainText('边界提醒')
  await expect(note).toContainText('采集、去重、时间线、来源矩阵')
  await expect(note).toContainText('深度分析、单篇富化、前沿综述')
  await expect(note).toContainText('不等同于全文事实核查')

  await expect(page.locator('.llm-analysis-body')).toContainText('本地规则已经根据标题、摘要、来源和时间生成基础判断。')
})
