import { expect, type Page, test } from '@playwright/test'
import { openWorkbench } from './helpers'

// Drain the browser event loop. A late response that production correctly discards
// commits nothing, so there is no positive DOM signal to await; instead we force a
// macrotask boundary (setTimeout 0) which flushes all pending microtasks — the fetch
// .then continuation, the awaited loader resumption — plus Vue's reactive DOM flush.
// After this, any BROKEN late-write has already committed to the DOM, so a subsequent
// toHaveCount(0) (which passes on first satisfaction and never re-checks) is meaningful.
async function drainBrowserEventLoop(page: Page) {
  await page.evaluate(() => new Promise<void>((r) => setTimeout(r, 0)))
}

// RM-065 P0 (frozen contract p0-topic-load-race-test-contract-2026-07-16):
// all seven topic-scoped async loads must remain owned by the newly selected
// topic after an intentionally delayed old-topic request, with at most one
// effective load per resource. Prior rounds used indistinguishable fixtures
// (identical A/B payloads, only articles held), so counting requests alone
// produced false greens. This fixture holds every A endpoint behind an
// independent barrier and gives each an observable, distinguishable marker.

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
  let resolve!: () => void
  const promise = new Promise<void>((done) => { resolve = done })
  return { promise, release: () => resolve() }
}

// Distinguishable marker per (topic, freshness, resource). A wrong late overwrite
// surfaces the stale marker on the rendered surface; a missing owner surfaces the
// absence. Counting requests alone can never produce these markers.
function marker(topic: 'A' | 'B' | 'C', freshness: 'STALE' | 'FRESH', resource: ResourceKey) {
  return `${topic}-${freshness}:${resource}`
}

const topics = [
  {
    id: 801, name: 'Topic Alpha', description: 'first topic', queries: ['alpha'],
    status: 'active', created_at: '2026-07-04T00:00:00',
    article_count: 1, source_count: 1, enriched_count: 0, relevant_count: 1,
    latest_published_at: '2026-07-03T08:00:00',
  },
  {
    id: 802, name: 'Topic Beta', description: 'second topic', queries: ['beta'],
    status: 'active', created_at: '2026-07-04T00:00:00',
    article_count: 1, source_count: 1, enriched_count: 0, relevant_count: 1,
    latest_published_at: '2026-07-03T08:00:00',
  },
]

// topicOf maps a topic id to its marker letter. 801=A, 802=B.
function topicOf(id: number): 'A' | 'B' {
  return id === 801 ? 'A' : 'B'
}

// ---- marker-bearing payload builders (valid existing DTO shapes) ----

// topic marker lives in analysis.content_md, rendered in the LLM panel.
// GUARD: content_md must NOT contain the '<!-- analysis-source: llm -->' sentinel,
// or hasLlmAnalysis flips true and majorEvents abandons localData.events for
// detail.timeline — the local-events marker would then silently vanish.
function topicDetail(id: number, freshness: 'STALE' | 'FRESH') {
  const topic = topics.find((item) => item.id === id) || topics[0]
  return {
    ...topic,
    timeline: [],
    framing: [],
    analysis: { id: id * 1000, generated_at: '2026-07-04T00:00:00', content_md: marker(topicOf(id), freshness, 'topic') },
  }
}

// articles marker lives on items[0].title; title_zh MUST be empty so titleFor
// falls back to title (titleFor prefers title_zh).
function articlesFor(id: number, freshness: 'STALE' | 'FRESH') {
  return {
    total: 1,
    items: [
      {
        id: id * 10 + (freshness === 'STALE' ? 1 : 0),
        url: `https://example.com/${topicOf(id).toLowerCase()}/${freshness.toLowerCase()}`,
        title: marker(topicOf(id), freshness, 'articles'),
        title_zh: '',
        source: `${topicOf(id)} Wire`,
        source_lang: 'en',
        collector: 'rss',
        category: '行动进展',
        published_at: '2026-07-03T08:00:00',
        relevance: 0.9,
      },
    ],
  }
}

