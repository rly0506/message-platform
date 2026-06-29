import { expect, type Page, test } from '@playwright/test'

const topic = {
  id: 101,
  name: '美伊战争',
  description: 'mock topic',
  queries: ['美伊战争', 'US Iran war'],
  status: 'active',
  created_at: '2026-06-21T00:00:00',
  article_count: 6,
  source_count: 4,
  enriched_count: 0,
  relevant_count: 6,
  latest_published_at: '2026-06-20T08:00:00',
}

const localEvents = {
  events: [
    {
      date: '2026-06-20',
      title_zh: '美国与伊朗冲突进入关键节点',
      summary_zh: '多个来源集中报道这一节点。',
      article_ids: [1, 2, 3, 4],
      score: 0.72,
      importance_label: '高',
      coverage_label: '多源覆盖',
      selection_basis: ['4 个来源、6 篇报道', '权威来源：Reuters'],
      source_count: 4,
      article_count: 6,
      sources: [
        { name: 'Reuters', count: 3, tier: 'wire', tier_label: '通讯社' },
        { name: 'BBC', count: 1, tier: 'mainstream', tier_label: '主流媒体' },
      ],
      source_matrix: [
        {
          source: 'Reuters',
          tier: 'wire',
          tier_label: '通讯社',
          article_count: 3,
          first_published_at: '2026-06-20T01:00:00',
          latest_published_at: '2026-06-20T05:00:00',
          dominant_stance: '冲突/安全',
          stance_counts: { '冲突/安全': 3 },
          dominant_category: '触发事件',
          category_counts: { 触发事件: 3 },
          representative_title: 'Reuters reports US-Iran strike risk',
          article_ids: [1, 2, 3],
        },
        {
          source: 'Financial Times',
          tier: 'professional',
          tier_label: '专业媒体',
          article_count: 2,
          first_published_at: '2026-06-20T02:00:00',
          latest_published_at: '2026-06-20T06:00:00',
          dominant_stance: '影响/后果',
          stance_counts: { '影响/后果': 2 },
          dominant_category: '影响后果',
          category_counts: { 影响后果: 2 },
          representative_title: 'Oil markets react to US-Iran conflict',
          article_ids: [4, 5],
        },
        {
          source: 'BBC',
          tier: 'mainstream',
          tier_label: '主流媒体',
          article_count: 1,
          first_published_at: '2026-06-20T03:00:00',
          latest_published_at: '2026-06-20T03:00:00',
          dominant_stance: '中性观察',
          stance_counts: { '中性观察': 1 },
          dominant_category: '外交降温',
          category_counts: { 外交降温: 1 },
          representative_title: 'BBC explains the latest diplomacy',
          article_ids: [6],
        },
      ],
      source_tiers: [
        { key: 'wire', label: '通讯社', count: 3 },
        { key: 'professional', label: '专业媒体', count: 2 },
        { key: 'mainstream', label: '主流媒体', count: 1 },
      ],
      category: '行动进展',
      category_reason: '命中阶段词：strike',
      stance: '冲突/安全',
      score_breakdown: {
        authority: { label: '权威来源', value: 0.8, weight: 0.22, reason: '命中来源：Reuters' },
        pickup: { label: '扩散/引用代理', value: 0.7, weight: 0.25, reason: '4 个来源、6 篇报道' },
      },
      evidence: {
        authority_sources: ['Reuters'],
        source_count: 4,
        article_count: 6,
        impact_terms: ['战争'],
        date_span_days: 1,
        first_sources: [],
        source_tiers: [],
      },
      keywords: [],
      entities: [],
      location_signals: [{ term: '伊朗', count: 2, weight: 0.7, kind: 'place', kind_label: '地点' }],
      evidence_articles: [],
    },
  ],
  framing: [
    {
      id: 1,
      party: '冲突/安全',
      stance: '基本稳定',
      summary_zh: '多家媒体集中讨论冲突升级风险。',
      article_ids: [1, 2],
    },
    {
      id: 2,
      party: '影响/后果',
      stance: '近期增强',
      summary_zh: '金融媒体关注油价与市场影响。',
      article_ids: [2],
    },
  ],
  analysis_md: '本地规则分析',
  stance_evolution: [
    {
      period: '2026-06',
      dominant_stance: '冲突/安全',
      counts: { '冲突/安全': 2, '影响/后果': 1 },
      article_ids: [1, 2, 3],
    },
  ],
  keywords: [],
  entities: [
    { term: '伊朗', count: 3, weight: 0.8, kind: 'place', kind_label: '地点' },
    { term: '白宫', count: 2, weight: 0.6, kind: 'organization', kind_label: '组织' },
  ],
  entity_groups: [
    {
      kind: 'place',
      label: '地点',
      items: [{ term: '伊朗', count: 3, weight: 0.8, kind: 'place', kind_label: '地点' }],
    },
    {
      kind: 'organization',
      label: '组织',
      items: [{ term: '白宫', count: 2, weight: 0.6, kind: 'organization', kind_label: '组织' }],
    },
  ],
  criteria: [
    { key: 'authority', label: '权威来源', description: '是否由权威来源报道。', weight: 0.22 },
  ],
  narrative_signals: [
    {
      claim: 'ai capex boom',
      source_count: 3,
      article_count: 3,
      first_seen: '2026-06-01T00:00:00',
      last_seen: '2026-06-03T00:00:00',
      sources: ['Reuters', 'Financial Times', 'Bloomberg'],
      article_ids: [1, 2, 3],
      representative_titles: ['AI capex boom reshapes market'],
    },
  ],
}

