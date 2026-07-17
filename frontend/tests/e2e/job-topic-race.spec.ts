import { expect, type Page, test } from '@playwright/test'
import { openWorkbench } from './helpers'

// A stale async result that is correctly discarded produces NO observable change
// (the token/generation guard returns silently), so a test cannot wait for a
// positive signal from it. Instead, after the late response has reached the
// browser, cross a macrotask boundary (setTimeout 0) which flushes all pending
// microtasks — the fetch .then continuation, the awaited loadTopics/finish
// resumption, and Vue's reactive DOM flush — so any (broken) late write would be
// committed and visible BEFORE the absence assertion runs. Draining twice covers
// a two-hop continuation (e.g. loadTopics' fetchTopics → fetchProjects → return).
async function drainBrowserEventLoop(page: Page, times = 1) {
  for (let i = 0; i < times; i += 1) {
    await page.evaluate(() => new Promise<void>((r) => setTimeout(r, 0)))
  }
}

const topics = [
  {
    id: 701,
    name: 'Topic Alpha',
    description: 'first topic',
    queries: ['alpha'],
    status: 'active',
    created_at: '2026-07-04T00:00:00',
    article_count: 0,
    source_count: 0,
    enriched_count: 0,
    relevant_count: 0,
    latest_published_at: null,
  },
  {
    id: 702,
    name: 'Topic Beta',
    description: 'second topic',
    queries: ['beta'],
    status: 'active',
    created_at: '2026-07-04T00:00:00',
    article_count: 0,
    source_count: 0,
    enriched_count: 0,
    relevant_count: 0,
    latest_published_at: null,
  },
]

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

function topicDetail(id: number) {
  const topic = topics.find((item) => item.id === id) || topics[0]
  return { ...topic, timeline: [], framing: [], analysis: null }
}

function academicLayer(id: number) {
  return {
    topic_id: id,
    topic_name: topics.find((item) => item.id === id)?.name || '',
    papers: [],
    graph: { nodes: [], edges: [] },
    schools: [],
    foundational_papers: [],
    summary_md: '',
  }
}

function sentimentLayer(id: number) {
  return {
    topic_id: id,
    topic_name: topics.find((item) => item.id === id)?.name || '',
    platform: 'multi',
    warning: '',
    posts: [],
    summary_md: '',
  }
}

function crossLayer(id: number) {
  return {
    topic_id: id,
    topic_name: topics.find((item) => item.id === id)?.name || '',
    content_md: '',
    voices_used: [],
    generated_at: null,
  }
}

async function mockRaceApi(page: Page) {
  let alphaAcademicLoads = 0
  let betaAcademicLoads = 0
  let alphaSentimentLoads = 0
  let betaSentimentLoads = 0
  let alphaCrossLoads = 0
  let betaCrossLoads = 0
  const betaAcademicSettled = deferred()
  const betaSentimentSettled = deferred()
  const betaCrossSettled = deferred()
  const academicJobBarrier = deferred()
  const sentimentJobBarrier = deferred()
  const crossJobBarrier = deferred()
  const academicJobEntered = deferred()
  const sentimentJobEntered = deferred()
  const crossJobEntered = deferred()

  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: topics })
  })
  await page.route('**/api/projects', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route(/.*\/api\/topics\/(701|702)$/, async (route) => {
    const id = Number(route.request().url().split('/').pop())
    await route.fulfill({ json: topicDetail(id) })
  })
  await page.route(/.*\/api\/topics\/(701|702)\/articles.*/, async (route) => {
    await route.fulfill({ json: { total: 0, items: [] } })
  })
  await page.route(/.*\/api\/topics\/(701|702)\/local-events$/, async (route) => {
    await route.fulfill({ json: emptyLocalEvents })
  })
  await page.route(/.*\/api\/topics\/(701|702)\/academic$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/academic$/)?.[1])
    if (id === 701) alphaAcademicLoads += 1
    if (id === 702) betaAcademicLoads += 1
    await route.fulfill({ json: academicLayer(id) })
    if (id === 702) betaAcademicSettled.release()
  })
  await page.route(/.*\/api\/topics\/(701|702)\/sentiment$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/sentiment$/)?.[1])
    if (id === 701) alphaSentimentLoads += 1
    if (id === 702) betaSentimentLoads += 1
    await route.fulfill({ json: sentimentLayer(id) })
    if (id === 702) betaSentimentSettled.release()
  })
  await page.route('**/api/integrations/opencli/diagnostics', async (route) => {
    await route.fulfill({ json: { ok: true, command: 'opencli', resolved: 'opencli', message: '', recommended_command: '' } })
  })
  await page.route(/.*\/api\/topics\/(701|702)\/cross-synthesis$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/cross-synthesis$/)?.[1])
    if (id === 701) alphaCrossLoads += 1
    if (id === 702) betaCrossLoads += 1
    await route.fulfill({ json: crossLayer(id) })
    if (id === 702) betaCrossSettled.release()
  })
  await page.route('**/api/topics/701/academic/jobs', async (route) => {
    await route.fulfill({
      json: {
        id: 'academic-race-job',
        query: 'academic:Topic Alpha',
        status: 'queued',
        steps: [{ key: 'fetch', label: 'fetch', status: 'running' }],
        created_at: '2026-07-04T00:00:00',
        updated_at: '2026-07-04T00:00:00',
        result: null,
        error: '',
      },
    })
  })
  await page.route('**/api/topics/701/sentiment/jobs', async (route) => {
    await route.fulfill({
      json: {
        id: 'sentiment-race-job',
        query: 'sentiment:Topic Alpha',
        status: 'queued',
        steps: [{ key: 'fetch', label: 'fetch', status: 'running' }],
        created_at: '2026-07-04T00:00:00',
        updated_at: '2026-07-04T00:00:00',
        result: null,
        error: '',
      },
    })
  })
  await page.route('**/api/topics/701/cross-synthesis/jobs', async (route) => {
    await route.fulfill({
      json: {
        id: 'cross-race-job',
        query: 'cross-synthesis:Topic Alpha',
        status: 'queued',
        steps: [{ key: 'gather', label: 'gather', status: 'running' }],
        created_at: '2026-07-04T00:00:00',
        updated_at: '2026-07-04T00:00:00',
        result: null,
        error: '',
      },
    })
  })
  await page.route('**/api/search/jobs/academic-race-job', async (route) => {
    academicJobEntered.release()
    await academicJobBarrier.promise
    await route.fulfill({
      json: {
        id: 'academic-race-job',
        query: 'academic:Topic Alpha',
        status: 'done',
        steps: [{ key: 'fetch', label: 'fetch', status: 'done' }],
        created_at: '2026-07-04T00:00:00',
        updated_at: '2026-07-04T00:00:01',
        result: academicLayer(701),
        error: '',
      },
    })
  })
  await page.route('**/api/search/jobs/sentiment-race-job', async (route) => {
    sentimentJobEntered.release()
    await sentimentJobBarrier.promise
    await route.fulfill({
      json: {
        id: 'sentiment-race-job',
        query: 'sentiment:Topic Alpha',
        status: 'empty',
        steps: [{ key: 'fetch', label: 'fetch', status: 'empty' }],
        created_at: '2026-07-04T00:00:00',
        updated_at: '2026-07-04T00:00:01',
        result: sentimentLayer(701),
        error: '',
      },
    })
  })
  await page.route('**/api/search/jobs/cross-race-job', async (route) => {
    crossJobEntered.release()
    await crossJobBarrier.promise
    await route.fulfill({
      json: {
        id: 'cross-race-job',
        query: 'cross-synthesis:Topic Alpha',
        status: 'done',
        steps: [{ key: 'gather', label: 'gather', status: 'done' }],
        created_at: '2026-07-04T00:00:00',
        updated_at: '2026-07-04T00:00:01',
        result: {
          ...crossLayer(701),
          content_md: '## cross',
          voices_used: ['media'],
          chain: {},
        },
        error: '',
      },
    })
  })

  return {
    alphaAcademicLoads: () => alphaAcademicLoads,
    betaAcademicLoads: () => betaAcademicLoads,
    alphaSentimentLoads: () => alphaSentimentLoads,
    betaSentimentLoads: () => betaSentimentLoads,
    alphaCrossLoads: () => alphaCrossLoads,
    betaCrossLoads: () => betaCrossLoads,
    waitForBetaAcademicSettled: () => betaAcademicSettled.promise,
    waitForBetaSentimentSettled: () => betaSentimentSettled.promise,
    waitForBetaCrossSettled: () => betaCrossSettled.promise,
    waitUntilAcademicJobIsHeld: () => academicJobEntered.promise,
    waitUntilSentimentJobIsHeld: () => sentimentJobEntered.promise,
    waitUntilCrossJobIsHeld: () => crossJobEntered.promise,
    releaseAcademicJob: () => academicJobBarrier.release(),
    releaseSentimentJob: () => sentimentJobBarrier.release(),
    releaseCrossJob: () => crossJobBarrier.release(),
  }
}

