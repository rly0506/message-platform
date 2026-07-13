import { expect, type Page, test } from '@playwright/test'
import { openWorkbench } from './helpers'

// RM-055 Phase 2 覆盖仪表 e2e：消费 GET /api/topics/{id}/coverage + analysis_meta。
// 红线覆盖：每个计数可点回证据 + 「未采集到」≠「未报道」+ 正文指标诚实 unknown +
//           分层对不上诚实标未分层 + 解码率 null 标未知 + 接口未上线时诚实降级 +
//           analysis_meta 旧行无快照时诚实标未知（不猜是否过时）。

const topic = {
  id: 101,
  name: '美伊战争',
  description: 'mock topic',
  queries: ['美伊战争'],
  status: 'active',
  created_at: '2026-06-21T00:00:00',
  article_count: 4,
  source_count: 2,
  enriched_count: 0,
  relevant_count: 4,
  latest_published_at: '2026-06-20T08:00:00',
}

const localEvents = {
  events: [],
  framing: [],
  analysis_md: '本地规则分析',
  stance_evolution: [],
  keywords: [],
  entities: [],
  entity_groups: [],
  criteria: [],
  narrative_signals: [],
}

// 覆盖快照：2 篇 gnews（1 解码 / 1 未解码）、1 篇 rss、1 篇未知采集器；
// 语言英/中各带、国家 US 1 篇、其余未标注；分层 1 篇 tier_1、其余未登记。
const coverage = {
  topic_id: 101,
  event_id: null,
  sample: {
    basis: 'persisted_topic_articles',
    article_count: 4,
    article_ids: [1, 2, 3, 4],
    note: 'Counts describe persisted articles collected for this scope; absence is not proof that a source did not report.',
  },
  independent_source_count: 2,
  collector_distribution: [
    { key: 'gnews', count: 2, article_ids: [1, 2] },
    { key: 'rss', count: 1, article_ids: [3] },
    { key: 'unknown', count: 1, article_ids: [4] },
  ],
  language_distribution: [
    { key: 'en', count: 2, article_ids: [1, 2] },
    { key: 'zh', count: 1, article_ids: [3] },
    { key: 'unknown', count: 1, article_ids: [4] },
  ],
  country_distribution: [
    { key: 'US', count: 1, article_ids: [1] },
    { key: 'unknown', count: 3, article_ids: [2, 3, 4] },
  ],
  url_decoding: {
    eligible_count: 2,
    decoded_count: 1,
    rate: 0.5,
    decoded_article_ids: [1],
    not_decoded_article_ids: [2],
  },
  source_registry: {
    type_distribution: [{ key: 'news_agency', count: 1, article_ids: [1] }],
    tier_distribution: [{ key: 'tier_1', count: 1, article_ids: [1] }],
    unclassified_article_ids: [2, 3, 4],
  },
  fulltext: { status: 'unknown', reason: 'article_bodies_not_persisted' },
}

const articles = {
  total: 2,
  items: [
    {
      id: 1,
      url: 'https://reuters.com/1',
      title: 'Reuters reports US-Iran strike risk',
      title_zh: '路透：美伊冲突升级风险',
      source: 'Reuters',
      source_lang: 'en',
      source_country: 'US',
      published_at: '2026-06-20T01:00:00',
      snippet: 'strike risk',
      snippet_zh: '',
      collector: 'gnews',
      enriched: false,
      relevance: 0.9,
      relevant: true,
      stance: '冲突/安全',
      stance_summary: '',
      category: '触发事件',
      category_reason: '',
    },
  ],
}

// analysis_meta：旧行无快照（sample_article_count=null）→ 前端必须诚实标「未知」，不猜过时。
function topicDetail(analysisMeta: unknown) {
  return {
    ...topic,
    timeline: [],
    framing: [],
    analysis: { content_md: '分析正文', generated_at: '2026-06-19T00:00:00' },
    analysis_meta: analysisMeta,
  }
}

