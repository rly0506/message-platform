import { expect, type Page, test } from '@playwright/test'
import { openWorkbench } from './helpers'

const topic = {
  id: 601,
  name: '俄乌战争',
  description: 'mock topic',
  queries: ['俄乌战争'],
  status: 'active',
  created_at: '2026-07-03T00:00:00',
  article_count: 3,
  source_count: 2,
  enriched_count: 0,
  relevant_count: 3,
  latest_published_at: '2026-07-03T08:00:00',
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

async function mockApi(page: Page) {
  let crossPayload: { refresh_voices?: boolean } | null = null
  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: [topic] })
  })
  await page.route('**/api/projects', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/topics/601', async (route) => {
    await route.fulfill({ json: { ...topic, timeline: [], framing: [], analysis: null } })
  })
  await page.route('**/api/topics/601/articles**', async (route) => {
    await route.fulfill({ json: { total: 0, items: [] } })
  })
  await page.route('**/api/topics/601/local-events', async (route) => {
    await route.fulfill({ json: emptyLocalEvents })
  })
  await page.route('**/api/topics/601/academic', async (route) => {
    await route.fulfill({ json: { topic_id: 601, topic_name: topic.name, papers: [], graph: { nodes: [], edges: [] }, schools: [], foundational_papers: [], summary_md: '' } })
  })
  await page.route('**/api/topics/601/sentiment', async (route) => {
    await route.fulfill({ json: { topic_id: 601, topic_name: topic.name, platform: 'multi', warning: '', posts: [], summary_md: '' } })
  })
  await page.route('**/api/topics/601/cross-synthesis', async (route) => {
    await route.fulfill({ json: { topic_id: 601, topic_name: topic.name, content_md: '', voices_used: [], generated_at: null } })
  })
  await page.route('**/api/topics/601/cross-synthesis/jobs', async (route) => {
    crossPayload = route.request().postDataJSON() as { refresh_voices?: boolean }
    await route.fulfill({
      json: {
        id: 'cross-reuse-job',
        query: 'cross-synthesis:俄乌战争',
        status: 'done',
        steps: [],
        created_at: '2026-07-03T09:00:00',
        updated_at: '2026-07-03T09:00:00',
        result: null,
        error: '',
      },
    })
  })
  await page.route('**/api/search/jobs/cross-reuse-job', async (route) => {
    await route.fulfill({
      json: {
        id: 'cross-reuse-job',
        query: 'cross-synthesis:俄乌战争',
        status: 'done',
        steps: [],
        created_at: '2026-07-03T09:00:00',
        updated_at: '2026-07-03T09:00:00',
        result: {
          topic_id: 601,
          topic_name: topic.name,
          content_md: '## 三方对照\n复用既有声部。',
          voices_used: ['media'],
          chain: {},
          generated_at: '2026-07-03T09:00:00',
        },
        error: '',
      },
    })
  })
  return {
    crossPayload: () => crossPayload,
  }
}

test('runs standalone cross-synthesis in reuse-voices mode by default', async ({ page }) => {
  const api = await mockApi(page)
  await openWorkbench(page)

  await page.getByLabel('专题视图导航').getByRole('button', { name: '三方对照' }).click()
  await page.getByRole('button', { name: '生成三方对照' }).click()

  await expect.poll(() => api.crossPayload()).toEqual({ refresh_voices: false })
})
