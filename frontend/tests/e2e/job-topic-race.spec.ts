import { expect, type Page, test } from '@playwright/test'

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
  let releaseAcademicJob: (() => void) | null = null
  let releaseSentimentJob: (() => void) | null = null
  let releaseCrossJob: (() => void) | null = null

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
  })
  await page.route(/.*\/api\/topics\/(701|702)\/sentiment$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/sentiment$/)?.[1])
    if (id === 701) alphaSentimentLoads += 1
    if (id === 702) betaSentimentLoads += 1
    await route.fulfill({ json: sentimentLayer(id) })
  })
  await page.route('**/api/integrations/opencli/diagnostics', async (route) => {
    await route.fulfill({ json: { ok: true, command: 'opencli', resolved: 'opencli', message: '', recommended_command: '' } })
  })
  await page.route(/.*\/api\/topics\/(701|702)\/cross-synthesis$/, async (route) => {
    const id = Number(route.request().url().match(/\/topics\/(\d+)\/cross-synthesis$/)?.[1])
    if (id === 701) alphaCrossLoads += 1
    if (id === 702) betaCrossLoads += 1
    await route.fulfill({ json: crossLayer(id) })
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
    await new Promise<void>((resolve) => {
      releaseAcademicJob = resolve
    })
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
    await new Promise<void>((resolve) => {
      releaseSentimentJob = resolve
    })
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
    await new Promise<void>((resolve) => {
      releaseCrossJob = resolve
    })
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
    releaseAcademicJob: () => releaseAcademicJob?.(),
    releaseSentimentJob: () => releaseSentimentJob?.(),
    releaseCrossJob: () => releaseCrossJob?.(),
  }
}

test('does not load a finished academic job into a newly selected topic', async ({ page }) => {
  const api = await mockRaceApi(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()
  await page.getByRole('button', { name: '学界视角' }).click()
  await expect(page.getByText(/学界任务：academic/)).toBeVisible()

  await page.getByLabel('选择专题').selectOption('702')
  await expect(page.getByRole('heading', { name: 'Topic Beta' })).toBeVisible()
  const betaLoadsAfterSwitch = api.betaAcademicLoads()

  api.releaseAcademicJob()
  await expect(page.getByText('学界任务已完成；你已切换专题，当前页未自动刷新。')).toBeVisible()

  expect(api.alphaAcademicLoads()).toBeGreaterThan(0)
  expect(api.betaAcademicLoads()).toBe(betaLoadsAfterSwitch)
})

test('does not load a finished sentiment job into a newly selected topic', async ({ page }) => {
  const api = await mockRaceApi(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()
  await page.locator('.deep-actions').getByRole('button', { name: '民间情绪' }).click()
  await expect(page.getByText(/民间情绪任务：sentimen/)).toBeVisible()

  await page.getByLabel('选择专题').selectOption('702')
  await expect(page.getByRole('heading', { name: 'Topic Beta' })).toBeVisible()
  const betaLoadsAfterSwitch = api.betaSentimentLoads()

  api.releaseSentimentJob()
  await expect(page.getByText('民间情绪任务已完成；你已切换专题，当前页未自动刷新。')).toBeVisible()

  expect(api.alphaSentimentLoads()).toBeGreaterThan(0)
  expect(api.betaSentimentLoads()).toBe(betaLoadsAfterSwitch)
})

test('does not load a finished cross-synthesis job into a newly selected topic', async ({ page }) => {
  const api = await mockRaceApi(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Topic Alpha' })).toBeVisible()
  await page.locator('.deep-actions').getByRole('button', { name: /^三方对照$/ }).click()
  await expect(page.getByText(/三方对照任务：cross-r/)).toBeVisible()

  await page.getByLabel('选择专题').selectOption('702')
  await expect(page.getByRole('heading', { name: 'Topic Beta' })).toBeVisible()
  const betaLoadsAfterSwitch = api.betaCrossLoads()

  api.releaseCrossJob()
  await expect(page.getByText('三方对照任务已完成；你已切换专题，当前页未自动刷新。')).toBeVisible()

  expect(api.alphaCrossLoads()).toBeGreaterThan(0)
  expect(api.betaCrossLoads()).toBe(betaLoadsAfterSwitch)
})