async function mockCore(page: Page, detailMeta: unknown) {
  await page.route('**/api/topics', async (route) => route.fulfill({ json: [topic] }))
  await page.route('**/api/topics/101', async (route) => route.fulfill({ json: topicDetail(detailMeta) }))
  await page.route('**/api/topics/101/articles**', async (route) => route.fulfill({ json: articles }))
  await page.route('**/api/topics/101/local-events', async (route) => route.fulfill({ json: localEvents }))
  await page.route('**/api/topics/101/event-graph', async (route) =>
    route.fulfill({ json: { nodes: [], edges: [], degraded: true, note: '' } }),
  )
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

async function gotoCoverage(page: Page) {
  await openWorkbench(page)
  await page.getByLabel('专题视图导航').getByRole('button', { name: 'LLM 深度分析' }).click()
}

test('renders coverage overview and states uncollected is not unreported', async ({ page }) => {
  // sample_changed=true & evidence_newer=true → 有更新证据
  await mockCore(page, {
    source: 'llm',
    generated_at: '2026-06-19T00:00:00',
    sample_article_count: 3,
    sample_latest_published_at: '2026-06-19T00:00:00',
    current_article_count: 4,
    current_latest_published_at: '2026-06-20T08:00:00',
    evidence_newer: true,
    sample_changed: true,
  })
  await page.route('**/api/topics/101/coverage**', async (route) => route.fulfill({ json: coverage }))
  await gotoCoverage(page)

  const panel = page.locator('.coverage-panel')
  // 红线：认识论区分——「未采集到」≠「来源没报道」
  await expect(panel.locator('.coverage-note')).toContainText('不代表来源没有报道')
  await expect(panel.locator('.coverage-note')).toContainText('没抓到 ≠ 源没发')

  // 四个概览数：4 篇 / 2 独立来源 / 2 种语言（排除 unknown）/ 1 个国家（排除 unknown）
  const overview = panel.locator('.coverage-overview')
  await expect(overview).toContainText('4')
  await expect(overview).toContainText('篇报道')
  await expect(overview).toContainText('2')
  await expect(overview).toContainText('个独立来源')

  // analysis_meta 新鲜度：有更新证据
  const fresh = panel.locator('.freshness')
  await expect(fresh).toContainText('LLM 分析')
  await expect(fresh).toContainText('已有更新证据')
  await expect(fresh).toContainText('分析样本 3 篇 · 当前 4 篇')
})

test('makes every count clickable back to its evidence articles', async ({ page }) => {
  await mockCore(page, null)
  await page.route('**/api/topics/101/coverage**', async (route) => route.fulfill({ json: coverage }))
  await gotoCoverage(page)

  const panel = page.locator('.coverage-panel')
  // 点「篇报道」展开样本证据，命中当前页的文章给可点链接
  await panel.locator('.coverage-stat', { hasText: '篇报道' }).click()
  const evidence = panel.locator('.coverage-evidence').first()
  await expect(evidence.getByRole('link', { name: '路透：美伊冲突升级风险' })).toHaveAttribute(
    'href',
    'https://reuters.com/1',
  )
  // 不在当前页的文章（id 2/3/4）：诚实退化为「#id（不在当前页）」，不伪造链接
  await expect(evidence).toContainText('#2（不在当前页）')

  // 采集渠道桶也能点回证据
  await panel.locator('.dist-chip', { hasText: 'gnews · 2' }).click()
  await expect(panel.locator('.coverage-evidence.inline')).toContainText('路透：美伊冲突升级风险')
})

test('marks fulltext and unclassified sources honestly instead of faking them', async ({ page }) => {
  await mockCore(page, null)
  await page.route('**/api/topics/101/coverage**', async (route) => route.fulfill({ json: coverage }))
  await gotoCoverage(page)

  const panel = page.locator('.coverage-panel')
  // 正文指标诚实 unknown，不估算填充
  await expect(panel.locator('.coverage-meta-row')).toContainText('未知（正文未落库')
  // 解码率有真实样本 → 50%
  await expect(panel.locator('.coverage-meta-row')).toContainText('50%')
  await expect(panel.locator('.coverage-meta-row')).toContainText('1/2 篇')
  // 对不上源库的文章诚实标「未分层」，不塞进某层冒充
  await expect(panel.locator('.registry-unclassified')).toContainText('3 篇来源未登记在源库')
})

test('marks decode rate unknown when there is no gnews sample', async ({ page }) => {
  await mockCore(page, null)
  const noGnews = {
    ...coverage,
    url_decoding: {
      eligible_count: 0,
      decoded_count: 0,
      rate: null,
      decoded_article_ids: [],
      not_decoded_article_ids: [],
    },
  }
  await page.route('**/api/topics/101/coverage**', async (route) => route.fulfill({ json: noGnews }))
  await gotoCoverage(page)

  // eligible=0 → rate=null → 标「未知」，不显示 0%（无 gnews 样本 ≠ 解码失败）
  await expect(page.locator('.coverage-meta-row')).toContainText('未知')
  await expect(page.locator('.coverage-meta-row')).toContainText('本次无 GNews 样本')
})

test('degrades honestly when the coverage endpoint is not yet live', async ({ page }) => {
  await mockCore(page, null)
  // 接口 404（覆盖 API 在隔离分支、未合入本分支时的真实状态）→ 组件诚实降级：
  // 面板仍在、标题仍在、"未采集≠未报道"红线说明仍在，不崩、不伪造数据。
  await page.route('**/api/topics/101/coverage**', async (route) =>
    route.fulfill({ status: 404, json: { detail: 'Topic not found' } }),
  )
  await gotoCoverage(page)

  const panel = page.locator('.coverage-panel')
  // 面板整体不崩：标题在
  await expect(panel.getByText('本次分析基于什么')).toBeVisible()
  // 红线说明恒在，即便接口挂了也不误导
  await expect(panel.locator('.coverage-note')).toContainText('不代表来源没有报道')
  // 无 payload → 不渲染任何覆盖概览数（不伪造 0 篇冒充真实覆盖）
  await expect(panel.locator('.coverage-overview')).toHaveCount(0)
  // 接口错误被诚实透出（error 或 muted 兜底二选一，均不崩）
  await expect(panel.locator('.coverage-error, .muted')).toBeVisible()
})

test('states analysis freshness unknown for legacy analyses without a snapshot baseline', async ({ page }) => {
  // 旧行：sample_article_count=null → sample_changed/evidence_newer 都是 null → 诚实标未知
  await mockCore(page, {
    source: 'local',
    generated_at: '2026-06-10T00:00:00',
    sample_article_count: null,
    sample_latest_published_at: null,
    current_article_count: 4,
    current_latest_published_at: '2026-06-20T08:00:00',
    evidence_newer: null,
    sample_changed: null,
  })
  await page.route('**/api/topics/101/coverage**', async (route) => route.fulfill({ json: coverage }))
  await gotoCoverage(page)

  const fresh = page.locator('.coverage-panel .freshness')
  await expect(fresh).toContainText('本地分析')
  // 红线：不猜过时——旧行无基线诚实说「未知」
  await expect(fresh).toContainText('未记录基线')
})
