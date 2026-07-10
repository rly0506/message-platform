import { expect, type Page, test } from '@playwright/test'
import { openWorkbench, switchToWorkbench } from './helpers'

let startedJobs: string[] = []
let searchPayloads: Array<{ query: string }> = []
let autoRefreshRuns = 0

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
  startedJobs = []
  searchPayloads = []
  autoRefreshRuns = 0
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
  await page.route('**/api/cognition/marks?**', async (route) => {
    await route.fulfill({
      json: [
        {
          id: 7,
          target_type: 'article',
          target_id: 1,
          topic_id: 101,
          label: 'doubtful',
          updated_at: '2026-06-20T09:00:00',
        },
      ],
    })
  })
  await page.route('**/api/cognition/marks/summary', async (route) => {
    await route.fulfill({
      json: {
        counts: { doubtful: 1, unexpected: 1 },
        recent: [
          {
            id: 7,
            target_type: 'article',
            target_id: 1,
            topic_id: 101,
            label: 'doubtful',
            updated_at: '2026-06-20T09:00:00',
          },
        ],
        unfamiliar_topics: [],
      },
    })
  })
  await page.route('**/api/topics/101/local-events', async (route) => {
    await route.fulfill({ json: localEvents })
  })
  await page.route('**/api/auto-refresh/status', async (route) => {
    await route.fulfill({
      json: {
        enabled: true,
        running: false,
        last_started_at: '2026-07-04T12:00:00',
        last_finished_at: '2026-07-04T12:01:00',
        last_error: '',
        news_refreshed: 2,
        news_errors: ['美伊战争：RuntimeError: feed timeout'],
        frontier_refreshed: true,
        skipped_active: 1,
      },
    })
  })
  await page.route('**/api/auto-refresh/run', async (route) => {
    autoRefreshRuns += 1
    await route.fulfill({
      json: {
        enabled: true,
        running: false,
        last_started_at: '2026-07-04T12:30:00',
        last_finished_at: '2026-07-04T12:31:00',
        last_error: '',
        news_refreshed: 3,
        news_errors: [],
        frontier_refreshed: false,
        skipped_active: 0,
      },
    })
  })
  await page.route('**/api/cognition/marks', async (route) => {
    const body = route.request().postDataJSON()
    await route.fulfill({
      json: {
        id: 1,
        target_type: body.target_type,
        target_id: body.target_id,
        topic_id: body.topic_id,
        label: body.label,
        updated_at: '2026-06-20T10:00:00',
      },
    })
  })
  await page.route('**/api/topics/101/deep-analysis/jobs', async (route) => {
    startedJobs.push('deep')
    await route.fulfill({ json: analysisJob('deep-job', 'deep') })
  })
  await page.route('**/api/topics/101/academic/jobs', async (route) => {
    startedJobs.push('academic')
    await route.fulfill({ json: analysisJob('academic-job', 'academic') })
  })
  await page.route('**/api/topics/101/sentiment/jobs', async (route) => {
    startedJobs.push('sentiment')
    await route.fulfill({ json: analysisJob('sentiment-job', 'sentiment') })
  })
  await page.route('**/api/topics/101/cross-synthesis/jobs', async (route) => {
    // 记录 bundle 是否用轻量模式(refresh_voices:false) 触发三方对照。
    const body = route.request().postDataJSON() as { refresh_voices?: boolean } | null
    startedJobs.push(body?.refresh_voices === false ? 'cross:reuse' : 'cross:refresh')
    await route.fulfill({ json: analysisJob('cross-job', 'deep') })
  })
  await page.route('**/api/search/jobs', async (route) => {
    const body = route.request().postDataJSON() as { query: string }
    searchPayloads.push(body)
    await route.fulfill({
      json: {
        id: `search-refresh-${searchPayloads.length}`,
        query: body.query,
        status: 'done',
        steps: [],
        created_at: '2026-06-20T10:00:00',
        updated_at: '2026-06-20T10:00:00',
        result: null,
        error: '',
      },
    })
  })
  await page.route('**/api/search/jobs/*', async (route) => {
    const url = route.request().url()
    if (url.includes('search-refresh-')) {
      const id = url.split('/').pop() || ''
      const index = Number(id.replace('search-refresh-', '')) - 1
      const query = searchPayloads[index]?.query || topic.name
      await route.fulfill({
        json: {
          id,
          query,
          status: 'done',
          steps: [],
          created_at: '2026-06-20T10:00:00',
          updated_at: '2026-06-20T10:00:00',
          result: {
            topic: { ...topic, queries: [query] },
            collect: {
              raw: 0,
              kept: 0,
              new_articles: 0,
              new_links: 0,
              source_count: 0,
              requests: [],
              errors: [],
            },
            steps: [],
            subtopics: [],
            analogues: [],
            ...localEvents,
          },
          error: '',
        },
      })
    } else if (url.includes('deep-job')) {
      await route.fulfill({ json: analysisJob('deep-job', 'deep') })
    } else if (url.includes('academic-job')) {
      await route.fulfill({ json: analysisJob('academic-job', 'academic') })
    } else if (url.includes('cross-job')) {
      await route.fulfill({ json: analysisJob('cross-job', 'deep') })
    } else {
      await route.fulfill({ json: analysisJob('sentiment-job', 'sentiment') })
    }
  })
}