// RM-065 P0 合同：A 下发起的任务在切到 B 后完成，必须彻底丢弃——
// 不把 A 的「已切换专题」文案写进 B 现在看的面板，也不触发对任一资源的二次加载。
// 每种资源在整个切换过程中最多一次有效加载（切题时由 watch 加载，任务完成不得重复）。

test('discards a finished academic job after switching topics without leaking into topic B', async ({ page }) => {
  const api = await mockRaceApi(page)
  await openWorkbench(page)

  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()
  await page.getByRole('button', { name: '学界视角' }).click()
  await expect(page.getByText(/学界任务：academic/)).toBeVisible()
  await api.waitUntilAcademicJobIsHeld()

  await page.getByLabel('选择专题').selectOption('702')
  await expect(page.getByRole('heading', { name: 'Topic Beta' })).toBeVisible()
  await api.waitForBetaAcademicSettled()
  const betaLoadsAfterSwitch = api.betaAcademicLoads()
  const alphaLoadsAfterSwitch = api.alphaAcademicLoads()
  expect(betaLoadsAfterSwitch).toBe(1)

  const jobDone = page.waitForResponse('**/api/search/jobs/academic-race-job')
  api.releaseAcademicJob()
  await jobDone
  await drainBrowserEventLoop(page, 2)

  // 合同：切走后 A 的完成文案不得出现在任何面板。
  await expect(page.getByText('学界任务已完成；你已切换专题，当前页未自动刷新。')).toHaveCount(0)
  // 合同：每资源最多一次有效加载——切走的任务完成后不得再加载 A 或 B。
  expect(api.betaAcademicLoads()).toBe(betaLoadsAfterSwitch)
  expect(api.alphaAcademicLoads()).toBe(alphaLoadsAfterSwitch)
})

test('discards a finished sentiment job after switching topics without leaking into topic B', async ({ page }) => {
  const api = await mockRaceApi(page)
  await openWorkbench(page)

  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()
  await page.locator('.deep-actions').getByRole('button', { name: '民间情绪' }).click()
  await expect(page.getByText(/民间情绪任务：sentimen/)).toBeVisible()
  await api.waitUntilSentimentJobIsHeld()

  await page.getByLabel('选择专题').selectOption('702')
  await expect(page.getByRole('heading', { name: 'Topic Beta' })).toBeVisible()
  await api.waitForBetaSentimentSettled()
  const betaLoadsAfterSwitch = api.betaSentimentLoads()
  const alphaLoadsAfterSwitch = api.alphaSentimentLoads()
  expect(betaLoadsAfterSwitch).toBe(1)

  const jobDone = page.waitForResponse('**/api/search/jobs/sentiment-race-job')
  api.releaseSentimentJob()
  await jobDone
  await drainBrowserEventLoop(page, 2)

  await expect(page.getByText('民间情绪任务已完成；你已切换专题，当前页未自动刷新。')).toHaveCount(0)
  expect(api.betaSentimentLoads()).toBe(betaLoadsAfterSwitch)
  expect(api.alphaSentimentLoads()).toBe(alphaLoadsAfterSwitch)
})

