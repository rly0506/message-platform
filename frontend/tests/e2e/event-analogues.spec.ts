import { expect, type Page, test } from '@playwright/test'
import { openWorkbench } from './helpers'

// U1 类比卡带 e2e：消费 /events/{id}/analogues。
// 红线覆盖：相似依据逐项可见 + 差异提醒必显（类比不预言）+ 空结果诚实措辞（未达阈值≠不存在）+ 降级诚实。

const topic = {
  id: 101,
  name: '美伊战争',
  description: 'mock topic',
  queries: ['美伊战争'],
  status: 'active',
  created_at: '2026-06-21T00:00:00',
  article_count: 6,
  source_count: 4,
  enriched_count: 0,
  relevant_count: 6,
  latest_published_at: '2026-06-20T08:00:00',
}

// 时间轴渲染只需一个事件；类比台按 event-graph 的稳定 id(51) 取数。
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
      selection_basis: ['4 个来源、6 篇报道'],
      source_count: 4,
      article_count: 6,
      sources: [{ name: 'Reuters', count: 3, tier: 'wire', tier_label: '通讯社' }],
      source_matrix: [],
      source_tiers: [{ key: 'wire', label: '通讯社', count: 3 }],
      category: '行动进展',
      category_reason: '命中阶段词：strike',
      stance: '冲突/安全',
      score_breakdown: {
        authority: { label: '权威来源', value: 0.8, weight: 0.22, reason: '命中来源：Reuters' },
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
      location_signals: [],
      evidence_articles: [],
    },
  ],
  framing: [],
  analysis_md: '本地规则分析',
  stance_evolution: [],
  keywords: [],
  entities: [],
  entity_groups: [],
  criteria: [],
  narrative_signals: [],
}

const stableGraph = {
  nodes: [
    {
      id: 51,
      date: '2026-06-20',
      title_zh: '美国与伊朗冲突进入关键节点',
      summary_zh: '摘要',
      source_count: 4,
      article_count: 6,
      article_ids: [1, 2, 3, 4],
    },
  ],
  edges: [],
  degraded: true,
  note: '',
}

async function mockCore(page: Page) {
  await page.route('**/api/topics', async (route) => route.fulfill({ json: [topic] }))
  await page.route('**/api/topics/101', async (route) =>
    route.fulfill({ json: { ...topic, timeline: [], framing: [], analysis: null } }),
  )
  await page.route('**/api/topics/101/articles**', async (route) =>
    route.fulfill({ json: { total: 0, items: [] } }),
  )
  await page.route('**/api/topics/101/local-events', async (route) => route.fulfill({ json: localEvents }))
  await page.route('**/api/cognition/marks?**', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/cognition/marks/summary', async (route) =>
    route.fulfill({ json: { counts: {}, recent: [], unfamiliar_topics: [] } }),
  )
  await page.route('**/api/auto-refresh/status', async (route) =>
    route.fulfill({
      json: {
        enabled: false, running: false, last_started_at: '', last_finished_at: '',
        last_error: '', news_refreshed: 0, news_errors: [], frontier_refreshed: false, skipped_active: 0,
      },
    }),
  )
}

function analoguePayload(eventId: number, note = '类比不等于预测；请同时阅读差异提醒。') {
  return {
    target: { topic_id: 101, event_id: eventId, title_zh: '', entities: [], keywords: [] },
    items: [],
    scan: {
      total_events: 2,
      eligible_candidates: 1,
      scanned_candidates: 1,
      candidate_cap: 500,
      truncated: false,
      note: '实际扫描 1 个。',
    },
    degraded: false,
    degraded_reason: '',
    note,
  }
}

