import { expect, type Page, test } from '@playwright/test'
import { openWorkbench } from './helpers'

const project = {
  id: 201,
  name: '俄乌战争研究',
  description: '长期追踪俄乌战争的多个子专题。',
  status: 'active',
  archived_at: null,
  created_at: '2026-07-03T00:00:00',
  updated_at: '2026-07-03T00:00:00',
  topic_count: 1,
  topics: [
    {
      id: 101,
      project_id: 201,
      project_name: '俄乌战争研究',
      name: '俄乌战争',
      description: '主专题',
      queries: ['俄乌战争'],
      status: 'active',
      archived_at: null,
      created_at: '2026-07-03T00:00:00',
      updated_at: '2026-07-03T00:00:00',
      article_count: 12,
      source_count: 4,
      enriched_count: 3,
      relevant_count: 11,
      latest_published_at: '2026-07-03T09:00:00',
    },
  ],
}

const topic = project.topics[0]

async function mockProjectApi(page: Page) {
  const projects = [{ ...project, topics: project.topics.map((item) => ({ ...item })) }]
  const topics = project.topics.map((item) => ({ ...item }))
  let createdTopicPayload: any = null
  let createdProjectPayload: any = null
  let updatedProjectPayload: any = null
  let updatedTopicPayload: any = null
  let deletedProjectId: number | null = null
  let deletedTopicId: number | null = null

  function projectPayload() {
    return projects.map((item) => {
      const projectTopics = topics.filter((topicItem) => topicItem.project_id === item.id)
      return {
        ...item,
        topic_count: projectTopics.length,
        topics: projectTopics,
      }
    })
  }

  await page.route('**/api/projects', async (route) => {
    if (route.request().method() === 'POST') {
      createdProjectPayload = route.request().postDataJSON()
      const created = {
        ...project,
        id: 202,
        name: createdProjectPayload.name,
        description: createdProjectPayload.description || '',
        status: createdProjectPayload.status || 'active',
        topic_count: 0,
        topics: [],
      }
      projects.push(created)
      await route.fulfill({
        json: created,
      })
      return
    }
    await route.fulfill({ json: projectPayload() })
  })

  await page.route(/.*\/api\/projects\/\d+$/, async (route) => {
    const id = Number(route.request().url().split('/').pop())
    const target = projects.find((item) => item.id === id)
    if (!target) {
      await route.fulfill({ status: 404, json: { detail: 'Project not found' } })
      return
    }
    if (route.request().method() === 'PATCH') {
      updatedProjectPayload = route.request().postDataJSON()
      Object.assign(target, updatedProjectPayload, {
        archived_at: updatedProjectPayload.status === 'archived' ? '2026-07-03T10:00:00' : null,
      })
      await route.fulfill({ json: projectPayload().find((item) => item.id === id) })
      return
    }
    if (route.request().method() === 'DELETE') {
      deletedProjectId = id
      const index = projects.findIndex((item) => item.id === id)
      projects.splice(index, 1)
      await route.fulfill({ json: { deleted: true, project_id: id } })
      return
    }
    await route.fulfill({ json: target })
  })

  await page.route('**/api/topics', async (route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON()
      createdTopicPayload = body
      const created = {
        ...topic,
        id: 102,
        project_id: body.project_id,
        project_name: projects.find((item) => item.id === body.project_id)?.name || '',
        name: body.name,
        description: body.description,
        queries: body.queries,
        article_count: 0,
        source_count: 0,
        enriched_count: 0,
        relevant_count: 0,
        latest_published_at: null,
      }
      topics.push(created)
      await route.fulfill({
        json: created,
      })
      return
    }
    await route.fulfill({ json: topics })
  })

  await page.route(/.*\/api\/topics\/\d+$/, async (route) => {
    const id = Number(route.request().url().split('/').pop())
    const target = topics.find((item) => item.id === id)
    if (!target) {
      await route.fulfill({ status: 404, json: { detail: 'Topic not found' } })
      return
    }
    if (route.request().method() === 'PATCH') {
      updatedTopicPayload = route.request().postDataJSON()
      Object.assign(target, updatedTopicPayload, {
        archived_at: updatedTopicPayload.status === 'archived' ? '2026-07-03T10:30:00' : null,
      })
      await route.fulfill({ json: target })
      return
    }
    if (route.request().method() === 'DELETE') {
      deletedTopicId = id
      const index = topics.findIndex((item) => item.id === id)
      topics.splice(index, 1)
      await route.fulfill({ json: { deleted: true, topic_id: id } })
      return
    }
    await route.fulfill({ json: { ...target, timeline: [], framing: [], analysis: null } })
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
  await page.route('**/api/cognition/marks?**', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/cognition/marks/summary', async (route) => {
    await route.fulfill({ json: { counts: {}, recent: [], unfamiliar_topics: [] } })
  })

  return {
    createdProjectPayload: () => createdProjectPayload,
    createdTopicPayload: () => createdTopicPayload,
    updatedProjectPayload: () => updatedProjectPayload,
    updatedTopicPayload: () => updatedTopicPayload,
    deletedProjectId: () => deletedProjectId,
    deletedTopicId: () => deletedTopicId,
  }
}