function analysisJob(id: string, kind: 'deep' | 'academic' | 'sentiment') {
  const base = {
    id,
    query: '',
    status: kind === 'sentiment' ? 'empty' : 'done',
    steps: [{ key: 'done', label: 'done', status: 'done' }],
    created_at: '2026-06-20T10:00:00',
    updated_at: '2026-06-20T10:00:00',
    error: '',
  }
  if (kind === 'deep') {
    return {
      ...base,
      result: {
        topic_id: 101,
        topic_name: topic.name,
        enrich: { limit: 30, pending: 0, processed: 1, relevant: 1, batches: 1, calls: 1, errors: [] },
        synthesize: { input_articles: 1, timeline: 1, framing: 1, analysis_chars: 20, calls: 1 },
        timeline: [],
        framing: [],
        analysis_md: 'LLM done',
      },
    }
  }
  if (kind === 'academic') {
    return {
      ...base,
      result: {
        topic_id: 101,
        topic_name: topic.name,
        papers: [],
        graph: { nodes: [], edges: [] },
        schools: [],
        foundational_papers: [],
        summary_md: '',
      },
    }
  }
  return {
    ...base,
    result: {
      topic_id: 101,
      topic_name: topic.name,
      platform: 'reddit',
      warning: '',
      posts: [],
      summary_md: '',
    },
  }
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('explains stale latest-report dates as last collected time', async ({ page }) => {
  await openWorkbench(page)

  const staleNotice = page.locator('.freshness-warning')
  await expect(staleNotice).toContainText('最后采集时间')
  await expect(staleNotice).toContainText('2026/06/20')
  await expect(staleNotice).toContainText('不代表世界没有新报道')
  await expect(staleNotice).toContainText('刷新')
})

test('refreshes stale topics with the current topic context', async ({ page }) => {
  await openWorkbench(page)

  await page.locator('.event-input').fill('unrelated residual query')
  await page.locator('.freshness-warning').getByRole('button', { name: '刷新采集' }).click()

  await expect.poll(() => searchPayloads.map((payload) => payload.query)).toEqual(['美伊战争'])
})

test('shows backend auto-refresh status and can trigger it without losing topic context', async ({ page }) => {
  await openWorkbench(page)

  const status = page.locator('.auto-refresh-status')
  await expect(status.getByText('自动刷新：已开启')).toBeVisible()
  await expect(status.getByText('上次完成 2026/07/04 12:01')).toBeVisible()
  await expect(status.getByText('新闻刷新 2 个')).toBeVisible()
  await expect(status.getByText('前沿日报已更新')).toBeVisible()
  await expect(status.getByText('跳过 1 个活跃任务')).toBeVisible()
  await expect(status.getByText('feed timeout')).toBeVisible()

  await status.getByRole('button', { name: '立即运行' }).click()

  await expect.poll(() => autoRefreshRuns).toBe(1)
  await expect(status.getByText('上次完成 2026/07/04 12:31')).toBeVisible()
  await expect(status.getByText('新闻刷新 3 个')).toBeVisible()
  await expect(status.getByText('feed timeout')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '美伊战争' })).toBeVisible()
})