const articles = {
  total: 3,
  items: [
    {
      id: 1,
      url: 'https://example.com/1',
      title: 'Reuters reports US-Iran strike risk',
      title_zh: '',
      source: 'Reuters',
      source_lang: 'en',
      source_country: '',
      published_at: '2026-06-20T01:00:00',
      snippet: 'strike risk',
      snippet_zh: '',
      collector: 'gnews',
      enriched: false,
      relevance: 0.9,
      relevant: true,
      substance_score: 82,
      substance_note: 'specific numbers and timing',
      stance: '冲突/安全',
      stance_summary: '',
      category: '触发事件',
      category_reason: '命中阶段词：strike',
    },
    {
      id: 2,
      url: 'https://example.com/2',
      title: 'Oil markets react to US-Iran conflict',
      title_zh: '',
      source: 'Financial Times',
      source_lang: 'en',
      source_country: '',
      published_at: '2026-06-20T02:00:00',
      snippet: 'oil market impact',
      snippet_zh: '',
      collector: 'gnews',
      enriched: false,
      relevance: 0.8,
      relevant: true,
      substance_score: 45,
      substance_note: 'some checkable detail',
      stance: '影响/后果',
      stance_summary: '',
      category: '影响后果',
      category_reason: '命中阶段词：impact',
    },
    {
      id: 3,
      url: 'https://example.com/3',
      title: 'BBC explains the latest diplomacy',
      title_zh: '',
      source: 'BBC',
      source_lang: 'en',
      source_country: '',
      published_at: '2026-06-20T03:00:00',
      snippet: 'talks and diplomacy',
      snippet_zh: '',
      collector: 'gnews',
      enriched: false,
      relevance: 0.7,
      relevant: true,
      stance: '中性观察',
      stance_summary: '',
      category: '外交降温',
      category_reason: '命中阶段词：diplomacy',
    },
  ],
}

