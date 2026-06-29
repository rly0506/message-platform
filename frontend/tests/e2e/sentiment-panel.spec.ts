import { expect, type Page, test } from '@playwright/test'

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
  platforms: ['reddit', 'hackernews'],
  warning: 'community samples are not facts',
  summary_md: '## Sentiment summary\nCommunity attention is rising.',
  errors: [{ platform: 'xiaohongshu', error: 'browser unavailable' }],
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
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('renders sentiment as scannable sample cards', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('专题视图导航').getByRole('button', { name: '民间情绪' }).click()

  await expect(page.locator('.sentiment-overview')).toContainText('2')
  await expect(page.locator('.sentiment-overview')).toContainText('2')
  await expect(page.locator('.sentiment-overview')).toContainText('1')
  await expect(page.locator('.sentiment-sample-card')).toHaveCount(2)
  await expect(page.locator('.sentiment-sample-card').first()).toContainText('GPU shortage is back')
  await expect(page.locator('.sentiment-sample-card').first()).toContainText('情绪样本，非事实来源')
  await expect(page.getByText('1 条高赞评论')).toBeVisible()
})
