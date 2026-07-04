import { expect, type Page, test } from '@playwright/test'

const topic = {
  id: 101,
  project_id: 201,
  project_name: 'Source Ops',
  name: 'Ukraine frontline',
  description: '',
  queries: ['Ukraine frontline'],
  status: 'active',
  archived_at: null,
  created_at: '2026-07-03T00:00:00',
  updated_at: '2026-07-03T00:00:00',
  article_count: 3,
  source_count: 2,
  enriched_count: 0,
  relevant_count: 3,
  latest_published_at: '2026-07-03T09:00:00',
}

const project = {
  id: 201,
  name: 'Source Ops',
  description: '',
  status: 'active',
  archived_at: null,
  created_at: '2026-07-03T00:00:00',
  updated_at: '2026-07-03T00:00:00',
  topic_count: 1,
  topics: [topic],
}

const source = {
  id: 1,
  name: 'Reuters',
  url: 'https://example.com/reuters.xml',
  country: 'United Kingdom',
  language: 'en',
  source_type: 'rss',
  quality_tier: 'wire',
  requires_login: false,
  fulltext_support: false,
  enabled: true,
  last_status: 'ok',
  last_error: '',
  last_fetched_at: '2026-07-03T08:00:00',
  article_count: 12,
  notes: '',
  created_at: '2026-07-03T00:00:00',
  updated_at: '2026-07-03T08:00:00',
}

const failedSource = {
  ...source,
  id: 5,
  name: 'Bellingcat Monitor',
  url: 'https://example.com/bellingcat.xml',
  country: 'Netherlands',
  quality_tier: 'professional',
  enabled: false,
  last_status: 'failed',
  last_error: 'HTTP 403 blocked',
  last_fetched_at: null,
  article_count: 0,
}

async function mockApi(page: Page) {
  let patchedSource: any = null
  let createdSourcePayload: any = null
  let importedSourcePayload: any = null
  let sourceRows = [source, failedSource]
  await page.route('**/api/projects', async (route) => {
    await route.fulfill({ json: [project] })
  })
  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: [topic] })
  })
  await page.route('**/api/topics/101', async (route) => {
    await route.fulfill({ json: { ...topic, timeline: [], framing: [], analysis: null } })
  })
  await page.route('**/api/topics/101/articles**', async (route) => {
    await route.fulfill({ json: { total: 0, items: [] } })
  })
  await page.route('**/api/topics/101/local-events', async (route) => {
    await route.fulfill({
      json: {
        events: [],
        framing: [],
        analysis_md: '',
        stance_evolution: [],
        keywords: [],
        entities: [],
        entity_groups: [],
        criteria: [],
      },
    })
  })
  await page.route('**/api/topics/101/cross-synthesis', async (route) => {
    await route.fulfill({ json: { topic_id: 101, voices_used: [], content_md: '', generated_at: null } })
  })
  await page.route('**/api/topics/101/academic', async (route) => {
    await route.fulfill({ json: { topic_id: 101, papers: [], schools: [], citation_edges: [], summary_md: '' } })
  })
  await page.route('**/api/topics/101/sentiment', async (route) => {
    await route.fulfill({ json: { topic_id: 101, posts: [], platform_groups: [], summary_md: '', errors: [] } })
  })
  await page.route('**/api/sources', async (route) => {
    if (route.request().method() === 'POST') {
      createdSourcePayload = route.request().postDataJSON()
      const createdSource = {
        ...source,
        id: 2,
        ...createdSourcePayload,
        enabled: true,
        last_status: 'never',
        last_error: '',
        last_fetched_at: null,
        article_count: 0,
        created_at: '2026-07-03T10:00:00',
        updated_at: '2026-07-03T10:00:00',
      }
      sourceRows = [patchedSource || source, createdSource, failedSource]
      await route.fulfill({ json: createdSource })
      return
    }
    await route.fulfill({ json: sourceRows })
  })
  await page.route('**/api/sources/import', async (route) => {
    importedSourcePayload = route.request().postDataJSON()
    const importedSources = [
      {
        ...source,
        id: 3,
        name: 'Ukraine Alert',
        url: 'https://example.com/ukraine.xml',
        source_type: 'rss',
        quality_tier: 'newsletter',
        enabled: true,
        last_status: 'never',
        article_count: 0,
      },
      {
        ...source,
        id: 4,
        name: 'Morning Brew',
        url: 'https://www.morningbrew.com/daily/rss',
        source_type: 'rss',
        quality_tier: 'newsletter',
        enabled: true,
        last_status: 'never',
        article_count: 0,
      },
    ]
    sourceRows = [...importedSources, ...sourceRows]
    await route.fulfill({
      json: {
        created_count: 2,
        duplicate_count: 1,
        invalid_count: 1,
        created: importedSources,
        duplicates: [{ url: 'https://example.com/reuters.xml', name: 'Reuters' }],
        invalid: [{ line: 'not a url', error: 'No http(s) URL found' }],
      },
    })
  })
  await page.route('**/api/sources/1', async (route) => {
    patchedSource = { ...source, ...route.request().postDataJSON() }
    sourceRows = [patchedSource, ...sourceRows.filter((item) => item.id !== 1)]
    await route.fulfill({ json: patchedSource })
  })

  return {
    patchedSource: () => patchedSource,
    createdSourcePayload: () => createdSourcePayload,
    importedSourcePayload: () => importedSourcePayload,
  }
}