test('manages projects and creates a topic inside a project', async ({ page }) => {
  const api = await mockProjectApi(page)
  await openWorkbench(page)

  await expect(page.getByRole('button', { name: '管理项目' })).toBeVisible()
  await page.getByRole('button', { name: '管理项目' }).click()

  const panel = page.locator('.project-manager')
  const projectCard = panel.locator('.project-row').filter({ hasText: '俄乌战争研究' })
  await expect(projectCard).toBeVisible()
  await expect(panel.getByText('1 个专题')).toBeVisible()
  await expect(projectCard.getByRole('button', { name: '俄乌战争' })).toBeVisible()

  await projectCard.getByRole('button', { name: '新建专题' }).click()
  await page.getByLabel('专题名称').fill('前线态势')
  await page.getByLabel('检索词').fill('俄乌战争 前线态势')
  await page.getByLabel('专题描述').fill('保留父专题语境的前线态势追踪。')
  await page.getByRole('button', { name: '保存专题' }).click()

  await expect.poll(() => api.createdTopicPayload()).toEqual({
    project_id: 201,
    name: '前线态势',
    description: '保留父专题语境的前线态势追踪。',
    queries: ['俄乌战争 前线态势'],
  })
})

test('edits archives and deletes existing projects and topics', async ({ page }) => {
  const api = await mockProjectApi(page)
  await openWorkbench(page)

  await page.getByRole('button', { name: '管理项目' }).click()
  const panel = page.locator('.project-manager')
  const projectCard = panel.locator('.project-row').filter({ hasText: '俄乌战争研究' })
  const topicRow = projectCard.locator('li').filter({ hasText: '俄乌战争' })

  await panel.getByRole('button', { name: '新建项目' }).click()
  await page.getByLabel('项目名称').fill('能源安全研究')
  await page.getByLabel('项目描述').fill('跟踪能源安全与关键矿产。')
  await page.getByRole('button', { name: '保存项目' }).click()
  await expect.poll(() => api.createdProjectPayload()).toEqual({
    name: '能源安全研究',
    description: '跟踪能源安全与关键矿产。',
  })

  await projectCard.getByRole('button', { name: '编辑项目' }).click()
  await page.getByLabel('项目名称').fill('俄乌战争档案')
  await page.getByLabel('项目描述').fill('长期追踪俄乌战争与欧洲安全。')
  await page.getByRole('button', { name: '保存项目' }).click()
  await expect.poll(() => api.updatedProjectPayload()).toEqual({
    name: '俄乌战争档案',
    description: '长期追踪俄乌战争与欧洲安全。',
  })

  await projectCard.getByRole('button', { name: '归档项目' }).click()
  await expect.poll(() => api.updatedProjectPayload()).toEqual({ status: 'archived' })

  const updatedProjectCard = panel.locator('.project-row').filter({ hasText: '俄乌战争档案' })
  const updatedTopicRow = updatedProjectCard.locator('li').filter({ hasText: '俄乌战争' })

  await updatedTopicRow.getByRole('button', { name: '编辑专题' }).click()
  await page.getByLabel('专题名称').fill('俄乌战争：前线态势')
  await page.getByLabel('检索词').fill('俄乌战争 前线态势\nRussia Ukraine frontline')
  await page.getByLabel('专题描述').fill('追踪战线变化、兵力部署和消耗。')
  await page.getByRole('button', { name: '保存专题' }).click()
  await expect.poll(() => api.updatedTopicPayload()).toEqual({
    name: '俄乌战争：前线态势',
    description: '追踪战线变化、兵力部署和消耗。',
    queries: ['俄乌战争 前线态势', 'Russia Ukraine frontline'],
    project_id: 201,
  })

  await updatedTopicRow.getByRole('button', { name: '归档专题' }).click()
  await expect.poll(() => api.updatedTopicPayload()).toEqual({ status: 'archived' })

  page.once('dialog', (dialog) => dialog.accept())
  await updatedTopicRow.getByRole('button', { name: '删除专题' }).click()
  await expect.poll(() => api.deletedTopicId()).toBe(101)

  const emptyProjectCard = panel.locator('.project-row').filter({ hasText: '能源安全研究' })
  page.once('dialog', (dialog) => dialog.accept())
  await emptyProjectCard.getByRole('button', { name: '删除项目' }).click()
  await expect.poll(() => api.deletedProjectId()).toBe(202)
})