const emptyLocalEvents = {
  events: [], framing: [], analysis_md: '', stance_evolution: [],
  keywords: [], entities: [], entity_groups: [], criteria: [],
}

// local-events marker lives on events[0].title_zh, rendered in the media timeline.
function localEventsFor(id: number, freshness: 'STALE' | 'FRESH') {
  return {
    ...emptyLocalEvents,
    events: [
      {
        id: id * 100 + (freshness === 'STALE' ? 1 : 0),
        date: '2026-07-03',
        title_zh: marker(topicOf(id), freshness, 'local-events'),
        summary_zh: `${topicOf(id)} local event summary`,
        article_ids: [id * 10],
        score: 1, source_count: 1, article_count: 1, stance: '综合判断',
      },
    ],
  }
}

// event-graph marker lives on nodes[0].title_zh; the graph node button carries
// aria-label `事件 1：<marker>` (visible SVG text is truncated — target the label).
function eventGraphFor(id: number, freshness: 'STALE' | 'FRESH') {
  return {
    nodes: [
      {
        id: id * 10, date: '2026-07-03',
        title_zh: marker(topicOf(id), freshness, 'event-graph'),
        summary_zh: `${topicOf(id)} graph node`,
        source_count: 1, article_count: 1, article_ids: [id * 10],
      },
    ],
    edges: [],
    degraded: false,
    note: '',
  }
}

// academic marker lives on papers[0].title, rendered as a link in the academic panel.
function academicFor(id: number, freshness: 'STALE' | 'FRESH') {
  return {
    topic_id: id, topic_name: '',
    papers: [
      {
        openalex_id: `W${id}`,
        title: marker(topicOf(id), freshness, 'academic'),
        year: 2026, cited_by_count: 0, authors: ['Author'], venue: 'Venue',
      },
    ],
    graph: { nodes: [], edges: [] },
    schools: [], foundational_papers: [], summary_md: '',
  }
}

// sentiment marker lives on posts[0].title; kind must NOT be 'comment' (comments
// are filtered out of sentimentPostItems and only render in a nested details).
function sentimentFor(id: number, freshness: 'STALE' | 'FRESH') {
  return {
    topic_id: id, topic_name: '', platform: 'multi', warning: '',
    posts: [
      {
        id: `${id}-post`, platform: 'reddit', kind: 'post', subreddit: 'r/x',
        title: marker(topicOf(id), freshness, 'sentiment'),
        author: 'u/x', score: 1, num_comments: 0,
        url: `https://example.com/${topicOf(id).toLowerCase()}/post`,
        created_utc: '2026-07-03T08:00:00', selftext_snippet: 'snippet',
      },
    ],
    summary_md: '',
  }
}

// cross-synthesis marker lives in content_md, rendered as markdown in the cross panel.
function crossFor(id: number, freshness: 'STALE' | 'FRESH') {
  return {
    topic_id: id, topic_name: '',
    content_md: marker(topicOf(id), freshness, 'cross-synthesis'),
    voices_used: ['media'], generated_at: '2026-07-04T00:00:00',
  }
}

const builders: Record<ResourceKey, (id: number, freshness: 'STALE' | 'FRESH') => unknown> = {
  'topic': topicDetail,
  'articles': articlesFor,
  'local-events': localEventsFor,
  'event-graph': eventGraphFor,
  'academic': academicFor,
  'sentiment': sentimentFor,
  'cross-synthesis': crossFor,
}

type MockOpts = {
  // Hold every listed A resource behind its own barrier (P0-T1).
  holdAlphaResources?: ResourceKey[]
  // Hold only the FIRST A articles request (P0-T2 ABA); later A requests run fresh.
  holdFirstAlphaArticles?: boolean
}