test('lists source registry entries and can pause a source', async ({ page }) => {
  const api = await mockApi(page)
  await page.goto('/')

  await page.getByRole('button', { name: '管理项目' }).click()

  const panel = page.locator('.source-manager')
  const sourceRow = panel.locator('.source-table article').filter({ hasText: 'Reuters' })
  await expect(sourceRow.locator('strong').getByText('Reuters', { exact: true })).toBeVisible()
  await expect(sourceRow.getByText('wire')).toBeVisible()
  await expect(sourceRow.getByText('ok')).toBeVisible()
  await expect(sourceRow.getByText('12 篇')).toBeVisible()

  await panel.getByRole('button', { name: '暂停' }).click()

  await expect.poll(() => api.patchedSource()).toMatchObject({ enabled: false })
})

test('summarizes source coverage, freshness, and failed sources', async ({ page }) => {
  await mockApi(page)
  await page.goto('/')

  await page.getByRole('button', { name: '管理项目' }).click()

  const summary = page.locator('.source-manager').locator('.source-status-summary')
  await expect(summary.getByText('共 2 个源')).toBeVisible()
  await expect(summary.getByText('启用 1 个')).toBeVisible()
  await expect(summary.getByText('失败 1 个')).toBeVisible()
  await expect(summary.getByText(/最近成功.*2026\/07\/03 08:00/)).toBeVisible()
  await expect(summary.getByText('Bellingcat Monitor：HTTP 403 blocked')).toBeVisible()
})

test('explains the source-ingestion path for feeds, newsletters, alerts and video leads', async ({ page }) => {
  await mockApi(page)
  await page.goto('/')

  await page.getByRole('button', { name: '管理项目' }).click()

  const guide = page.locator('.source-ingestion-guide')
  await expect(guide.getByText('情报源导入路径')).toBeVisible()
  await expect(guide.getByText('RSS / Newsletter / Google Alerts')).toBeVisible()
  await expect(guide.getByText('B站视频 / 网页线索')).toBeVisible()
  await expect(guide.getByText('V1 不做视频转录')).toBeVisible()
  await expect(guide.getByText('失败原因会显示在源状态表里')).toBeVisible()
})

test('adds a user RSS source from a Google Alerts feed', async ({ page }) => {
  const api = await mockApi(page)
  await page.goto('/')

  await page.getByRole('button', { name: '管理项目' }).click()

  const panel = page.locator('.source-manager')
  await panel.getByLabel('源名').fill('Google Alert - Ukraine frontline')
  await panel.getByLabel('Feed URL').fill('https://example.com/google-alerts/ukraine-frontline.xml')
  await panel.getByRole('button', { name: '添加源' }).click()

  await expect.poll(() => api.createdSourcePayload()).toMatchObject({
    name: 'Google Alert - Ukraine frontline',
    url: 'https://example.com/google-alerts/ukraine-frontline.xml',
    source_type: 'rss',
    quality_tier: 'user',
  })
  await expect(panel.locator('strong').getByText('Google Alert - Ukraine frontline')).toBeVisible()
})

test('imports newsletter and Google Alerts sources in bulk', async ({ page }) => {
  const api = await mockApi(page)
  await page.goto('/')

  await page.getByRole('button', { name: '管理项目' }).click()

  const panel = page.locator('.source-manager')
  await panel.getByLabel('批量导入情报源').fill([
    'Ukraine Alert https://example.com/ukraine.xml',
    'https://example.com/reuters.xml',
    'not a url',
    'Morning Brew https://www.morningbrew.com/daily/rss',
  ].join('\n'))
  await panel.getByLabel('批量导入层级').selectOption('newsletter')
  await panel.getByRole('button', { name: '批量导入' }).click()

  await expect.poll(() => api.importedSourcePayload()).toMatchObject({
    source_type: 'rss',
    quality_tier: 'newsletter',
  })
  expect(api.importedSourcePayload().text).toContain('Ukraine Alert')
  await expect(panel.getByText('导入 2 个，重复 1 个，无效 1 个。')).toBeVisible()
  await expect(panel.locator('strong').getByText('Ukraine Alert')).toBeVisible()
  await expect(panel.locator('strong').getByText('Morning Brew')).toBeVisible()
})