test('filters and sorts the event source matrix', async ({ page }) => {
  await openWorkbench(page)

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
  await openWorkbench(page)

  await page.locator('details.article-feed-collapse > summary').click()
  await expect(page.locator('details.article-feed-collapse > summary')).toContainText('2/3')
  await expect(page.locator('.substance-summary')).toContainText('1')
  await expect(page.locator('.article-group').filter({ hasText: '触发事件' })).toBeVisible()
  await expect(page.locator('.article-group').filter({ hasText: '影响后果' })).toBeVisible()

  await page.locator('.article-row').filter({ hasText: 'Reuters reports US-Iran strike risk' }).getByRole('button', { name: '透视' }).click()
  await expect(page.locator('.article-perspective')).toContainText('摘要透视')
  await expect(page.locator('.article-perspective')).toContainText('strike risk')
  await expect(page.locator('.article-perspective')).toContainText('market panic is everywhere')
  await expect(page.locator('.article-row').filter({ hasText: 'Reuters reports US-Iran strike risk' }).getByRole('button', { name: '意外' })).toHaveCount(0)
  await page.reload()
  await switchToWorkbench(page)
  await page.locator('details.article-feed-collapse > summary').click()
  await expect(page.locator('.article-row').filter({ hasText: 'Reuters reports US-Iran strike risk' }).locator('.cognition-chip')).toHaveCount(0)

  await page.getByLabel('报道功能分类筛选').selectOption('影响后果')
  const articleGroups = page.locator('.article-group')
  await expect(articleGroups.getByRole('link', { name: 'Oil markets react to US-Iran conflict' })).toBeVisible()
  await expect(articleGroups.getByRole('link', { name: 'Reuters reports US-Iran strike risk' })).toBeHidden()
})

test('renders source matrix controls on mobile without horizontal overflow', async ({ page }) => {
  await openWorkbench(page)

  await expect(page.locator('.source-matrix').getByText('来源矩阵')).toBeVisible()
  await expect(page.locator('.source-matrix-tools')).toBeVisible()

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2)
  expect(overflow).toBe(false)
})

test('keeps secondary media panels collapsed with count summaries by default', async ({ page }) => {
  await openWorkbench(page)

  await expect(page.getByRole('heading', { name: '事件发展轴' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '美国与伊朗冲突进入关键节点' })).toBeVisible()
  await expect(page.locator('details.article-feed-collapse > summary')).toContainText('已评分 2/3')

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
      name: /媒体立场时间线.*1 期/,
      hiddenText: '2026-06',
    },
    {
      name: /叙事趋同信号.*1 条/,
      hiddenText: 'Bloomberg',
    },
  ]

  for (const panel of collapsedPanels) {
    const details = page.locator('details.media-collapse').filter({
      has: page.locator('summary').filter({ hasText: panel.name }),
    })
    const summary = details.locator('summary').first()
    await expect(summary).toBeVisible()
    await expect(details.getByText(panel.hiddenText)).toBeHidden()
    await summary.click()
    await expect(details.getByText(panel.hiddenText)).toBeVisible()
  }
})

test('shows narrative convergence signals as evidence cards', async ({ page }) => {
  await openWorkbench(page)

  const toggle = page.locator('details.media-collapse > summary').filter({
    hasText: /叙事趋同信号.*1 条/,
  })
  await toggle.click()

  await expect(page.getByText('主题内相似说法聚合，不代表事实真假或操控判定。')).toBeVisible()

  const card = page.locator('.narrative-signal').filter({ hasText: 'ai capex boom' })
  await expect(card).toBeVisible()
  await expect(card.getByText('相似说法')).toBeVisible()
  await expect(card.getByText('3 源')).toBeVisible()
  await expect(card.getByText('3 篇')).toBeVisible()
  await expect(card.getByText('2026/06/01 至 2026/06/03')).toBeVisible()
  await expect(card.getByText('Reuters')).toBeVisible()
  await expect(card.getByText('Financial Times')).toBeVisible()
  await expect(card.getByText('Bloomberg')).toBeVisible()
  await expect(card.getByText('代表报道')).toBeVisible()
  await expect(card.getByText('AI capex boom reshapes market')).toBeVisible()
})