test('renders analogue cards with per-item basis and mandatory difference reminders', async ({ page }) => {
  await mockCore(page)
  await page.route('**/api/topics/101/event-graph', async (route) => route.fulfill({ json: stableGraph }))
  await page.route('**/api/topics/101/events/51/analogues', async (route) =>
    route.fulfill({
      json: {
        target: { topic_id: 101, event_id: 51, title_zh: '美国与伊朗冲突进入关键节点', entities: ['伊朗'], keywords: [] },
        items: [
          {
            topic_id: 202,
            topic_name: '海湾局势',
            event_id: 88,
            date: '2019-09-14',
            title_zh: '沙特石油设施遇袭',
            similarity_score: 75,
            score_label: '较强相似',
            basis: [
              { kind: 'shared_entity', items: ['伊朗', '霍尔木兹海峡'], weight: 40 },
              { kind: 'shared_source_tier', items: ['通讯社'], weight: 10 },
            ],
            differences: [
              '目标事件为 2026-06-20，对方为 2019-09-14，时间相差 81 个月。',
              '对方 top 实体含沙特，本事件无。',
            ],
            evidence_article_ids: [301, 302],
            evidence_articles: [
              {
                id: 301,
                title: 'Reuters: Saudi oil facilities attacked',
                url: 'https://reuters.example/saudi-oil',
                source: 'Reuters',
                published_at: '2019-09-14T08:00:00',
              },
              {
                id: 302,
                title: 'AP: Oil market reacts',
                url: 'https://ap.example/oil-market',
                source: 'AP News',
                published_at: '2019-09-14T09:00:00',
              },
            ],
            note: '相似仅表示样本内结构信号重合，不代表同因、同果或会重演。',
          },
          {
            topic_id: 203,
            topic_name: '油价波动',
            event_id: 90,
            date: '2020-01-03',
            title_zh: '苏莱曼尼事件',
            similarity_score: 45,
            score_label: '有限相似',
            basis: [{ kind: 'shared_keyword', items: ['制裁'], weight: 8 }],
            differences: ['目标事件为 2026-06-20，对方为 2020-01-03，时间相差 77 个月。'],
            evidence_article_ids: [305],
            evidence_articles: [
              {
                id: 305,
                title: 'BBC: Soleimani event',
                url: 'https://bbc.example/soleimani',
                source: 'BBC',
                published_at: '2020-01-03T07:00:00',
              },
            ],
            note: '相似仅表示样本内结构信号重合，不代表同因、同果或会重演。',
          },
        ],
        scan: {
          total_events: 120,
          eligible_candidates: 40,
          scanned_candidates: 40,
          candidate_cap: 500,
          truncated: false,
          note: '线性检查全库 120 个事件；排除目标话题后 40 个候选，实际扫描 40 个。',
        },
        degraded: false,
        degraded_reason: '',
        note: '类比不等于预测；请同时阅读差异提醒。',
      },
    }),
  )

  await openWorkbench(page)
  await page.locator('.timeline-node').filter({ hasText: '美国与伊朗冲突进入关键节点' }).click()

  const panel = page.locator('.event-analogues-panel')
  await panel.getByRole('button', { name: '扫描先例' }).click()

  const analogues = panel.locator('.event-analogues')
  // 两张类比卡
  await expect(analogues.locator('.analogue-card')).toHaveCount(2)

  const strong = analogues.locator('.analogue-card').filter({ hasText: '沙特石油设施遇袭' })
  // 相似度徽标：较强相似用实心色调
  await expect(strong.locator('.analogue-score.tone-strong')).toHaveText('较强相似')
  // 相似依据逐项：kind 中文标签 + 具体命中项，不藏黑箱分数
  await expect(strong.locator('.analogue-basis')).toContainText('共享实体')
  await expect(strong.locator('.analogue-basis')).toContainText('伊朗、霍尔木兹海峡')
  await expect(strong.locator('.analogue-basis')).toContainText('共享来源层')
  // 差异提醒必显（红线：类比不预言）——差异区可见且含两条差异
  const diff = strong.locator('.analogue-diff')
  await expect(diff.getByText('差异提醒')).toBeVisible()
  await expect(diff).toContainText('时间相差 81 个月')
  await expect(diff).toContainText('对方 top 实体含沙特')
  // 样本证据既显示数量，也能点回后端返回的真实原文。
  await expect(strong.locator('.analogue-evidence')).toContainText('样本证据 2 篇')
  await expect(strong.getByRole('link', { name: 'Reuters: Saudi oil facilities attacked' })).toHaveAttribute(
    'href',
    'https://reuters.example/saudi-oil',
  )
  await expect(strong.locator('.analogue-item-note')).toContainText('不代表同因、同果或会重演')

  // 有限相似卡：弱化色调，但依据/差异同样完整可见
  const limited = analogues.locator('.analogue-card').filter({ hasText: '苏莱曼尼事件' })
  await expect(limited.locator('.analogue-score.tone-limited')).toHaveText('有限相似')
  await expect(limited.locator('.analogue-diff')).toContainText('时间相差 77 个月')

  // 扫描范围诚实交代 + 全局免责
  await expect(analogues.locator('.analogue-scan')).toContainText('实际扫描 40 个')
  await expect(analogues.locator('.analogue-foot-note')).toContainText('类比不等于预测')
})