test('discards a finished cross-synthesis job after switching topics without leaking into topic B', async ({ page }) => {
  const api = await mockRaceApi(page)
  await openWorkbench(page)

  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()
  await page.locator('.deep-actions').getByRole('button', { name: /^三方对照$/ }).click()
  await expect(page.getByText(/三方对照任务：cross-r/)).toBeVisible()
  await api.waitUntilCrossJobIsHeld()

  await page.getByLabel('选择专题').selectOption('702')
  await expect(page.getByRole('heading', { name: 'Topic Beta' })).toBeVisible()
  await api.waitForBetaCrossSettled()
  const betaLoadsAfterSwitch = api.betaCrossLoads()
  const alphaLoadsAfterSwitch = api.alphaCrossLoads()
  expect(betaLoadsAfterSwitch).toBe(1)

  const jobDone = page.waitForResponse('**/api/search/jobs/cross-race-job')
  api.releaseCrossJob()
  await jobDone
  await drainBrowserEventLoop(page, 2)

  await expect(page.getByText('三方对照任务已完成；你已切换专题，当前页未自动刷新。')).toHaveCount(0)
  expect(api.betaCrossLoads()).toBe(betaLoadsAfterSwitch)
  expect(api.alphaCrossLoads()).toBe(alphaLoadsAfterSwitch)
})

// ── P0.7 frozen contract: search/deep full-lifecycle ownership (P0-T3, T4, T5) ──
// Shared lifecycle fixture. Topics 701=A, 702=B, 703=C. Every resource route carries
// a distinguishable `<letter>-<FRESH|STALE>:<resource>` marker on a real rendered
// surface (verified against source), so request counts alone cannot false-green.

type ResourceKey =
  | 'topic'
  | 'articles'
  | 'local-events'
  | 'event-graph'
  | 'academic'
  | 'sentiment'
  | 'cross-synthesis'

const resourceKeys: ResourceKey[] = [
  'topic', 'articles', 'local-events', 'event-graph',
  'academic', 'sentiment', 'cross-synthesis',
]

function deferred() {
  let release!: () => void
  const promise = new Promise<void>((done) => { release = done })
  return { promise, release: () => release() }
}

const letterOf: Record<number, 'A' | 'B' | 'C'> = { 701: 'A', 702: 'B', 703: 'C' }
function marker(id: number, freshness: 'STALE' | 'FRESH', resource: ResourceKey) {
  return `${letterOf[id]}-${freshness}:${resource}`
}

// Marker-bearing payload builders. Preconditions honored (verified against source):
// - topic marker on analysis.content_md WITHOUT the '<!-- analysis-source: llm -->'
//   sentinel (else hasLlmAnalysis flips true and majorEvents abandons localData.events).
// - articles marker on items[0].title with title_zh EMPTY (titleFor prefers title_zh).
// - sentiment posts[0].kind !== 'comment' (comments are filtered out of platform groups).
function detailC(id: number, freshness: 'STALE' | 'FRESH' = 'FRESH') {
  const topic = lifecycleTopics.find((item) => item.id === id) || lifecycleTopics[0]
  return {
    ...topic,
    timeline: [],
    framing: [],
    analysis: { id, generated_at: '2026-07-04T00:00:00', content_md: marker(id, freshness, 'topic') },
  }
}
function articlesC(id: number, freshness: 'STALE' | 'FRESH' = 'FRESH') {
  return {
    total: 1,
    items: [{
      id: id * 10 + (freshness === 'STALE' ? 1 : 0),
      url: `https://example.com/${id}/${freshness}`,
      title: marker(id, freshness, 'articles'),
      title_zh: '',
      source: 'Wire', source_lang: 'en', source_country: 'us',
      published_at: '2026-07-03T08:00:00', snippet: '', snippet_zh: '',
      collector: 'rss', enriched: false, relevance: 0.9, relevant: true,
      stance: '', stance_summary: '', category: '行动进展',
    }],
  }
}
function localEventsC(id: number, freshness: 'STALE' | 'FRESH' = 'FRESH') {
  return {
    ...emptyLocalEvents,
    events: [{
      id: id * 100 + (freshness === 'STALE' ? 1 : 0),
      date: '2026-07-03', title_zh: marker(id, freshness, 'local-events'),
      summary_zh: 'summary', article_ids: [id * 10],
      score: 1, source_count: 1, article_count: 1, stance: '综合判断',
    }],
  }
}
function eventGraphC(id: number, freshness: 'STALE' | 'FRESH' = 'FRESH') {
  return {
    nodes: [{
      id: id * 1000 + (freshness === 'STALE' ? 1 : 0),
      date: '2026-07-03', title_zh: marker(id, freshness, 'event-graph'),
      summary_zh: 'summary', source_count: 1, article_count: 1, article_ids: [id * 10],
    }],
    edges: [], degraded: false, note: '',
  }
}
function academicC(id: number, freshness: 'STALE' | 'FRESH' = 'FRESH') {
  return {
    topic_id: id, topic_name: letterOf[id],
    papers: [{
      openalex_id: `W${id}`, title: marker(id, freshness, 'academic'),
      year: 2020, cited_by_count: 1, authors: ['Author'], venue: 'Venue',
    }],
    graph: { nodes: [], edges: [] }, schools: [], foundational_papers: [], summary_md: '',
  }
}
function sentimentC(id: number, freshness: 'STALE' | 'FRESH' = 'FRESH') {
  return {
    topic_id: id, topic_name: letterOf[id], platform: 'multi', warning: '',
    posts: [{
      platform: 'reddit', kind: 'post', subreddit: 'news',
      title: marker(id, freshness, 'sentiment'), author: 'user', score: 1,
      num_comments: 0, url: `https://reddit.com/${id}`, created_utc: '2026-07-03T08:00:00',
      selftext_snippet: '',
    }],
    summary_md: '',
  }
}
function crossC(id: number, freshness: 'STALE' | 'FRESH' = 'FRESH') {
  return {
    topic_id: id, topic_name: letterOf[id],
    content_md: marker(id, freshness, 'cross-synthesis'),
    voices_used: ['media'], chain: {}, generated_at: '2026-07-04T00:00:00',
  }
}