test('summarizes media stance timeline as trend changes with evidence', async ({ page }) => {
  await page.route('**/api/topics/101/local-events', async (route) => {
    await route.fulfill({
      json: {
        ...localEvents,
        stance_evolution: [
          {
            period: '2026-05',
            dominant_stance: '中性观察',
            counts: { 中性观察: 4, 影响后果: 1 },
            article_ids: [1, 3],
          },
          {
            period: '2026-06',
            dominant_stance: '冲突/安全',
            counts: { 中性观察: 1, 冲突安全: 5, 影响后果: 3 },
            article_ids: [1, 2, 3],
          },
        ],
      },
    })
  })

  await openWorkbench(page)
  await page.locator('details.media-collapse > summary').filter({
    hasText: /媒体立场时间线.*2 期/,
  }).click()

  const panel = page.locator('.stance-trend-panel')
  await expect(panel.getByText('主要变化')).toBeVisible()
  const trendCard = panel.locator('.stance-trend-card').filter({ hasText: '冲突安全' })
  await expect(trendCard.locator('.stance-trend-head strong')).toHaveText('冲突安全')
  await expect(trendCard.getByText('增强 +5')).toBeVisible()
  await expect(trendCard.getByText('占比 0% → 56%')).toBeVisible()
  await expect(trendCard.getByText('转折期 2026-06')).toBeVisible()
  await expect(trendCard.getByText(/推动来源.*Reuters/)).toBeVisible()
  await expect(trendCard.getByText('代表报道')).toBeVisible()
  await expect(trendCard.getByText('Reuters reports US-Iran strike risk')).toBeVisible()
})

test('degrades media stance timeline when the sample is too small', async ({ page }) => {
  await page.route('**/api/topics/101/local-events', async (route) => {
    await route.fulfill({
      json: {
        ...localEvents,
        stance_evolution: [
          {
            period: '2026-05',
            dominant_stance: '中性观察',
            counts: { 中性观察: 1 },
            article_ids: [3],
          },
          {
            period: '2026-06',
            dominant_stance: '冲突安全',
            counts: { 冲突安全: 1 },
            article_ids: [1],
          },
        ],
      },
    })
  })

  await openWorkbench(page)
  await page.locator('details.media-collapse > summary').filter({
    hasText: /媒体立场时间线.*2 期/,
  }).click()

  const panel = page.locator('.stance-trend-panel')
  await expect(panel.getByText('当前样本只能显示立场分布')).toBeVisible()
  await expect(panel.locator('.stance-trend-card')).toHaveCount(0)
  await expect(panel.getByText('2026-06')).toBeVisible()
  await expect(panel.getByText('冲突安全 1')).toBeVisible()
})

test('keeps media stance timeline distribution-only when the shift is weak', async ({ page }) => {
  await page.route('**/api/topics/101/local-events', async (route) => {
    await route.fulfill({
      json: {
        ...localEvents,
        stance_evolution: [
          {
            period: '2026-05',
            dominant_stance: 'neutral',
            counts: { neutral: 4, conflict: 3 },
            article_ids: [1, 2, 3],
          },
          {
            period: '2026-06',
            dominant_stance: 'neutral',
            counts: { neutral: 3, conflict: 4 },
            article_ids: [1, 2, 3],
          },
        ],
      },
    })
  })

  await openWorkbench(page)
  await page.locator('details.media-collapse > summary').filter({
    hasText: /媒体立场时间线.*2 期/,
  }).click()

  const panel = page.locator('.stance-trend-panel')
  await expect(panel.locator('.stance-trend-card')).toHaveCount(0)
  await expect(panel.getByText('2026-06')).toBeVisible()
  await expect(panel.getByText('conflict 4')).toBeVisible()
})

