import { expect, type Page, test } from '@playwright/test'

const topic = {
  id: 501,
  project_id: 701,
  project_name: '战争研究',
  name: '俄乌战争',
  description: '长期追踪俄乌战争。',
  queries: ['俄乌战争'],
  status: 'active',
  archived_at: null,
  created_at: '2026-07-03T00:00:00',
  updated_at: '2026-07-03T00:00:00',
  article_count: 4,
  source_count: 3,
  enriched_count: 0,
  relevant_count: 4,
  latest_published_at: '2026-07-03T08:00:00',
}

const project = {
  id: 701,
  name: '战争研究',
  description: '地缘冲突专题集合。',
  status: 'active',
  archived_at: null,
  created_at: '2026-07-03T00:00:00',
  updated_at: '2026-07-03T00:00:00',
  topic_count: 1,
  topics: [topic],
}

const localEvents = {
  events: [
    {
      date: '2026-07-03',
      title_zh: '俄乌战争前线态势更新',
      summary_zh: '多家来源关注前线态势变化。',
      article_ids: [1],
      score: 0.7,
      importance_label: '高',
      coverage_label: '多源覆盖',
      selection_basis: ['2 篇报道'],
      source_count: 2,
      article_count: 2,
      sources: [{ name: 'Reuters', count: 1, tier: 'wire', tier_label: '通讯社' }],
      source_matrix: [],
      source_tiers: [],
      category: '行动进展',
      category_reason: '命中阶段词：frontline',
      stance: '冲突/安全',
      score_breakdown: [],
      evidence: {
        authority_sources: ['Reuters'],
        source_count: 2,
        article_count: 2,
        impact_terms: [],
        date_span_days: 1,
        first_sources: [],
        source_tiers: [],
      },
      keywords: [],
      entities: [],
      location_signals: [],
      evidence_articles: [
        {
          id: 1,
          title: 'Frontline status update',
          url: 'https://example.com/frontline',
          published_at: '2026-07-03T08:00:00',
          source: 'Reuters',
          category: '行动进展',
          relevance: 0.9,
          snippet: 'frontline status',
        },
      ],
    },
  ],
  framing: [],
  analysis_md: '',
  stance_evolution: [],
  keywords: [],
  entities: [],
  entity_groups: [],
  criteria: [],
}

function searchResult(query: string, subtopics: string[] = []) {
  return {
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
    steps: [
      { key: 'topic', label: '创建/复用专题', status: 'done' },
      { key: 'collect', label: '采集新闻', status: 'done' },
      { key: 'analyze', label: '本地分析', status: 'done' },
    ],
    subtopics,
    analogues: [],
    ...localEvents,
  }
}

async function mockApi(page: Page) {
  const searchPayloads: Array<{ query: string }> = []

  await page.route('**/api/projects', async (route) => {
    await route.fulfill({ json: [project] })
  })
  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: [topic] })
  })
  await page.route('**/api/topics/501', async (route) => {
    await route.fulfill({ json: { ...topic, timeline: [], framing: [], analysis: null } })
  })
  await page.route('**/api/topics/501/articles**', async (route) => {
    await route.fulfill({ json: { total: 0, items: [] } })
  })
  await page.route('**/api/topics/501/local-events', async (route) => {
    await route.fulfill({ json: localEvents })
  })
  await page.route('**/api/topics/501/academic', async (route) => {
    await route.fulfill({ status: 404, json: { detail: 'missing' } })
  })
  await page.route('**/api/topics/501/sentiment', async (route) => {
    await route.fulfill({ status: 404, json: { detail: 'missing' } })
  })
  await page.route('**/api/topics/501/cross-synthesis', async (route) => {
    await route.fulfill({ status: 404, json: { detail: 'missing' } })
  })
  await page.route('**/api/cognition/marks?**', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/cognition/marks/summary', async (route) => {
    await route.fulfill({ json: { counts: {}, recent: [], unfamiliar_topics: [] } })
  })
  await page.route('**/api/search/jobs', async (route) => {
    const body = route.request().postDataJSON() as { query: string }
    searchPayloads.push(body)
    const id = `search-${searchPayloads.length}`
    await route.fulfill({
      json: {
        id,
        query: body.query,
        status: 'done',
        steps: [],
        created_at: '2026-07-03T09:00:00',
        updated_at: '2026-07-03T09:00:00',
        result: null,
        error: '',
      },
    })
  })
  await page.route('**/api/search/jobs/*', async (route) => {
    const id = route.request().url().split('/').pop() || ''
    const index = Number(id.replace('search-', '')) - 1
    const query = searchPayloads[index]?.query || ''
    await route.fulfill({
      json: {
        id,
        query,
        status: 'done',
        steps: [],
        created_at: '2026-07-03T09:00:00',
        updated_at: '2026-07-03T09:00:00',
        result: searchResult(query, index === 0 ? ['前线态势'] : []),
        error: '',
      },
    })
  })

  return searchPayloads
}