async function mockApi(page: Page) {
  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: [topic] })
  })
  await page.route('**/api/topics/101', async (route) => {
    await route.fulfill({ json: { ...topic, timeline: [], framing: [], analysis: null } })
  })
  await page.route('**/api/topics/101/articles**', async (route) => {
    await route.fulfill({ json: articles })
  })
  await page.route('**/api/topics/101/articles/1/perspective', async (route) => {
    await route.fulfill({
      json: {
        article_id: 1,
        mode: 'summary',
        items: [
          { sentence: 'strike risk', kind: 'substance', reason: 'checkable claim' },
          { sentence: 'market panic is everywhere', kind: 'emotion', reason: 'loaded wording' },
        ],
        error: '',
        source_error: 'fetch failed',
      },
    })
  })
  await page.route('**/api/topics/101/local-events', async (route) => {
    await route.fulfill({ json: localEvents })
  })
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('filters and sorts the event source matrix', async ({ page }) => {
  await page.goto('/')

  await expect(page.locator('.source-matrix').getByText('来源矩阵')).toBeVisible()
  await expect(page.getByText('显示 3 / 3 个来源')).toBeVisible()

  await page.getByLabel('来源层级筛选').selectOption('wire')
  await expect(page.getByText('显示 1 / 3 个来源')).toBeVisible()
  await expect(page.locator('.source-matrix-table').getByText('Reuters reports US-Iran strike risk')).toBeVisible()
  await expect(page.locator('.source-matrix-table').getByText('Oil markets react to US-Iran conflict')).toBeHidden()

  await page.getByRole('button', { name: '权威来源' }).click()
  await expect(page.getByText('显示 3 / 3 个来源')).toBeVisible()

  await page.getByLabel('来源层级筛选').selectOption('all')
  await page.getByLabel('来源矩阵排序').selectOption('count')

  const sourceNames = await page.locator('.source-matrix-table article strong').allTextContents()
  expect(sourceNames.slice(0, 3)).toEqual(['Reuters', 'Financial Times', 'BBC'])
})

test('groups original articles by report category', async ({ page }) => {
  await page.goto('/')

  await page.locator('details.article-feed-collapse > summary').click()
  await expect(page.locator('details.article-feed-collapse > summary')).toContainText('2/3')
  await expect(page.locator('.substance-summary')).toContainText('1')
  await expect(page.locator('.article-group').filter({ hasText: '触发事件' })).toBeVisible()
  await expect(page.locator('.article-group').filter({ hasText: '影响后果' })).toBeVisible()

  await page.locator('.article-row').filter({ hasText: 'Reuters reports US-Iran strike risk' }).getByRole('button', { name: '透视' }).click()
  await expect(page.locator('.article-perspective')).toContainText('摘要透视')
  await expect(page.locator('.article-perspective')).toContainText('strike risk')
  await expect(page.locator('.article-perspective')).toContainText('market panic is everywhere')

  await page.getByLabel('报道功能分类筛选').selectOption('影响后果')
  const articleGroups = page.locator('.article-group')
  await expect(articleGroups.getByRole('link', { name: 'Oil markets react to US-Iran conflict' })).toBeVisible()
  await expect(articleGroups.getByRole('link', { name: 'Reuters reports US-Iran strike risk' })).toBeHidden()
})

test('renders source matrix controls on mobile without horizontal overflow', async ({ page }) => {
  await page.goto('/')

  await expect(page.locator('.source-matrix').getByText('来源矩阵')).toBeVisible()
  await expect(page.locator('.source-matrix-tools')).toBeVisible()

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2)
  expect(overflow).toBe(false)
})

test('keeps secondary media panels collapsed with count summaries by default', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '事件发展轴' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '美国与伊朗冲突进入关键节点' })).toBeVisible()

  const collapsedPanels = [
    {
      name: /关键节点判定标准.*1 项/,
      hiddenText: '是否由权威来源报道。',
    },
    {
      name: /各方态度.*2 方/,
      hiddenText: '金融媒体关注油价与市场影响。',
    },
    {
      name: /原始报道流.*3 篇/,
      hiddenText: 'oil market impact',
    },
    {
      name: /关键人物\/组织.*2 个/,
      hiddenText: '白宫',
    },
    {
      name: /态度随时间变化.*1 期/,
      hiddenText: '2026-06',
    },
    {
      name: /叙事趋同信号.*1 条/,
      hiddenText: 'Reuters、Financial Times、Bloomberg',
    },
  ]

  for (const panel of collapsedPanels) {
    const toggle = page.locator('details.media-collapse > summary').filter({ hasText: panel.name })
    await expect(toggle).toBeVisible()
    await expect(page.getByText(panel.hiddenText)).toBeHidden()
    await toggle.click()
    await expect(page.getByText(panel.hiddenText)).toBeVisible()
  }
})