test('shows an event structure tree from existing media signals', async ({ page }) => {
  await openWorkbench(page)

  const toggle = page.locator('details.media-collapse > summary').filter({
    hasText: /事件发展网络.*1 节点/,
  })

  await expect(toggle).toBeVisible()
  await expect(page.getByText('本地证据边')).toBeHidden()

  await toggle.click()

  const network = page.locator('.event-graph')
  await expect(network).toBeVisible()
  await expect(network.getByText('本地证据边，不显示 LLM 因果假设。')).toBeVisible()
  // 节点标题在 SVG 里按宽度截断，全名保留在 <g role="button"> 的 aria-label 中
  await expect(network.getByRole('button', { name: /美国与伊朗冲突进入关键节点/ })).toBeVisible()
  await expect(network.getByText('暂无可连接的事件边。')).toBeVisible()
})

test('renders local evidence edges between events in the event network', async ({ page }) => {
  await page.route('**/api/topics/101/local-events', async (route) => {
    await route.fulfill({
      json: {
        ...localEvents,
        events: [
          localEvents.events[0],
          {
            ...localEvents.events[0],
            date: '2026-06-21',
            title_zh: '油价与外交反应继续发酵',
            summary_zh: '后续报道集中讨论油价和外交反应。',
            article_ids: [4, 5, 6],
            source_count: 3,
            article_count: 3,
            sources: [
              { name: 'Reuters', count: 1, tier: 'wire', tier_label: '通讯社' },
              { name: 'Financial Times', count: 2, tier: 'professional', tier_label: '专业媒体' },
            ],
            source_matrix: [
              localEvents.events[0].source_matrix[0],
              localEvents.events[0].source_matrix[1],
            ],
            entities: [
              { term: '伊朗', count: 2, weight: 0.7, kind: 'place', kind_label: '地点' },
            ],
            location_signals: [{ term: '伊朗', count: 2, weight: 0.7, kind: 'place', kind_label: '地点' }],
          },
        ],
      },
    })
  })

  await openWorkbench(page)
  await page.locator('details.media-collapse > summary').filter({
    hasText: /事件发展网络.*2 节点/,
  }).click()

  const network = page.locator('.event-graph')
  await expect(network.locator('.event-graph-node')).toHaveCount(2)
  // 证据边始终可见（审计红线）：每条边一行，标签 + 连接符 + 可核查证据项
  const chronRow = network.locator('.event-graph-evidence-row').filter({ hasText: '时间顺序' })
  const entityRow = network.locator('.event-graph-evidence-row').filter({ hasText: '共享对象' })
  const sourceRow = network.locator('.event-graph-evidence-row').filter({ hasText: '共同来源' })
  await expect(chronRow).toContainText('#1 → #2')
  await expect(entityRow).toContainText('#1 ↔ #2')
  await expect(sourceRow).toContainText('#1 ↔ #2')
  await expect(entityRow.locator('.evidence-item', { hasText: /^伊朗$/ })).toBeVisible()
  await expect(sourceRow.locator('.evidence-item', { hasText: /^Reuters$/ })).toBeVisible()
})

test('prefers the backend event graph and maps node ids to display order', async ({ page }) => {
  // 后端返回的 id 是任意主键(51/52),适配器要按顺序映射成 #1/#2,并且后端标题压过本地兜底。
  await page.route('**/api/topics/101/event-graph', async (route) => {
    await route.fulfill({
      json: {
        nodes: [
          { id: 51, date: '2026-06-20', title_zh: '后端事件A：冲突升级', summary_zh: '后端摘要A', source_count: 4, article_count: 6 },
          { id: 52, date: '2026-06-21', title_zh: '后端事件B：外交斡旋', summary_zh: '后端摘要B', source_count: 3, article_count: 3 },
        ],
        edges: [
          { from_id: 51, to_id: 52, relation_type: 'chronological', direction: 'directed', evidence: '时间先后', items: [] },
          { from_id: 51, to_id: 52, relation_type: 'shared_source', direction: 'symmetric', evidence: '共同来源', items: ['Reuters'] },
        ],
        degraded: false,
        note: '',
      },
    })
  })

  await openWorkbench(page)
  await page.locator('details.media-collapse > summary').filter({
    hasText: /事件发展网络.*2 节点/,
  }).click()

  const network = page.locator('.event-graph')
  await expect(network.locator('.event-graph-node')).toHaveCount(2)
  // 后端标题压过本地兜底事件
  await expect(network.getByRole('button', { name: /后端事件A：冲突升级/ })).toBeVisible()
  await expect(network.getByRole('button', { name: /后端事件B：外交斡旋/ })).toBeVisible()
  // id 51/52 → 序号 #1/#2，而非原始主键
  const chronRow = network.locator('.event-graph-evidence-row').filter({ hasText: '时间顺序' })
  const sourceRow = network.locator('.event-graph-evidence-row').filter({ hasText: '共同来源' })
  await expect(chronRow).toContainText('#1 → #2')
  await expect(sourceRow).toContainText('#1 ↔ #2')
  await expect(sourceRow.locator('.evidence-item', { hasText: /^Reuters$/ })).toBeVisible()
})