const lifecycleTopics = [
  { id: 701, name: 'Topic Alpha', description: 'a', queries: ['alpha'], status: 'active', created_at: '2026-07-04T00:00:00', article_count: 1, source_count: 1, enriched_count: 0, relevant_count: 1, latest_published_at: '2026-07-03T08:00:00' },
  { id: 702, name: 'Topic Beta', description: 'b', queries: ['beta'], status: 'active', created_at: '2026-07-04T00:00:00', article_count: 1, source_count: 1, enriched_count: 0, relevant_count: 1, latest_published_at: '2026-07-03T08:00:00' },
  { id: 703, name: 'Topic Gamma', description: 'c', queries: ['gamma'], status: 'active', created_at: '2026-07-04T00:00:00', article_count: 1, source_count: 1, enriched_count: 0, relevant_count: 1, latest_published_at: '2026-07-03T08:00:00' },
]

function zeroLoads(): Record<ResourceKey, number> {
  return { topic: 0, articles: 0, 'local-events': 0, 'event-graph': 0, academic: 0, sentiment: 0, 'cross-synthesis': 0 }
}

// Registers the seven marker-bearing resource routes + per-(topic,resource) settled
// counters + a settled-count waiter. Job-protocol routes are added per-test on top.
async function mockLifecycleResources(page: Page) {
  // Two counters (mirrors the robust P0-T1 pattern in topic-load-race.spec.ts):
  //  • requested — bumped at handler ENTRY (before fulfill). The exactly-once UPPER
  //    bound reads this: a double-owner regression dispatches its duplicate
  //    synchronously in the same Promise.all as the primary load, so the duplicate's
  //    handler-entry bump lands before the primary settles → caught deterministically.
  //    (Reading the settled counter instead could miss a dispatched-but-not-yet-settled
  //    late duplicate — the audit's Important finding.)
  //  • settled — bumped AFTER fulfill. The waitForResources GATES read this, so a
  //    "resource loaded" wait only resolves once the response actually reached the browser.
  const requested: Record<number, Record<ResourceKey, number>> = { 701: zeroLoads(), 702: zeroLoads(), 703: zeroLoads() }
  const settled: Record<number, Record<ResourceKey, number>> = { 701: zeroLoads(), 702: zeroLoads(), 703: zeroLoads() }
  const waiters: Array<{ id: number; resource: ResourceKey; count: number; resolve: () => void }> = []
  const request = (id: number, resource: ResourceKey) => { if (requested[id]) requested[id][resource] += 1 }
  const settle = (id: number, resource: ResourceKey) => {
    if (!settled[id]) return
    settled[id][resource] += 1
    for (const w of [...waiters]) {
      if (w.id === id && w.resource === resource && settled[id][resource] >= w.count) {
        w.resolve()
        waiters.splice(waiters.indexOf(w), 1)
      }
    }
  }
  function waitForSettled(id: number, resource: ResourceKey, count: number) {
    if (settled[id] && settled[id][resource] >= count) return Promise.resolve()
    return new Promise<void>((resolve) => waiters.push({ id, resource, count, resolve }))
  }

  await page.route('**/api/topics', async (route) => { await route.fulfill({ json: lifecycleTopics }) })
  await page.route('**/api/projects', async (route) => { await route.fulfill({ json: [] }) })
  await page.route('**/api/integrations/opencli/diagnostics', async (route) => {
    await route.fulfill({ json: { ok: true, command: 'opencli', resolved: 'opencli', message: '', recommended_command: '' } })
  })
  await page.route(/.*\/api\/topics\/(701|702|703)$/, async (route) => {
    const id = Number(route.request().url().split('/').pop())
    request(id, 'topic'); await route.fulfill({ json: detailC(id) }); settle(id, 'topic')
  })
  await page.route(/.*\/api\/topics\/(701|702|703)\/articles.*/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/articles/)?.[1])
    request(id, 'articles'); await route.fulfill({ json: articlesC(id) }); settle(id, 'articles')
  })
  await page.route(/.*\/api\/topics\/(701|702|703)\/local-events$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/local-events$/)?.[1])
    request(id, 'local-events'); await route.fulfill({ json: localEventsC(id) }); settle(id, 'local-events')
  })
  await page.route(/.*\/api\/topics\/(701|702|703)\/event-graph$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/event-graph$/)?.[1])
    request(id, 'event-graph'); await route.fulfill({ json: eventGraphC(id) }); settle(id, 'event-graph')
  })
  await page.route(/.*\/api\/topics\/(701|702|703)\/academic$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/academic$/)?.[1])
    request(id, 'academic'); await route.fulfill({ json: academicC(id) }); settle(id, 'academic')
  })
  await page.route(/.*\/api\/topics\/(701|702|703)\/sentiment$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/sentiment$/)?.[1])
    request(id, 'sentiment'); await route.fulfill({ json: sentimentC(id) }); settle(id, 'sentiment')
  })
  await page.route(/.*\/api\/topics\/(701|702|703)\/cross-synthesis$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/cross-synthesis$/)?.[1])
    request(id, 'cross-synthesis'); await route.fulfill({ json: crossC(id) }); settle(id, 'cross-synthesis')
  })
  await page.route(/.*\/api\/topics\/(701|702|703)\/coverage.*/, async (route) => {
    await route.fulfill({ status: 404, json: { detail: 'not found' } })
  })

  return {
    // Upper-bound assertions read the REQUEST-time counter (bumped at handler entry):
    // a double-owner regression dispatches its duplicate synchronously with the primary
    // load, so requested lands before the primary settles → the ==N check catches it
    // deterministically (reading settled could miss a dispatched-but-unsettled duplicate).
    loads: (id: number) => requested[id],
    // Gates wait on SETTLED (response actually reached the browser), not mere dispatch.
    waitForResources: (id: number, resources: readonly ResourceKey[]) =>
      Promise.all(resources.map((r) => waitForSettled(id, r, 1))),
    waitForResourcesAfterBaseline: (id: number, resources: readonly ResourceKey[], baseline: Record<ResourceKey, number>) =>
      Promise.all(resources.map((r) => waitForSettled(id, r, baseline[r] + 1))),
  }
}

async function startSearch(page: Page, term: string) {
  await page.locator('input.event-input').fill(term)
  await page.locator('.search-action').getByRole('button').click()
}