test('keeps parent topic context when drilling into a suggested subtopic', async ({ page }) => {
  const searchPayloads = await mockApi(page)
  await page.goto('/')

  await page.locator('.event-input').fill('俄乌战争')
  await page.getByRole('button', { name: '搜集并生成时间轴' }).click()
  await expect(page.locator('.summary-band').getByRole('button', { name: '前线态势' })).toBeVisible()

  await page.locator('.summary-band').getByRole('button', { name: '前线态势' }).click()

  await expect.poll(() => searchPayloads.map((payload) => payload.query)).toEqual([
    '俄乌战争',
    '俄乌战争 前线态势',
  ])
})

test('shows contextual drilldown inside the selected event detail', async ({ page }) => {
  const searchPayloads = await mockApi(page)
  await page.goto('/')

  await page.locator('.event-input').fill('俄乌战争')
  await page.getByRole('button', { name: '搜集并生成时间轴' }).click()

  await page.locator('.timeline-node').filter({ hasText: '俄乌战争前线态势更新' }).click()

  const detail = page.locator('.timeline-item').filter({ hasText: '俄乌战争前线态势更新' }).locator('.event-detail-inline')
  await expect(detail).toBeVisible()
  await expect(detail.getByText('继续下钻')).toBeVisible()
  await detail.getByRole('button', { name: '前线态势' }).click()

  await expect.poll(() => searchPayloads.map((payload) => payload.query)).toEqual([
    '俄乌战争',
    '俄乌战争 前线态势',
  ])
})

test('offers an event-title drilldown when no suggested subtopics exist', async ({ page }) => {
  const searchPayloads = await mockApi(page)
  const eventWithoutParentContext = {
    ...localEvents,
    events: [
      {
        ...localEvents.events[0],
        title_zh: '前线态势更新',
      },
    ],
  }
  await page.route('**/api/topics/501/local-events', async (route) => {
    await route.fulfill({ json: eventWithoutParentContext })
  })
  await page.route('**/api/search/jobs/*', async (route) => {
    const id = route.request().url().split('/').pop() || ''
    const index = Number(id.replace('search-', '')) - 1
    const query = searchPayloads[index]?.query || ''
    await route.fulfill({
      json: {
        id,
        query,
        status: 'done',
        steps: [],
        created_at: '2026-07-03T09:00:00',
        updated_at: '2026-07-03T09:00:00',
        result: { ...searchResult(query, []), ...eventWithoutParentContext },
        error: '',
      },
    })
  })
  await page.goto('/')

  await page.locator('.event-input').fill('俄乌战争')
  await page.getByRole('button', { name: '搜集并生成时间轴' }).click()

  await page.locator('.timeline-node').filter({ hasText: '前线态势更新' }).click()

  const detail = page.locator('.timeline-item').filter({ hasText: '前线态势更新' }).locator('.event-detail-inline')
  await expect(detail.getByText('围绕此事件')).toBeVisible()
  await detail.getByRole('button', { name: '前线态势更新' }).click()

  await expect.poll(() => searchPayloads.map((payload) => payload.query)).toEqual([
    '俄乌战争',
    '俄乌战争 前线态势更新',
  ])
})

test('ignores duplicate event-search triggers while a search is starting', async ({ page }) => {
  const searchPayloads = await mockApi(page)
  const releaseSearches: Array<() => void> = []
  await page.route('**/api/search/jobs', async (route) => {
    const body = route.request().postDataJSON() as { query: string }
    searchPayloads.push(body)
    await new Promise<void>((resolve) => {
      releaseSearches.push(resolve)
    })
    await route.fulfill({
      json: {
        id: `search-${searchPayloads.length}`,
        query: body.query,
        status: 'done',
        steps: [],
        created_at: '2026-07-03T09:00:00',
        updated_at: '2026-07-03T09:00:00',
        result: null,
        error: '',
      },
    })
  })
  await page.goto('/')

  await page.locator('.event-input').fill('俄乌战争')
  await page.locator('.event-input').press('Enter')
  await page.locator('.event-input').press('Enter')
  await expect.poll(() => searchPayloads.length).toBe(1)

  for (const release of releaseSearches) release()
})