test('states scanned-but-below-threshold honestly instead of claiming no precedent exists', async ({ page }) => {
  await mockCore(page)
  await page.route('**/api/topics/101/event-graph', async (route) => route.fulfill({ json: stableGraph }))
  await page.route('**/api/topics/101/events/51/analogues', async (route) =>
    route.fulfill({
      json: {
        target: { topic_id: 101, event_id: 51, title_zh: '美国与伊朗冲突进入关键节点', entities: [], keywords: [] },
        items: [],
        scan: {
          total_events: 80, eligible_candidates: 30, scanned_candidates: 30, candidate_cap: 500, truncated: false,
          note: '线性检查全库 80 个事件；排除目标话题后 30 个候选，实际扫描 30 个。',
        },
        degraded: false,
        degraded_reason: '',
        note: '类比不等于预测；请同时阅读差异提醒。',
      },
    }),
  )

  await openWorkbench(page)
  await page.locator('.timeline-node').filter({ hasText: '美国与伊朗冲突进入关键节点' }).click()

  const panel = page.locator('.event-analogues-panel')
  await panel.getByRole('button', { name: '扫描先例' }).click()

  const analogues = panel.locator('.event-analogues')
  await expect(analogues.locator('.analogue-card')).toHaveCount(0)
  // 空结果措辞诚实：说「未达阈值」「本库当前样本内未命中」，绝不说「无相似事件/不存在先例」
  const empty = analogues.locator('.analogue-empty')
  await expect(empty).toContainText('没有一个达到相似度阈值')
  await expect(empty).toContainText('不代表全网无先例')
  await expect(analogues).not.toContainText('无相似事件')
  // 扫描范围仍诚实交代
  await expect(analogues.locator('.analogue-scan')).toContainText('实际扫描 30 个')
})

test('shows an honest degraded reason when the topic has no persisted events', async ({ page }) => {
  await mockCore(page)
  await page.route('**/api/topics/101/event-graph', async (route) => route.fulfill({ json: stableGraph }))
  await page.route('**/api/topics/101/events/51/analogues', async (route) =>
    route.fulfill({
      json: {
        target: { topic_id: 101, event_id: 51, title_zh: '', entities: [], keywords: [] },
        items: [],
        scan: { total_events: 0, eligible_candidates: 0, scanned_candidates: 0, candidate_cap: 500, truncated: false, note: '' },
        degraded: true,
        degraded_reason: '该话题没有持久化事件；只读类比不会自动同步或创建事件。',
        note: '类比不等于预测；请同时阅读差异提醒。',
      },
    }),
  )

  await openWorkbench(page)
  await page.locator('.timeline-node').filter({ hasText: '美国与伊朗冲突进入关键节点' }).click()

  const panel = page.locator('.event-analogues-panel')
  await panel.getByRole('button', { name: '扫描先例' }).click()

  const analogues = panel.locator('.event-analogues')
  // 降级：诚实解释为何没有，且明确「只读、不会自动建事件」，不伪造相似
  await expect(analogues.locator('.coverage-gap')).toContainText('只读类比不会自动同步或创建事件')
  await expect(analogues.locator('.analogue-card')).toHaveCount(0)
})

test('disables the analogue scan when no stable backend event id is available', async ({ page }) => {
  await mockCore(page)
  // 无后端事件图 → 本地兜底事件无稳定 id → 按钮禁用并诚实提示，不伪造 id。
  await page.route('**/api/topics/101/event-graph', async (route) =>
    route.fulfill({ json: { nodes: [], edges: [], degraded: true, note: '' } }),
  )

  await openWorkbench(page)
  await page.locator('.timeline-node').filter({ hasText: '美国与伊朗冲突进入关键节点' }).click()

  const panel = page.locator('.event-analogues-panel')
  await expect(panel.getByRole('button', { name: '扫描先例' })).toBeDisabled()
  await expect(panel).toContainText('需先切到后端事件图')
})