// P0-T3: Search success + single owner. Search on A finishes to a NEW topic C(703);
// the selection watcher (not the finish path) owns C's loads; C's seven resources
// each load exactly once and the search terminal state survives the self-navigation.
test('Search success and single owner: C loads once each and terminal survives self-navigation', async ({ page }) => {
  const api = await mockLifecycleResources(page)
  await page.route('**/api/search/jobs', async (route) => {
    await route.fulfill({ json: {
      id: 'search-success-job', query: 'search C', status: 'queued',
      steps: [{ key: 'topic', label: 'topic', status: 'running' }],
      created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:00', result: null, error: '',
    } })
  })
  await page.route('**/api/search/jobs/search-success-job', async (route) => {
    await route.fulfill({ json: {
      id: 'search-success-job', query: 'search C', status: 'done',
      steps: [{ key: 'topic', label: 'topic', status: 'done' }],
      created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:01',
      result: {
        ...emptyLocalEvents,
        topic: lifecycleTopics[2],
        collect: {
          raw: 1, kept: 1, new_articles: 1, new_links: 1,
          requests: [{ id: 'r1', collector: 'rss', query: 'C-FRESH:search-terminal', raw_count: 1, kept_count: 1, status: 'ok' }],
          errors: [],
        },
        steps: [{ key: 'topic', label: 'topic', status: 'done' }],
      },
      error: '',
    } })
  })
  await openWorkbench(page)
  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()

  await startSearch(page, 'search C')

  // Self-navigation to C is performed by the selection watcher; terminal state persists.
  await expect(page.getByRole('heading', { name: 'Topic Gamma' })).toBeVisible()
  await expect(page.locator('.collect-diagnostics').getByText('C-FRESH:search-terminal')).toBeVisible()

  // The watcher (single owner) loads each of C's seven resources exactly once.
  await api.waitForResources(703, resourceKeys)
  // Quiescence margin (audit P0-T3): waitForResources resolves at the >=1 boundary, so
  // a late duplicate load could still be in flight when the ==1 check reads the counter.
  // Drain the browser event loop so any second-owner load (e.g. a finish-path duplicate)
  // would have dispatched + settled before the upper-bound assertion — proving "exactly
  // one ever", not merely "one at this instant".
  await drainBrowserEventLoop(page, 2)
  for (const resource of resourceKeys) expect(api.loads(703)[resource]).toBe(1)
})

// Helper for the round-trippable selection path. The contract's P0-T4 sequence
// "A → null/B → A" splits into two genuine-UI facts, each proven by its own test:
//  • The null cancellation boundary (contract invariant #5): reachable ONLY by DELETING
//    the selected topic (the dropdown's null <option> is `disabled`, App.vue:1285, so it
//    cannot be selected). After a delete you cannot round-trip back to the deleted topic,
//    so "A → null → A" is not a single drivable sequence. The null boundary is proven
//    separately by the dedicated delete-path test below ('null cancellation boundary…').
//  • The ABA lifecycle (S1 held continuation, active S2 survives): proven by P0-T4 via
//    the round-trippable A → B → A. Both halves of the frozen row are covered; neither
//    is downgraded (per human decision 2026-07-16 to split null into its own test).
async function selectTopic(page: Page, id: number) {
  const select = page.locator('select.topic-select')
  await select.selectOption(String(id))
  await expect(select).toHaveValue(String(id))
}