async function mockTopicApi(page: Page, opts: MockOpts = {}) {
  const held = new Set(opts.holdAlphaResources || [])
  const barriers = new Map<ResourceKey, ReturnType<typeof deferred>>()
  for (const resource of held) barriers.set(resource, deferred())

  // First-A-articles ABA barrier (independent of the seven-resource holds).
  const firstArticlesBarrier = opts.holdFirstAlphaArticles ? deferred() : null
  let firstArticlesHeld = false
  // Track the STALE first-A response settling SEPARATELY from the generic articles
  // counter: the fresh return-to-A leg pre-satisfies settled[801].articles=1, so a
  // count-based waiter would short-circuit before the stale response is even sent
  // (the audit's P0-T2 Critical false-green). This deferred resolves ONLY after the
  // held stale response has been fulfilled to the browser.
  const firstArticlesStaleSettled = deferred()

  // entered[resource] resolves once that A route has reached its barrier.
  const enteredSignals = new Map<ResourceKey, ReturnType<typeof deferred>>()
  for (const resource of held) enteredSignals.set(resource, deferred())
  const firstArticlesEntered = deferred()

  // requests[id][resource] counts requests; settled[id][resource] counts responses.
  const zero = (): Record<ResourceKey, number> => ({
    topic: 0, articles: 0, 'local-events': 0, 'event-graph': 0, academic: 0, sentiment: 0, 'cross-synthesis': 0,
  })
  const requests: Record<number, Record<ResourceKey, number>> = { 801: zero(), 802: zero() }
  const settled: Record<number, Record<ResourceKey, number>> = { 801: zero(), 802: zero() }
  const settleWaiters: Array<{ id: number; resource: ResourceKey; count: number; release: () => void }> = []

  function bumpSettled(id: number, resource: ResourceKey) {
    if (!settled[id]) return
    settled[id][resource] += 1
    for (const w of settleWaiters) {
      if (w.id === id && w.resource === resource && settled[id][resource] >= w.count) w.release()
    }
  }

  function waitForSettledCount(id: number, resource: ResourceKey, count: number) {
    if (settled[id] && settled[id][resource] >= count) return Promise.resolve()
    const d = deferred()
    settleWaiters.push({ id, resource, count, release: d.release })
    return d.promise
  }

  async function fulfill(route: import('@playwright/test').Route, id: number, resource: ResourceKey, freshness: 'STALE' | 'FRESH') {
    await route.fulfill({ json: builders[resource](id, freshness) as object })
    bumpSettled(id, resource)
  }

  // A held A resource enters its barrier (signalling entry), waits, then fulfills STALE.
  async function routeResource(route: import('@playwright/test').Route, id: number, resource: ResourceKey) {
    if (requests[id]) requests[id][resource] += 1
    if (id === 801 && held.has(resource)) {
      enteredSignals.get(resource)?.release()
      await barriers.get(resource)!.promise
      await fulfill(route, id, resource, 'STALE')
      return
    }
    await fulfill(route, id, resource, 'FRESH')
  }

  await page.route('**/api/topics', async (route) => route.fulfill({ json: topics }))
  await page.route('**/api/projects', async (route) => route.fulfill({ json: [] }))
  await page.route('**/api/integrations/opencli/diagnostics', async (route) =>
    route.fulfill({ json: { ok: true, command: 'opencli', resolved: 'opencli', message: '', recommended_command: '' } }),
  )
  await page.route(/.*\/api\/topics\/(801|802)\/coverage.*/, async (route) =>
    route.fulfill({ status: 404, json: { detail: 'not found' } }),
  )

  await page.route(/.*\/api\/topics\/(801|802)$/, async (route) => {
    const id = Number(route.request().url().split('/').pop())
    await routeResource(route, id, 'topic')
  })
  await page.route(/.*\/api\/topics\/(801|802)\/articles.*/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/articles/)?.[1])
    if (requests[id]) requests[id].articles += 1
    // First-A-articles ABA hold: only the very first A request is held (stale);
    // subsequent A requests (the return-to-A leg) resolve fresh.
    if (id === 801 && firstArticlesBarrier && !firstArticlesHeld) {
      firstArticlesHeld = true
      firstArticlesEntered.release()
      await firstArticlesBarrier.promise
      await fulfill(route, id, 'articles', 'STALE')
      firstArticlesStaleSettled.release() // signals the STALE response reached the browser
      return
    }
    // Seven-resource hold path (P0-T1) reuses routeResource semantics.
    if (id === 801 && held.has('articles')) {
      enteredSignals.get('articles')?.release()
      await barriers.get('articles')!.promise
      await fulfill(route, id, 'articles', 'STALE')
      return
    }
    await fulfill(route, id, 'articles', 'FRESH')
  })
  await page.route(/.*\/api\/topics\/(801|802)\/local-events$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/local-events$/)?.[1])
    await routeResource(route, id, 'local-events')
  })
  await page.route(/.*\/api\/topics\/(801|802)\/event-graph$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/event-graph$/)?.[1])
    await routeResource(route, id, 'event-graph')
  })
  await page.route(/.*\/api\/topics\/(801|802)\/academic$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/academic$/)?.[1])
    await routeResource(route, id, 'academic')
  })
  await page.route(/.*\/api\/topics\/(801|802)\/sentiment$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/sentiment$/)?.[1])
    await routeResource(route, id, 'sentiment')
  })
  await page.route(/.*\/api\/topics\/(801|802)\/cross-synthesis$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/cross-synthesis$/)?.[1])
    await routeResource(route, id, 'cross-synthesis')
  })

  // ---- render-surface helpers (verified locators; only the active tab mounts) ----

  async function openDetails(page: Page, selector: string) {
    const details = page.locator(selector)
    if (await details.count()) {
      const open = await details.evaluate((el) => (el as HTMLDetailsElement).open).catch(() => true)
      if (!open) await details.locator('summary').first().click()
    }
  }

  async function gotoResourceSurface(page: Page, resource: ResourceKey) {
    const nav = page.locator('nav.workspace-tabs')
    const tab = (name: string) => nav.getByRole('button', { name, exact: true }).click()
    if (resource === 'topic') await tab('LLM 深度分析')
    else if (resource === 'academic') await tab('学界')
    else if (resource === 'sentiment') await tab('民间情绪')
    else if (resource === 'cross-synthesis') await tab('三方对照')
    else {
      await tab('媒体')
      if (resource === 'articles') await openDetails(page, 'details.article-feed-collapse')
      if (resource === 'event-graph') await openDetails(page, 'details.event-network-panel')
    }
  }

  function markerLocator(page: Page, resource: ResourceKey, text: string) {
    if (resource === 'event-graph') return page.getByRole('button', { name: `事件 1：${text}` })
    if (resource === 'articles' || resource === 'academic' || resource === 'sentiment') {
      return page.getByRole('link', { name: text })
    }
    return page.getByText(text)
  }

  async function expectRenderedMarkers(page: Page, topic: 'A' | 'B' | 'C', freshness: 'STALE' | 'FRESH', list: readonly ResourceKey[]) {
    for (const resource of list) {
      await gotoResourceSurface(page, resource)
      await expect(markerLocator(page, resource, marker(topic, freshness, resource)).first()).toBeVisible()
    }
    await page.locator('nav.workspace-tabs').getByRole('button', { name: '媒体', exact: true }).click()
  }

  async function expectMarkersAbsent(page: Page, topic: 'A' | 'B' | 'C', freshness: 'STALE' | 'FRESH', list: readonly ResourceKey[]) {
    // A discarded late response commits nothing by design, so drain the event loop to
    // let any BROKEN late-write reach the DOM before the (first-satisfaction) absence check.
    await drainBrowserEventLoop(page)
    for (const resource of list) {
      await gotoResourceSurface(page, resource)
      await expect(markerLocator(page, resource, marker(topic, freshness, resource))).toHaveCount(0)
    }
    await page.locator('nav.workspace-tabs').getByRole('button', { name: '媒体', exact: true }).click()
  }

  return {
    loads: (id: number) => requests[id],
    releaseAlpha: (resource: ResourceKey) => barriers.get(resource)?.release(),
    releaseAllAlpha: () => { for (const b of barriers.values()) b.release() },
    releaseFirstAlphaArticles: () => firstArticlesBarrier?.release(),
    waitUntilAllAlphaResourcesAreHeld: () => Promise.all([...enteredSignals.values()].map((s) => s.promise)),
    waitUntilFirstAlphaArticlesIsHeld: () => firstArticlesEntered.promise,
    waitForAllAlphaResponses: () => Promise.all([...held].map((r) => waitForSettledCount(801, r, 1))),
    // Resolves only after the STALE first-A response reached the browser (not the fresh
    // return-to-A leg that pre-satisfies the generic counter — audit P0-T2 fix).
    waitForFirstAlphaArticlesResponse: () => firstArticlesStaleSettled.promise,
    expectRenderedMarkers,
    expectMarkersAbsent,
  }
}

