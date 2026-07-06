import { expect, type Page, test } from '@playwright/test'
import { openWorkbench } from './helpers'

const topic = {
  id: 202,
  name: 'AI hardware cycle',
  description: 'mock topic',
  queries: ['AI hardware cycle'],
  status: 'active',
  created_at: '2026-06-21T00:00:00',
  article_count: 0,
  source_count: 0,
  enriched_count: 0,
  relevant_count: 0,
  latest_published_at: null,
}

const emptyLocalEvents = {
  events: [],
  framing: [],
  analysis_md: '',
  stance_evolution: [],
  keywords: [],
  entities: [],
  entity_groups: [],
  criteria: [],
}

const sentiment = {
  topic_id: 202,
  topic_name: 'AI hardware cycle',
  query: 'AI hardware cycle',
  queries: { reddit: 'AI hardware cycle', chinese: 'AI hardware cycle' },
  platform: 'multi',
  platforms: ['reddit', 'hackernews', 'bilibili', 'xiaohongshu', 'xueqiu'],
  warning: 'community samples are not facts',
  summary_md: '## Sentiment summary\nCommunity attention is rising.',
  timeline: [
    {
      time_bucket: '2026-06-20',
      platform: 'reddit',
      dominant_frame: 'supply anxiety',
      sentiment_label: 'anxious',
      sample_count: 2,
      confidence: 0.8,
      representative_posts: [
        {
          id: 'r1',
          platform: 'reddit',
          kind: 'post',
          subreddit: 'hardware',
          title: 'GPU shortage is back',
          author: 'reader',
          score: 120,
          num_comments: 44,
          url: 'https://reddit.com/r/hardware/comments/r1',
          created_utc: '2026-06-20T03:00:00',
          selftext_snippet: 'People are debating whether supply is actually tight.',
        },
      ],
    },
    {
      time_bucket: '2026-06-20',
      platform: 'hackernews',
      dominant_frame: 'capex debate',
      sentiment_label: 'skeptical',
      sample_count: 1,
      confidence: 0.45,
      representative_posts: [
        {
          id: 'h1',
          platform: 'hackernews',
          kind: 'post',
          subreddit: 'Hacker News',
          title: 'Accelerator demand keeps climbing',
          author: 'hnuser',
          score: 80,
          num_comments: 12,
          url: 'https://news.ycombinator.com/item?id=1',
          created_utc: '2026-06-20T05:00:00',
          selftext_snippet: 'HN is arguing about capex and bottlenecks.',
        },
      ],
    },
  ],
  errors: [
    { platform: 'xiaohongshu', error: 'browser unavailable' },
    { platform: 'xueqiu', error: 'login expired' },
  ],
  posts: [
    {
      id: 'r1',
      platform: 'reddit',
      kind: 'post',
      subreddit: 'hardware',
      title: 'GPU shortage is back',
      author: 'reader',
      score: 120,
      num_comments: 44,
      url: 'https://reddit.com/r/hardware/comments/r1',
      created_utc: '2026-06-20T03:00:00',
      selftext_snippet: 'People are debating whether supply is actually tight.',
    },
    {
      id: 'c1',
      platform: 'reddit',
      kind: 'comment',
      parent_post_id: 'r1',
      subreddit: 'hardware',
      title: 'Retail inventory is still uneven.',
      author: 'commenter',
      score: 18,
      num_comments: 0,
      url: 'https://reddit.com/r/hardware/comments/r1/c1',
      created_utc: '2026-06-20T04:00:00',
      selftext_snippet: 'Retail inventory is still uneven.',
    },
    {
      id: 'h1',
      platform: 'hackernews',
      kind: 'post',
      subreddit: 'Hacker News',
      title: 'Accelerator demand keeps climbing',
      author: 'hnuser',
      score: 80,
      num_comments: 12,
      url: 'https://news.ycombinator.com/item?id=1',
      created_utc: '2026-06-20T05:00:00',
      selftext_snippet: 'HN is arguing about capex and bottlenecks.',
    },
  ],
}