// P0-T4: Search ABA and stale finally. S1 finishes but its loadTopics continuation is
// held; the user moves A → B → A and starts S2. When S1 is released it must not write
// terminal/message/diagnostics, must not clear S2's busy/active state, and must not
// leave list-loading stuck. S2 completes normally.
test('Search ABA and stale finally: released S1 cannot write or clear active S2', async ({ page }) => {
  const api = await mockLifecycleResources(page)
  const s1LoadTopics = deferred()
  const s2Poll = deferred()
  let searchPostCount = 0
  let s1LoadTopicsArmed = false
  let s1LoadTopicsConsumed = false
  let s1LoadTopicsEntered: (() => void) | null = null
  const s1LoadTopicsHeld = new Promise<void>((resolve) => { s1LoadTopicsEntered = resolve })
  let s1Continued: (() => void) | null = null
  const s1Continuation = new Promise<void>((resolve) => { s1Continued = resolve })

  // Override /api/topics AFTER mockLifecycleResources (later route wins): hold exactly
  // S1's finish continuation (the first /api/topics after S1's search POST).
  await page.route('**/api/topics', async (route) => {
    if (s1LoadTopicsArmed && !s1LoadTopicsConsumed) {
      s1LoadTopicsConsumed = true
      s1LoadTopicsEntered?.()
      await s1LoadTopics.promise
      await route.fulfill({ json: lifecycleTopics })
      s1Continued?.()
      return
    }
    await route.fulfill({ json: lifecycleTopics })
  })
  await page.route('**/api/search/jobs', async (route) => {
    searchPostCount += 1
    if (searchPostCount === 1) {
      s1LoadTopicsArmed = true
      await route.fulfill({ json: {
        id: 's1job', query: 'S1', status: 'queued',
        steps: [{ key: 'topic', label: 'topic', status: 'running' }],
        created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:00', result: null, error: '',
      } })
      return
    }
    await route.fulfill({ json: {
      id: 's2active0', query: 'S2', status: 'queued',
      steps: [{ key: 'topic', label: 'topic', status: 'running' }],
      created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:00', result: null, error: '',
    } })
  })
  // S1 finishes done on its origin topic 701 with a distinguishable message + diagnostic.
  await page.route('**/api/search/jobs/s1job', async (route) => {
    await route.fulfill({ json: {
      id: 's1job', query: 'S1', status: 'done',
      steps: [{ key: 'topic', label: 'topic', status: 'done' }],
      created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:01',
      result: {
        ...emptyLocalEvents,
        topic: lifecycleTopics[0],
        collect: {
          raw: 101, kept: 102, new_articles: 103, new_links: 1,
          requests: [{ id: 'r1', collector: 'rss', query: 'S1-DIAGNOSTIC', raw_count: 101, kept_count: 102, status: 'ok' }],
          errors: [],
        },
        steps: [{ key: 'topic', label: 'topic', status: 'done' }],
      },
      error: '',
    } })
  })
  // S2 poll is held until finishS2(); the held poll keeps S2 active/searching.
  await page.route('**/api/search/jobs/s2active0', async (route) => {
    await s2Poll.promise
    await route.fulfill({ json: {
      id: 's2active0', query: 'S2', status: 'done',
      steps: [{ key: 'topic', label: 'topic', status: 'done' }],
      created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:02',
      result: {
        ...emptyLocalEvents,
        topic: lifecycleTopics[0],
        collect: {
          raw: 201, kept: 202, new_articles: 203, new_links: 1,
          requests: [{ id: 'r2', collector: 'rss', query: 'S2-DIAGNOSTIC', raw_count: 201, kept_count: 202, status: 'ok' }],
          errors: [],
        },
        steps: [{ key: 'topic', label: 'topic', status: 'done' }],
      },
      error: '',
    } })
  })

  await openWorkbench(page)
  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()

  const listLoading = page.locator('section.notice').filter({ hasText: '正在读取本地专题库...' })

  await startSearch(page, 'S1')
  await s1LoadTopicsHeld // S1 finished and is parked in loadTopics.

  // A → B → A (the round-trippable ABA; see selectTopic deviation note). Each switch
  // bumps the search-owner token, so S1's held continuation is stale when released.
  await selectTopic(page, 702)
  await expect(listLoading).toHaveCount(0) // switch is a cancellation boundary, not stuck-loading.
  await selectTopic(page, 701)

  await startSearch(page, 'S2') // S1 could not block S2 (busy flag released on switch).
  await expect(page.getByText('当前任务：s2active')).toBeVisible()
  await expect(page.locator('.search-action').getByRole('button', { name: '任务执行中...' })).toBeDisabled()

  // Arm the projects-continuation wait BEFORE releasing: S1's loadTopics does a second
  // hop (fetchTopics -> fetchProjects) before its stale-token return, so the /api/topics
  // fulfill alone does not prove S1's write path ran (audit P0-T4). Wait for BOTH hops.
  const s1ProjectsContinuation = page.waitForResponse('**/api/projects')
  s1LoadTopics.release()
  await s1Continuation // /api/topics fulfilled (hop 1)
  await s1ProjectsContinuation // /api/projects fetched (hop 2) — S1 is now at its token check
  // Drain twice: flush the topics .then -> fetchProjects dispatch, then the projects
  // .then -> token-check/write. Any BROKEN stale write is now committed to the DOM.
  await drainBrowserEventLoop(page, 2)

  // S1 must not write its terminal message/diagnostic, nor clear S2's active state.
  await expect(page.getByText('采集 101 条，保留 102 条，新增 103 篇。')).toHaveCount(0)
  await expect(page.getByText('S1-DIAGNOSTIC')).toHaveCount(0)
  await expect(listLoading).toHaveCount(0)
  await expect(page.getByText('当前任务：s2active')).toBeVisible()
  await expect(page.locator('.search-action').getByRole('button', { name: '任务执行中...' })).toBeDisabled()

  s2Poll.release()
  await expect(page.getByText('采集 201 条，保留 202 条，新增 203 篇。').first()).toBeVisible()
})