test('shows selected event detail inline below the clicked timeline node', async ({ page }) => {
  await openWorkbench(page)

  await expect(page.getByText('Selected Node')).toHaveCount(0)
  await expect(page.locator('.event-detail')).toHaveCount(0)

  await page.locator('.timeline-node').filter({ hasText: '美国与伊朗冲突进入关键节点' }).click()

  const timelineItem = page.locator('.timeline-item').filter({ hasText: '美国与伊朗冲突进入关键节点' })
  await expect(timelineItem.locator('.event-detail-inline')).toBeVisible()
  await expect(timelineItem.locator('.event-detail-inline').getByRole('button', { name: '各国怎么报道' })).toBeVisible()
  await expect(page.locator('.feed-pane > .event-detail')).toHaveCount(0)
})

test('renders the multi-source contrast table with neutral coverage-gap wording', async ({ page }) => {
  // 对照台按 event_id 取数：先给后端事件图一个稳定 id（node[0].id=51），
  // 选中时间轴第 0 个节点 → selectedEventId=51 → 触发 /events/51/contrast。
  await page.route('**/api/topics/101/event-graph', async (route) => {
    await route.fulfill({
      json: {
        nodes: [
          { id: 51, date: '2026-06-20', title_zh: '美国与伊朗冲突进入关键节点', summary_zh: '摘要', source_count: 3, article_count: 6 },
        ],
        edges: [],
        degraded: true,
        note: '',
      },
    })
  })
  await page.route('**/api/topics/101/events/51/contrast', async (route) => {
    await route.fulfill({
      json: {
        event: { id: 51, date: '2026-06-20', title_zh: '美国与伊朗冲突进入关键节点', summary_zh: '摘要', source_count: 3, article_count: 6 },
        sources: [
          {
            source: 'Reuters', tier: 'wire', tier_label: '通讯社',
            stance: '风险/审慎', stance_summary: '强调升级风险',
            substance_score: 82, substance_note: '含具体时间和可核查事实',
            emotion_score: 25, emotion_note: '修辞压力较低',
            emphasized_entities: [{ term: '霍尔木兹海峡', count: 2, kind: 'entity' }],
            emphasized_keywords: [{ term: '制裁', count: 1, kind: 'keyword' }],
            representative_title: 'Reuters headline', url: 'https://example.com/r1',
            article_ids: [10, 11],
            articles: [{ id: 10, title: 'Reuters headline', url: 'https://example.com/r1', published_at: '2026-06-20T01:00:00' }],
          },
          {
            source: 'BBC', tier: 'mainstream', tier_label: '主流媒体',
            stance: '中性观察', stance_summary: '侧重外交降温',
            substance_score: -1, substance_note: '',
            emotion_score: -1, emotion_note: '',
            emphasized_entities: [], emphasized_keywords: [],
            representative_title: 'BBC headline', url: 'https://example.com/b1',
            article_ids: [12],
            articles: [{ id: 12, title: 'BBC headline', url: 'https://example.com/b1', published_at: '2026-06-20T03:00:00' }],
          },
        ],
        coverage_gaps: [
          { term: '霍尔木兹海峡', kind: 'entity', salience: 3, covered_by: ['Reuters'], not_observed_in: ['BBC'], evidence_article_ids: [10] },
          { term: '油价', kind: 'keyword', salience: 1, covered_by: ['Reuters'], not_observed_in: ['BBC'], evidence_article_ids: [10] },
        ],
        degraded: false,
        note: '',
      },
    })
  })

  await openWorkbench(page)
  await page.locator('.timeline-node').filter({ hasText: '美国与伊朗冲突进入关键节点' }).click()

  const panel = page.locator('.event-contrast-panel')
  await panel.getByRole('button', { name: '生成对照' }).click()

  const contrast = panel.locator('.event-contrast')
  // 两个来源并排成列
  await expect(contrast.locator('.contrast-col')).toHaveCount(2)
  await expect(contrast.locator('.contrast-col-head', { hasText: 'Reuters' })).toBeVisible()
  await expect(contrast.locator('.contrast-col-head', { hasText: 'BBC' })).toBeVisible()
  // 富化字段缺失（-1）诚实标「未评分」，不伪造分数
  await expect(contrast.locator('.contrast-col').filter({ hasText: 'BBC' }).locator('.unscored')).toHaveCount(2)
  // 覆盖差异用中性措辞「未在…样本中观察到」，不写成蓄意隐瞒
  const gap = contrast.locator('.contrast-gap-row').filter({ hasText: '霍尔木兹海峡' })
  await expect(gap).toContainText('仅见于 Reuters')
  await expect(gap).toContainText('未在 BBC 的样本中观察到')
  // 强度亮出来（诚实展示证据强度，不藏阈值）：强差异 ×3
  await expect(gap).toContainText('强调 ×3')
  // 弱差异（salience==1）淡化，但不静默丢弃——仍可见、仍可核查
  const weakGap = contrast.locator('.contrast-gap-row').filter({ hasText: '油价' })
  await expect(weakGap).toHaveClass(/weak/)
  await expect(weakGap).toContainText('强调 ×1')
})