// P0-T1: seven-resource delayed ownership.
test('seven delayed A resources never overwrite B and B owns each resource once', async ({ page }) => {
  const api = await mockTopicApi(page, { holdAlphaResources: resourceKeys })
  await openWorkbench(page)
  // Prove every A endpoint has started and is blocked at its own barrier.
  await api.waitUntilAllAlphaResourcesAreHeld()

  // Select B while all seven A resources are held in flight.
  await page.getByLabel('选择专题').selectOption('802')
  await expect(page.getByRole('heading', { name: 'Topic Beta' })).toBeVisible()
  // Every B resource renders its FRESH marker (B is not blocked behind A).
  await api.expectRenderedMarkers(page, 'B', 'FRESH', resourceKeys)

  // Release all A barriers; the stale A responses must be discarded, not committed under B.
  api.releaseAllAlpha()
  await api.waitForAllAlphaResponses()

  // B still owns every surface; no A-STALE marker ever lands.
  await api.expectRenderedMarkers(page, 'B', 'FRESH', resourceKeys)
  await api.expectMarkersAbsent(page, 'A', 'STALE', resourceKeys)
  // Single owner: each B resource loaded exactly once (watch is the sole loader).
  for (const resource of resourceKeys) expect(api.loads(802)[resource]).toBe(1)
})