async function mockApi(page: Page) {
  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: [topic] })
  })
  await page.route('**/api/topics/202', async (route) => {
    await route.fulfill({ json: { ...topic, timeline: [], framing: [], analysis: null } })
  })
  await page.route('**/api/topics/202/articles**', async (route) => {
    await route.fulfill({ json: { total: 0, items: [] } })
  })
  await page.route('**/api/topics/202/local-events', async (route) => {
    await route.fulfill({ json: emptyLocalEvents })
  })
  await page.route('**/api/topics/202/sentiment', async (route) => {
    await route.fulfill({ json: sentiment })
  })
  await page.route('**/api/integrations/opencli/diagnostics', async (route) => {
    await route.fulfill({
      json: {
        configured_command: 'opencli',
        available: false,
        resolved_path: '',
        recommended_command: 'D:\\npm-global\\opencli.cmd',
        browser_required_platforms: ['reddit', 'bilibili', 'xiaohongshu', 'xueqiu'],
        message: "OpenCLI is not available at 'opencli'. Set OPENCLI_COMMAND to 'D:\\npm-global\\opencli.cmd'. Chrome 登录态不是当前阻塞点；请先让后端能启动 OpenCLI。",
      },
    })
  })
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('renders sentiment as scannable sample cards', async ({ page }) => {
  await openWorkbench(page)
  await page.getByLabel('专题视图导航').getByRole('button', { name: '民间情绪' }).click()

  await expect(page.locator('.sentiment-overview')).toContainText('2')
  await expect(page.locator('.sentiment-overview')).toContainText('2')
  await expect(page.locator('.sentiment-overview')).toContainText('1')
  const coverage = page.locator('.sentiment-platform-coverage')
  await expect(coverage).toContainText('平台覆盖')
  await expect(coverage.locator('.sentiment-platform-chip').filter({ hasText: 'Reddit' })).toContainText('有样本')
  await expect(coverage.locator('.sentiment-platform-chip').filter({ hasText: 'Hacker News' })).toContainText('有样本')
  await expect(coverage.locator('.sentiment-platform-chip').filter({ hasText: 'Hacker News' })).toContainText('公开 API')
  await expect(coverage.locator('.sentiment-platform-chip').filter({ hasText: 'B站' })).toContainText('已尝试无样本')
  await expect(coverage.locator('.sentiment-platform-chip').filter({ hasText: 'B站' })).toContainText('需 Chrome 登录态')
  await expect(coverage.locator('.sentiment-platform-chip').filter({ hasText: '小红书' })).toContainText('暂不可用')
  await expect(coverage.locator('.sentiment-platform-chip').filter({ hasText: '小红书' })).toContainText('需 Chrome 登录态')
  await expect(coverage.locator('.sentiment-platform-chip').filter({ hasText: '雪球' })).toContainText('暂不可用')
  await expect(coverage.locator('.sentiment-platform-chip').filter({ hasText: '雪球' })).toContainText('需 Chrome 登录态')
  await expect(page.locator('.sentiment-sample-card')).toHaveCount(2)
  await expect(page.locator('.sentiment-sample-card').first()).toContainText('GPU shortage is back')
  await expect(page.locator('.sentiment-sample-card').first()).toContainText('情绪样本，非事实来源')
  await expect(page.getByText('1 条高赞评论')).toBeVisible()
})

test('renders sentiment change timeline as platform-frame samples', async ({ page }) => {
  await openWorkbench(page)
  await page.getByLabel('专题视图导航').getByRole('button', { name: '民间情绪' }).click()

  const timeline = page.locator('.sentiment-timeline')
  await expect(timeline).toContainText('舆论变化时间线')
  await expect(timeline.locator('.sentiment-timeline-item')).toHaveCount(2)
  await expect(timeline.locator('.sentiment-timeline-item').first()).toContainText('Reddit')
  await expect(timeline.locator('.sentiment-timeline-item').first()).toContainText('supply anxiety')
  await expect(timeline.locator('.sentiment-timeline-item').first()).toContainText('anxious')
  await expect(timeline.locator('.sentiment-timeline-item').first()).toContainText('2 条样本')
  await expect(timeline.locator('.sentiment-timeline-item').first()).toContainText('代表样本')
  await expect(timeline.locator('.sentiment-timeline-item').first()).toContainText('GPU shortage is back')
  await expect(timeline.locator('.sentiment-timeline-item').nth(1)).toContainText('小样本线索')
  await expect(timeline).toContainText('样本趋势，非事实时间线')
})

test('shows actionable OpenCLI diagnostics in the sentiment panel', async ({ page }) => {
  await openWorkbench(page)
  await page.getByLabel('专题视图导航').getByRole('button', { name: '民间情绪' }).click()

  const diagnostics = page.locator('.opencli-diagnostics')
  await expect(diagnostics).toContainText('OpenCLI 未连接')
  await expect(diagnostics).toContainText('当前命令：opencli')
  await expect(diagnostics).toContainText('建议设置：D:\\npm-global\\opencli.cmd')
  await expect(diagnostics).toContainText('Chrome 已登录仍报错时，先修 OPENCLI_COMMAND')
})