test('matches the selected LLM timeline event to its stable graph id instead of reusing the array index', async ({ page }) => {
  await mockCore(page)
  await page.route('**/api/topics/101', async (route) =>
    route.fulfill({
      json: {
        ...topic,
        timeline: [
          {
            date: '2026-06-20',
            title_zh: '时间线事件 A',
            summary_zh: 'A',
            article_ids: [1, 2],
          },
          {
            date: '2026-06-21',
            title_zh: '时间线事件 B',
            summary_zh: 'B',
            article_ids: [3, 4],
          },
        ],
        framing: [],
        analysis: {
          content_md: '<!-- analysis-source: llm -->\nLLM 分析',
          generated_at: '2026-06-21T00:00:00',
        },
      },
    }),
  )
  await page.route('**/api/topics/101/event-graph', async (route) =>
    route.fulfill({
      json: {
        nodes: [
          { id: 52, date: '2026-06-21', title_zh: '图事件 B', summary_zh: 'B', source_count: 1, article_count: 2, article_ids: [3, 4] },
          { id: 51, date: '2026-06-20', title_zh: '图事件 A', summary_zh: 'A', source_count: 1, article_count: 2, article_ids: [1, 2] },
        ],
        edges: [],
        degraded: false,
        note: '',
      },
    }),
  )
  let requestedEventId: number | null = null
  await page.route('**/api/topics/101/events/*/analogues', async (route) => {
    const match = new URL(route.request().url()).pathname.match(/\/events\/(\d+)\/analogues$/)
    requestedEventId = match ? Number(match[1]) : null
    await route.fulfill({ json: analoguePayload(requestedEventId ?? 0) })
  })

  await openWorkbench(page)
  await page.locator('.timeline-node').filter({ hasText: '时间线事件 A' }).click()
  await page.locator('.event-analogues-panel').getByRole('button', { name: '扫描先例' }).click()

  await expect.poll(() => requestedEventId).toBe(51)
})

test('allows the newly selected event to load while an older analogue request later fails', async ({ page }) => {
  const secondEvent = {
    ...localEvents.events[0],
    date: '2026-06-21',
    title_zh: '第二事件',
    summary_zh: '第二事件摘要',
    article_ids: [5, 6],
    article_count: 2,
  }
  await mockCore(page)
  await page.route('**/api/topics/101/local-events', async (route) =>
    route.fulfill({ json: { ...localEvents, events: [localEvents.events[0], secondEvent] } }),
  )
  await page.route('**/api/topics/101/event-graph', async (route) =>
    route.fulfill({
      json: {
        nodes: [
          stableGraph.nodes[0],
          { id: 52, date: '2026-06-21', title_zh: '第二事件', summary_zh: '第二事件摘要', source_count: 1, article_count: 2, article_ids: [5, 6] },
        ],
        edges: [],
        degraded: false,
        note: '',
      },
    }),
  )

  let firstStarted = false
  let releaseFirst!: () => void
  const firstRelease = new Promise<void>((resolve) => { releaseFirst = resolve })
  await page.route('**/api/topics/101/events/51/analogues', async (route) => {
    firstStarted = true
    await firstRelease
    await route.fulfill({ status: 500, json: { detail: '旧事件失败' } })
  })
  await page.route('**/api/topics/101/events/52/analogues', async (route) =>
    route.fulfill({ json: analoguePayload(52, '第二事件类比已加载') }),
  )

  await openWorkbench(page)
  await page.locator('.timeline-node').filter({ hasText: '美国与伊朗冲突进入关键节点' }).click()
  await page.locator('.event-analogues-panel').getByRole('button', { name: '扫描先例' }).click()
  await expect.poll(() => firstStarted).toBe(true)
  await page.locator('.timeline-node').filter({ hasText: '第二事件' }).click()

  const secondPanel = page.locator('.event-analogues-panel')
  try {
    await expect(secondPanel.getByRole('button', { name: '扫描先例' })).toBeEnabled()
    await secondPanel.getByRole('button', { name: '扫描先例' }).click()
    await expect(secondPanel).toContainText('第二事件类比已加载')
  } finally {
    releaseFirst()
  }
  await expect(secondPanel).not.toContainText('旧事件失败')
})