test('disables the contrast trigger when no stable backend event id is available', async ({ page }) => {
  // 无后端事件图 → 本地兜底事件无稳定 id → 按钮禁用并诚实提示，不伪造 id。
  await openWorkbench(page)
  await page.locator('.timeline-node').filter({ hasText: '美国与伊朗冲突进入关键节点' }).click()

  const panel = page.locator('.event-contrast-panel')
  await expect(panel.getByRole('button', { name: '生成对照' })).toBeDisabled()
  await expect(panel).toContainText('需先切到后端事件图')
})

test('starts academic, sentiment and reuse-voices cross-synthesis with LLM analysis', async ({ page }) => {
  await openWorkbench(page)

  await page.getByRole('button', { name: /深度分析（LLM/ }).click()

  // 深度分析(三级)先并发跑三个一级声部, 再用轻量模式(refresh_voices:false)跑三方对照。
  await expect.poll(() => startedJobs.sort()).toEqual(['academic', 'cross:reuse', 'deep', 'sentiment'])
})

test('keeps existing LLM analysis visible when refreshing only the academic layer', async ({ page }) => {
  await page.route('**/api/topics/101', async (route) => {
    await route.fulfill({
      json: {
        ...topic,
        timeline: [],
        framing: [],
        analysis: {
          content_md: '<!-- analysis-source: llm -->\n## LLM批判分析\n已有深度分析仍应保留。',
        },
      },
    })
  })

  await openWorkbench(page)

  await page.getByLabel('专题视图导航').getByRole('button', { name: 'LLM 深度分析' }).click()
  await expect(page.getByText('当前展示 LLM 生成结果')).toBeVisible()
  await expect(page.locator('.llm-analysis-body')).toContainText('已有深度分析仍应保留')

  await page.getByLabel('专题视图导航').getByRole('button', { name: '学界' }).click()
  await page.getByRole('button', { name: /生成学界层|刷新学界层/ }).click()

  await expect.poll(() => startedJobs).toEqual(['academic'])

  await page.getByLabel('专题视图导航').getByRole('button', { name: 'LLM 深度分析' }).click()
  await expect(page.getByText('当前展示 LLM 生成结果')).toBeVisible()
  await expect(page.locator('.llm-analysis-body')).toContainText('已有深度分析仍应保留')
})
