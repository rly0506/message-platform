import { expect, type Page, test } from '@playwright/test'

let savedMark: Record<string, unknown> | null = null

const seeds = [
  {
    title: 'New nuclear battery moves from lab to pilot',
    url: 'https://example.com/energy-seed',
    domain: 'science',
    domain_label: '科学',
    signal: 88,
    delta: 32,
    is_new: true,
    what: '小型核能储能进入试点',
    why: '能源领域是你的陌生区，适合放入认知边界队列',
    still_niche: true,
  },
  {
    title: 'GPU cluster financing shifts to private credit',
    url: 'https://example.com/ai-finance-seed',
    domain: 'finance',
    domain_label: '财经',
    signal: 65,
    delta: 12,
    is_new: false,
    what: '算力中心融资方式变化',
    why: '连接你的金融背景和 AI 机制缺口',
    still_niche: true,
  },
]

async function mockDiscoveryApi(page: Page) {
  savedMark = null
  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/discovery/latest', async (route) => {
    await route.fulfill({
      json: {
        markdown: '## 今日前沿\n\n两条值得追踪的种子。',
        run_id: '20260629T040000Z',
        seeds,
      },
    })
  })
  await page.route('**/api/cognition/profile', async (route) => {
    await route.fulfill({
      json: [
        {
          id: 1,
          domain_key: 'energy',
          domain_label: '能源 / 核能 / 新能源',
          level: 'unfamiliar',
          note: '只在身边新闻中听说，没有主动了解。',
          updated_at: '2026-06-29T00:00:00',
        },
        {
          id: 2,
          domain_key: 'ai_infra',
          domain_label: 'AI / 算力基础设施',
          level: 'partial',
          note: '知晓 CPU、GPU、CPO、算力中心、大模型等词，但不懂具体机制与实现。',
          updated_at: '2026-06-29T00:00:00',
        },
        {
          id: 3,
          domain_key: 'finance',
          domain_label: '金融 / 经济 / 公司财务',
          level: 'strong_partial',
          note: '课程基础较强。',
          updated_at: '2026-06-29T00:00:00',
        },
      ],
    })
  })
  await page.route('**/api/cognition/marks?**', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/cognition/marks/summary', async (route) => {
    await route.fulfill({ json: { counts: {}, recent: [], unfamiliar_topics: [] } })
  })
  await page.route('**/api/cognition/marks', async (route) => {
    savedMark = route.request().postDataJSON()
    await route.fulfill({
      json: {
        id: 9,
        target_type: savedMark?.target_type,
        target_id: savedMark?.target_id,
        target_key: savedMark?.target_key,
        topic_id: null,
        label: savedMark?.label,
        note: savedMark?.note,
        updated_at: '2026-06-29T05:00:00',
      },
    })
  })
}

test.beforeEach(async ({ page }) => {
  await mockDiscoveryApi(page)
})

test('marks a frontier seed as known from the cognition boundary queue and closes it', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '今日情报台' }).click()

  // 队列初始 2 条, 显示推荐理由(不再显示 🔥 热度数字)。
  await expect(page.locator('.boundary-queue').getByText('认知边界队列（2）')).toBeVisible()
  await expect(page.locator('.boundary-queue')).toContainText('边界外')
  await expect(page.locator('.boundary-queue')).toContainText('机制缺口')
  await expect(page.locator('.seed-stream').getByText('🔥', { exact: false })).toHaveCount(0)

  // 在队列里一键「我懂了」: 复用 seed mark 的 known。
  const queueItem = page.locator('.boundary-list li').filter({ hasText: 'New nuclear battery' })
  await queueItem.getByRole('button', { name: '我懂了' }).click()

  // 闭环可见: 点完后该条从队列消失, 计数降为 1。(先等 UI 闭环, 再断言 POST 内容, 避免竞态)
  await expect(page.locator('.boundary-queue').getByText('认知边界队列（1）')).toBeVisible()
  await expect(page.locator('.boundary-list li').filter({ hasText: 'New nuclear battery' })).toHaveCount(0)

  await expect.poll(() => savedMark).toMatchObject({
    target_type: 'seed',
    target_id: 0,
    target_key: 'https://example.com/energy-seed',
    label: 'known',
  })
})