// P0-T4 (null leg): null cancellation boundary proven through the real delete path.
// Contract invariant #5: selectedTopicId = null is a cancellation boundary. Per the
// 2026-07-17 human/Codex decision (TO_CLAUDE): start S1 on selected A, hold ONLY S1's
// post-finish GET /api/topics continuation, then delete A through the project-manager
// UI (native confirm accepted) so the real removeTopic → loadTopics(undefined) path
// reaches selectedTopicId = null. This is the second subscenario of the SAME frozen
// P0-T4 row (the ABA half stays above); it is not a new P0 task. Mock isolation:
// only S1's finish continuation is held (armed at S1's POST, consumed on entry) — the
// delete refresh is a separate, later GET and is never held. S1's delayed continuation
// is served the WITH-A list on purpose: if any stale guard regressed, S1 would visibly
// resurrect A instead of passing silently. No Vue-ref mutation, no disabled-option
// force-selection.
test('null cancellation boundary: deleting selected A to null voids held S1 (no terminal, no resurrection)', async ({ page }) => {
  await mockLifecycleResources(page)
  const topicsWithoutA = lifecycleTopics.filter((topic) => topic.id !== 701)
  let aDeleted = false
  const projectsPayload = () => [
    {
      id: 11, name: 'Project One', description: 'p', status: 'active',
      archived_at: null, created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:00',
      topic_count: aDeleted ? topicsWithoutA.length : 2,
      topics: aDeleted ? topicsWithoutA : [lifecycleTopics[0], lifecycleTopics[1]],
    },
  ]

  // Project-manager data feed (overrides the fixture's empty default; later route wins).
  await page.route('**/api/projects', async (route) => {
    await route.fulfill({ json: projectsPayload() })
  })
  // Opening the project manager triggers loadSourceRegistry (watch(showProjectManager)).
  await page.route('**/api/sources', async (route) => { await route.fulfill({ json: [] }) })
  // The real DELETE endpoint used by removeTopic; flips the post-delete payloads.
  await page.route(/.*\/api\/topics\/701$/, async (route) => {
    if (route.request().method() === 'DELETE') {
      aDeleted = true
      await route.fulfill({ json: { deleted: true, topic_id: 701 } })
      return
    }
    await route.fallback()
  })

  // Hold ONLY S1's post-finish GET /api/topics continuation. The delete's own
  // loadTopics(undefined) fires a LATER /api/topics GET that must NOT be held.
  const s1LoadTopics = deferred()
  let s1Armed = false
  let s1Consumed = false
  let s1Entered: (() => void) | null = null
  const s1LoadTopicsHeld = new Promise<void>((resolve) => { s1Entered = resolve })
  let s1Continued: (() => void) | null = null
  const s1Continuation = new Promise<void>((resolve) => { s1Continued = resolve })
  await page.route('**/api/topics', async (route) => {
    if (s1Armed && !s1Consumed) {
      s1Consumed = true
      s1Entered?.()
      await s1LoadTopics.promise
      await route.fulfill({ json: lifecycleTopics }) // WITH-A list: a broken guard resurrects A visibly.
      s1Continued?.()
      return
    }
    await route.fulfill({ json: aDeleted ? topicsWithoutA : lifecycleTopics })
  })
  await page.route('**/api/search/jobs', async (route) => {
    s1Armed = true
    await route.fulfill({ json: {
      id: 's1job', query: 'S1', status: 'queued',
      steps: [{ key: 'topic', label: 'topic', status: 'running' }],
      created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:00', result: null, error: '',
    } })
  })
  await page.route('**/api/search/jobs/s1job', async (route) => {
    await route.fulfill({ json: {
      id: 's1job', query: 'S1', status: 'done',
      steps: [{ key: 'topic', label: 'topic', status: 'done' }],
      created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:01',
      result: {
        ...emptyLocalEvents,
        topic: lifecycleTopics[0],
        collect: {
          raw: 101, kept: 102, new_articles: 103, new_links: 1,
          requests: [{ id: 'r1', collector: 'rss', query: 'S1-DIAGNOSTIC', raw_count: 101, kept_count: 102, status: 'ok' }],
          errors: [],
        },
        steps: [{ key: 'topic', label: 'topic', status: 'done' }],
      },
      error: '',
    } })
  })

  await openWorkbench(page)
  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()

  const select = page.locator('select.topic-select')
  const listLoading = page.locator('section.notice').filter({ hasText: '正在读取本地专题库...' })

  await startSearch(page, 'S1')
  await s1LoadTopicsHeld // S1's finish is parked inside loadTopics BEFORE the delete.
  await expect(page.getByText('当前任务：s1job')).toBeVisible() // positive control: S1 is live.

  // Genuine UI path to null: project manager → 删除专题(A) → accept the native confirm.
  page.on('dialog', (dialog) => { void dialog.accept() })
  await page.getByRole('button', { name: '管理项目' }).click()
  const alphaRow = page.locator('.project-grid li').filter({ has: page.getByRole('button', { name: 'Topic Alpha' }) })
  await expect(alphaRow).toHaveCount(1)
  await alphaRow.getByRole('button', { name: '删除专题' }).click()

  // Null boundary reached. The empty-state notice is the SETTLED anchor FIRST: it only
  // renders once the delete's loadTopics has finished (loading released + no selected
  // topic), so the count-0 assertions after it cannot pass inside a transient loading
  // window (summary-band unmounts while loading — the transient false-green class).
  await expect(page.locator('section.notice').filter({ hasText: '还没有专题' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toHaveCount(0)
  await expect(alphaRow).toHaveCount(0)
  await expect(listLoading).toHaveCount(0)
  // NOTE: the placeholder <option :value="null"> has no value ATTRIBUTE, so the DOM
  // select.value falls back to the option's TEXT ("选择已有专题…") — the frozen plan's
  // '' assertion was unfulfillable; assert the selected INDEX instead (still "empty").
  await expect.poll(() => select.evaluate((el) => (el as HTMLSelectElement).selectedIndex)).toBe(0)

  // The null-time cancel ITSELF, asserted BEFORE releasing S1: busy/active state must
  // already be released at the boundary. Without the unconditional
  // cancelRunningJobs(null), '当前任务：s1job' would still be displayed and the search
  // button still busy here — the post-release backstops (topicsRequestId natural bump
  // by the delete's own loadTopics, finishSearchJob's selectedTopicId fallback) would
  // mask that. (Mutation-probe anchor; verified RED when null-cancel is removed.)
  await expect(page.getByText('当前任务：s1job')).toHaveCount(0)
  await expect(page.locator('.search-action').getByRole('button', { name: '搜集并生成时间轴' })).toBeEnabled()

  // Release S1 and wait for its browser-side continuation (topics fulfill → projects
  // fetch → stale token check / owner-token check / finally). route.fulfill alone is
  // not proof the continuation ran (per the 2026-07-17 decision).
  const s1ProjectsContinuation = page.waitForResponse('**/api/projects')
  s1LoadTopics.release()
  await s1Continuation
  await s1ProjectsContinuation
  // Drain twice: flush the topics .then → fetchProjects dispatch, then the projects
  // .then → token-check/write/finally. Any BROKEN stale write is now committed to the DOM.
  await drainBrowserEventLoop(page, 2)

  // S1 writes no terminal message / diagnostic / error / active-job state…
  await expect(page.getByText('采集 101 条，保留 102 条，新增 103 篇。')).toHaveCount(0)
  await expect(page.getByText('S1-DIAGNOSTIC')).toHaveCount(0)
  await expect(page.locator('section.notice.error')).toHaveCount(0)
  await expect(page.getByText('当前任务：s1job')).toHaveCount(0)
  // …and cannot resurrect A or the selection: the null state persists.
  await expect.poll(() => select.evaluate((el) => (el as HTMLSelectElement).selectedIndex)).toBe(0)
  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toHaveCount(0)
  await expect(alphaRow).toHaveCount(0)
  await expect(listLoading).toHaveCount(0)
})

function deepResult(id: number, processed: number, inputArticles: number, timeline: number) {
  return {
    topic_id: id, topic_name: letterOf[id],
    enrich: { limit: 30, pending: 0, processed, relevant: processed, batches: 1, calls: 1, errors: [] },
    synthesize: { input_articles: inputArticles, timeline, framing: 0, analysis_chars: 100, calls: 1 },
    timeline: [], framing: [], analysis_md: 'analysis',
  }
}

function queuedJob(id: string, key: string) {
  return {
    id, query: id, status: 'queued',
    steps: [{ key, label: key, status: 'running' }],
    created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:00', result: null, error: '',
  }
}
function doneJob(id: string, key: string, result: unknown) {
  return {
    id, query: id, status: 'done',
    steps: [{ key, label: key, status: 'done' }],
    created_at: '2026-07-04T00:00:00', updated_at: '2026-07-04T00:00:01', result, error: '',
  }
}

async function startDeep(page: Page) {
  // No pure-deep UI path exists: both deep buttons invoke runLlmAnalysisBundle
  // (App.vue:1655 and LlmPanel.vue:33 → App.vue:1969). Driving the real bundle is a
  // stronger lifecycle test than a synthetic pure-deep call. Click the LLM tab, then
  // the LlmPanel deep button ('深度分析（LLM）', distinct from App.vue's longer label).
  await page.locator('nav.workspace-tabs').getByRole('button', { name: 'LLM 深度分析', exact: true }).click()
  await page.getByRole('button', { name: '深度分析（LLM）' }).click()
}

// P0-T5: Deep full-lifecycle ownership. DEVIATION (documented): the deep button runs
// the LLM bundle (deep+academic+sentiment, then cross), so the fixture mocks the whole
// bundle for both topics; only each topic's DEEP poll is independently controllable.
// Hold A's deep poll, switch to B, start B's deep, release A: A's superseded finish must
// not write A's message or clear B; B completes and B's topic/articles/local-events each
// advance exactly +1 from the post-switch settled baseline.
test('Deep full-lifecycle ownership: released A deep cannot write or clear active B', async ({ page }) => {
  const api = await mockLifecycleResources(page)
  const aDeepPoll = deferred()
  const bDeepPoll = deferred()
  let aDeepEntered: (() => void) | null = null
  const aDeepHeld = new Promise<void>((resolve) => { aDeepEntered = resolve })

  // Job POSTs for the full bundle on both topics.
  await page.route('**/api/topics/701/deep-analysis/jobs', async (route) => route.fulfill({ json: queuedJob('adeepjob0', 'enrich') }))
  await page.route('**/api/topics/701/academic/jobs', async (route) => route.fulfill({ json: queuedJob('aacadjob0', 'fetch') }))
  await page.route('**/api/topics/701/sentiment/jobs', async (route) => route.fulfill({ json: queuedJob('asentjob0', 'fetch') }))
  await page.route('**/api/topics/701/cross-synthesis/jobs', async (route) => route.fulfill({ json: queuedJob('acrossjob0', 'gather') }))
  await page.route('**/api/topics/702/deep-analysis/jobs', async (route) => route.fulfill({ json: queuedJob('bdeepact0', 'enrich') }))
  await page.route('**/api/topics/702/academic/jobs', async (route) => route.fulfill({ json: queuedJob('bacadjob0', 'fetch') }))
  await page.route('**/api/topics/702/sentiment/jobs', async (route) => route.fulfill({ json: queuedJob('bsentjob0', 'fetch') }))
  await page.route('**/api/topics/702/cross-synthesis/jobs', async (route) => route.fulfill({ json: queuedJob('bcrossjob0', 'gather') }))

  // Unified poll route: dispatch on job id. Deep polls are held; others resolve done.
  await page.route(/.*\/api\/search\/jobs\/([a-z0-9]+)$/, async (route) => {
    const jobId = route.request().url().match(/\/search\/jobs\/([a-z0-9]+)$/)?.[1] || ''
    if (jobId === 'adeepjob0') {
      aDeepEntered?.()
      await aDeepPoll.promise
      await route.fulfill({ json: doneJob('adeepjob0', 'enrich', deepResult(701, 101, 102, 103)) })
      return
    }
    if (jobId === 'bdeepact0') {
      await bDeepPoll.promise
      await route.fulfill({ json: doneJob('bdeepact0', 'enrich', deepResult(702, 201, 202, 203)) })
      return
    }
    if (jobId === 'aacadjob0') return route.fulfill({ json: doneJob(jobId, 'fetch', academicC(701)) })
    if (jobId === 'bacadjob0') return route.fulfill({ json: doneJob(jobId, 'fetch', academicC(702)) })
    if (jobId === 'asentjob0') return route.fulfill({ json: doneJob(jobId, 'fetch', sentimentC(701)) })
    if (jobId === 'bsentjob0') return route.fulfill({ json: doneJob(jobId, 'fetch', sentimentC(702)) })
    if (jobId === 'acrossjob0') return route.fulfill({ json: doneJob(jobId, 'gather', crossC(701)) })
    if (jobId === 'bcrossjob0') return route.fulfill({ json: doneJob(jobId, 'gather', crossC(702)) })
    await route.fulfill({ json: doneJob(jobId, 'fetch', {}) })
  })

  await openWorkbench(page)
  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()

  await startDeep(page) // bundle on A; deep poll held
  await aDeepHeld

  await selectTopic(page, 702) // switch to B: cancels A's in-flight generation
  await api.waitForResources(702, ['topic', 'articles', 'local-events'])
  const baseline = { ...api.loads(702) }

  await startDeep(page) // bundle on B
  await expect(page.getByText('深度任务：bdeepact').first()).toBeVisible()

  // Browser-confirmed receipt anchor (audit P0-T5 fix): waitForResponse on A's deep poll
  // URL fires only when the browser RECEIVED the response — a happens-before edge to A's
  // poll .then continuation (the Node-side aDeepContinuation signal does not prove receipt).
  const aDeepReceived = page.waitForResponse('**/api/search/jobs/adeepjob0')
  aDeepPoll.release()
  await aDeepReceived
  // Drain TWICE (matches the sibling P0-T4 pattern): waitForResponse proves network
  // RECEIPT, which queues the XHR onload macrotask but does not prove the browser ran
  // A's poll continuation. Two setTimeout(0) boundaries guarantee any macrotask queued
  // at/before the first boundary (the onload, queued at receipt) has run before the
  // second — so A's fetch .then → isCurrent guard → any broken finish writing deepMessage
  // synchronously → Vue flush is fully committed before the absence check (audit P0-T5).
  await drainBrowserEventLoop(page, 2)

  // A's superseded finish must not write A's message, and B stays active.
  await expect(page.getByText('LLM 深度分析完成：富化 101 篇，综合 102 篇，生成 103 个节点。')).toHaveCount(0)
  await expect(page.getByText('深度任务：bdeepact').first()).toBeVisible()

  bDeepPoll.release()
  // B completes with its own distinguishable message.
  await expect(page.getByText('LLM 深度分析完成：富化 201 篇，综合 202 篇，生成 203 个节点。').first()).toBeVisible()

  // B's post-deep topic/articles/local-events each advance exactly +1 from the baseline.
  await api.waitForResourcesAfterBaseline(702, ['topic', 'articles', 'local-events'], baseline)
  for (const resource of ['topic', 'articles', 'local-events'] as const) {
    expect(api.loads(702)[resource]).toBe(baseline[resource] + 1)
  }
})