// P0-T2: generic loader ABA — freshness cannot be inferred from topic id alone.
test('an A->B->A article sequence discards the stale first-A response (no ABA)', async ({ page }) => {
  const api = await mockTopicApi(page, { holdFirstAlphaArticles: true })
  await openWorkbench(page)
  await api.waitUntilFirstAlphaArticlesIsHeld()

  // A(held) -> B -> A. The second Alpha selection issues a fresh (unheld) request.
  await page.getByLabel('选择专题').selectOption('802')
  await expect(page.getByRole('heading', { name: 'Topic Beta' })).toBeVisible()
  await page.getByLabel('选择专题').selectOption('801')
  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()
  await expect(page.getByText(marker('A', 'FRESH', 'articles'))).toHaveCount(1)

  // Release the stale first-A response. The monotonic generation must discard it —
  // not accept it just because the id equals Alpha again (ABA).
  // Browser-confirmed receipt anchor (audit P0-T2 fix): waitForResponse fires only when
  // the browser has RECEIVED the stale response — establishing a happens-before edge to
  // the XHR onload task (a Node-side route.fulfill signal does not). The body predicate
  // matches the STALE marker so it cannot resolve on the fresh return-to-A leg (same URL).
  // Then drain the event loop so a BROKEN clobber would commit to the DOM before the
  // absence assertion runs.
  const staleReceived = page.waitForResponse(async (res) =>
    /\/api\/topics\/801\/articles/.test(res.url()) && (await res.text()).includes(marker('A', 'STALE', 'articles')),
  )
  api.releaseFirstAlphaArticles()
  await staleReceived
  await drainBrowserEventLoop(page)

  await expect(page.getByText(marker('A', 'FRESH', 'articles'))).toHaveCount(1)
  await expect(page.getByText(marker('A', 'STALE', 'articles'))).toHaveCount(0)
  await expect(page.getByText(marker('B', 'FRESH', 'articles'))).toHaveCount(0)
})
