import { expect, type Page, test } from '@playwright/test'

const currentYear = new Date().getFullYear()

const topic = {
  id: 303,
  name: 'AI academic signals',
  description: 'mock topic',
  queries: ['AI academic signals'],
  status: 'active',
  created_at: '2026-07-02T00:00:00',
  article_count: 0,
  source_count: 0,
  enriched_count: 0,
  relevant_count: 0,
  latest_published_at: null,
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

const academicLayer = {
  topic_id: 303,
  topic_name: topic.name,
  papers: [
    {
      openalex_id: 'https://openalex.org/W1',
      title: 'Foundational compute scaling paper',
      abstract: 'This paper reports compute scaling evidence across multiple model families.',
      year: currentYear - 8,
      cited_by_count: 900,
      authors: ['A. Scholar'],
      venue: 'Journal of AI Systems',
      concepts: [{ name: 'Artificial intelligence', score: 0.9, level: 1 }],
      doi: 'https://doi.org/10.1000/foundation',
      openalex_url: 'https://openalex.org/W1',
      citation_key: 'W1',
      citation: 'A. Scholar (2018). Foundational compute scaling paper. Journal of AI Systems. https://doi.org/10.1000/foundation',
      url: 'https://example.com/foundation',
    },
    {
      openalex_id: 'https://openalex.org/W2',
      title: 'Recent frontier evaluation paper',
      abstract: 'A recent evaluation of frontier model behavior.',
      year: currentYear,
      cited_by_count: 50,
      authors: ['B. Researcher'],
      venue: 'Conference on Machine Learning',
      concepts: [{ name: 'Evaluation', score: 0.8, level: 2 }],
      doi: '',
      openalex_url: 'https://openalex.org/W2',
      citation_key: 'W2',
      citation: 'B. Researcher (2026). Recent frontier evaluation paper. Conference on Machine Learning. https://openalex.org/W2',
      url: 'https://example.com/recent',
    },
    {
      openalex_id: 'https://openalex.org/W3',
      title: 'Sparse metadata working paper',
      abstract: '',
      year: currentYear - 1,
      cited_by_count: 0,
      authors: [],
      venue: '',
      concepts: [],
      doi: '',
      openalex_url: 'https://openalex.org/W3',
      citation_key: 'W3',
      citation: 'Unknown authors (2025). Sparse metadata working paper. Unknown venue. https://openalex.org/W3',
      url: 'https://example.com/sparse',
    },
    {
      openalex_id: 'https://openalex.org/W4',
      title: 'Venue-only background paper',
      abstract: 'Background context for the topic.',
      year: currentYear - 10,
      cited_by_count: 5,
      authors: ['C. Author'],
      venue: 'Policy Review',
      concepts: [],
      doi: '',
      openalex_url: 'https://openalex.org/W4',
      citation_key: 'W4',
      citation: 'C. Author (2016). Venue-only background paper. Policy Review. https://openalex.org/W4',
      url: 'https://example.com/background',
    },
  ],
  graph: {
    nodes: [],
    edges: [{ citing_openalex_id: 'https://openalex.org/W2', cited_openalex_id: 'https://openalex.org/W1' }],
  },
  literature_network: {
    nodes: [
      {
        id: 'https://openalex.org/W1',
        citation_key: 'W1',
        title: 'Foundational compute scaling paper',
        year: currentYear - 8,
        venue: 'Journal of AI Systems',
        cited_by_count: 900,
      },
      {
        id: 'https://openalex.org/W2',
        citation_key: 'W2',
        title: 'Recent frontier evaluation paper',
        year: currentYear,
        venue: 'Conference on Machine Learning',
        cited_by_count: 50,
      },
    ],
    edges: [
      {
        citing_openalex_id: 'https://openalex.org/W2',
        cited_openalex_id: 'https://openalex.org/W1',
        citing_title: 'Recent frontier evaluation paper',
        cited_title: 'Foundational compute scaling paper',
        relation: 'cites',
      },
    ],
  },
  schools: [],
  foundational_papers: [
    {
      openalex_id: 'https://openalex.org/W1',
      title: 'Foundational compute scaling paper',
      year: currentYear - 8,
      cited_by_count: 900,
      internal_citations: 3,
    },
  ],
  summary_md: '',
}

async function mockApi(page: Page) {
  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: [topic] })
  })
  await page.route('**/api/topics/303', async (route) => {
    await route.fulfill({ json: { ...topic, timeline: [], framing: [], analysis: null } })
  })
  await page.route('**/api/topics/303/articles**', async (route) => {
    await route.fulfill({ json: { total: 0, items: [] } })
  })
  await page.route('**/api/topics/303/local-events', async (route) => {
    await route.fulfill({ json: emptyLocalEvents })
  })
  await page.route('**/api/topics/303/academic', async (route) => {
    await route.fulfill({ json: academicLayer })
  })
  await page.route('**/api/cognition/marks?**', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/cognition/marks/summary', async (route) => {
    await route.fulfill({ json: { counts: {}, recent: [], unfamiliar_topics: [] } })
  })
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('shows academic priority-reading summary and neutral paper labels', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('专题视图导航').getByRole('button', { name: '学界' }).click()

  const scope = page.locator('.academic-source-scope')
  await expect(scope).toContainText('当前学界样本：OpenAlex')
  await expect(scope).toContainText('综述引用必须保留作者、年份、期刊/会议、DOI 或来源链接')
  await expect(scope).toContainText('文献网络只显示样本内部引用')

  const summary = page.locator('.academic-signal-summary')
  await expect(summary).toContainText('优先阅读信号')
  await expect(summary).toContainText('高引用')
  await expect(summary).toContainText('1')
  await expect(summary).toContainText('新近')
  await expect(summary).toContainText('2')
  await expect(summary).toContainText('样本内奠基')
  await expect(summary).toContainText('1')
  await expect(summary).toContainText('低信息')
  await expect(summary).toContainText('1')

  const foundational = page.locator('.academic-paper-list article').filter({ hasText: 'Foundational compute scaling paper' })
  await expect(foundational.locator('.academic-signal-badge')).toContainText(['样本内奠基', '高引用', 'venue明确'])
  await expect(foundational.getByRole('link', { name: 'Foundational compute scaling paper' })).toBeVisible()

  const recent = page.locator('.academic-paper-list article').filter({ hasText: 'Recent frontier evaluation paper' })
  await expect(recent.locator('.academic-signal-badge')).toContainText(['新近', 'venue明确'])

  const sparse = page.locator('.academic-paper-list article').filter({ hasText: 'Sparse metadata working paper' })
  await expect(sparse.locator('.academic-signal-badge')).toContainText(['新近', '低信息'])
})

test('shows citation metadata and readable literature network', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('专题视图导航').getByRole('button', { name: '学界' }).click()

  const foundational = page.locator('.academic-paper-list article').filter({ hasText: 'Foundational compute scaling paper' })
  await expect(foundational).toContainText('A. Scholar')
  await expect(foundational).toContainText('Journal of AI Systems')
  await expect(foundational).toContainText('https://doi.org/10.1000/foundation')
  await expect(foundational.getByRole('link', { name: 'DOI' })).toHaveAttribute('href', 'https://doi.org/10.1000/foundation')
  await expect(foundational.getByRole('link', { name: 'OpenAlex' })).toHaveAttribute('href', 'https://openalex.org/W1')

  const network = page.locator('.academic-literature-network')
  await expect(network).toContainText('文献网络')
  await expect(network).toContainText('Recent frontier evaluation paper')
  await expect(network).toContainText('引用')
  await expect(network).toContainText('Foundational compute scaling paper')
  await expect(page.locator('.academic-edge-list')).toHaveCount(0)
})
