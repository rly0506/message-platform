import { expect, type Page, test } from '@playwright/test'

let savedMark: Record<string, unknown> | null = null
let startedDiscoveryJobs = 0

const seeds = [
  {
    title: 'New nuclear battery moves from lab to pilot',
    url: 'https://example.com/energy-seed',
    domain: 'energy',
    domain_label: 'Energy',
    signal: 88,
    delta: 32,
    is_new: true,
    what: 'Small nuclear storage enters pilot',
    why: 'Energy is outside the current cognition boundary',
    still_niche: true,
  },
  {
    title: 'GPU cluster financing shifts to private credit',
    url: 'https://example.com/ai-finance-seed',
    domain: 'finance',
    domain_label: 'Finance',
    signal: 65,
    delta: 12,
    is_new: false,
    what: 'Compute center financing changes',
    why: 'Connects finance background with AI infrastructure mechanisms',
    still_niche: true,
  },
]

const historicalSeeds = [
  {
    title: 'Historical grid bottleneck',
    url: 'https://example.com/historical-grid',
    domain: 'energy',
    domain_label: 'Energy',
    signal: 71,
    delta: 11,
    is_new: false,
    what: 'Grid capacity constraint',
    why: 'Older report seed',
    still_niche: true,
  },
]

async function mockDiscoveryApi(page: Page) {
  savedMark = null
  startedDiscoveryJobs = 0
  await page.route('**/api/topics', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/discovery/latest', async (route) => {
    await route.fulfill({
      json: {
        markdown: '## Latest frontier report\n\nTwo seeds worth tracking.',
        run_id: '20260702T135734Z',
        seeds,
      },
    })
  })
  await page.route('**/api/discovery/reports', async (route) => {
    await route.fulfill({
      json: [
        { run_id: '20260702T135734Z', created_at: '20260702T135734Z', seed_count: 2, has_sidecar: true },
        { run_id: '20260630T043006Z', created_at: '20260630T043006Z', seed_count: 1, has_sidecar: true },
        { run_id: '20260629T010000Z', created_at: '20260629T010000Z', seed_count: 1, has_sidecar: true },
      ],
    })
  })
  await page.route('**/api/discovery/reports/20260630T043006Z', async (route) => {
    await route.fulfill({
      json: {
        markdown: '## Historical frontier report\n\nA previous archive entry.',
        run_id: '20260630T043006Z',
        seeds: historicalSeeds,
      },
    })
  })
  await page.route('**/api/discovery/timeline-tree', async (route) => {
    await route.fulfill({
      json: {
        branches: [
          {
            branch_key: 'energy',
            label: 'Energy',
            evidence_basis: 'local similarity signal',
            connection_kind: 'local_similarity',
            items: [
              {
                run_id: '20260630T043006Z',
                title: 'Historical grid bottleneck',
                url: 'https://example.com/historical-grid',
                domain: 'energy',
                domain_label: 'Energy',
                signal: 71,
                delta: 11,
                why: 'Older report seed',
              },
              {
                run_id: '20260702T135734Z',
                title: 'New nuclear battery moves from lab to pilot',
                url: 'https://example.com/energy-seed',
                domain: 'energy',
                domain_label: 'Energy',
                signal: 88,
                delta: 32,
                why: 'Latest report seed',
              },
            ],
          },
        ],
      },
    })
  })
  await page.route('**/api/discovery/jobs**', async (route) => {
    startedDiscoveryJobs += 1
    await route.fulfill({ status: 500, json: { detail: 'archive selection must not start discovery job' } })
  })
  await page.route('**/api/cognition/profile', async (route) => {
    await route.fulfill({
      json: [
        {
          id: 1,
          domain_key: 'energy',
          domain_label: 'Energy',
          level: 'unfamiliar',
          note: 'Heard in news, not actively studied',
          depth: 'none',
          interest: 'medium',
          confidence: 58,
          evidence: 'User said energy is mostly from surrounding news.',
          recommended_seed_style: 'mechanism',
          updated_at: '2026-06-29T00:00:00',
        },
        {
          id: 2,
          domain_key: 'ai_infra',
          domain_label: 'AI infrastructure',
          level: 'partial',
          note: 'Knows CPU, GPU, CPO and compute center terms',
          depth: 'terms',
          interest: 'high',
          confidence: 64,
          evidence: 'User chose AI infrastructure as a priority frontier.',
          recommended_seed_style: 'mechanism',
          updated_at: '2026-06-29T00:00:00',
        },
        {
          id: 3,
          domain_key: 'finance',
          domain_label: 'Finance',
          level: 'strong_partial',
          note: 'Course background is relatively strong',
          depth: 'coursework',
          interest: 'high',
          confidence: 78,
          evidence: 'User listed finance and accounting courses.',
          recommended_seed_style: 'financial_model',
          updated_at: '2026-06-29T00:00:00',
        },
      ],
    })
  })
  await page.route('**/api/cognition/marks?**', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/cognition/marks/summary', async (route) => {
    await route.fulfill({ json: { counts: {}, recent: [], unfamiliar_topics: [] } })
  })
  await page.route('**/api/cognition/marks', async (route) => {
    savedMark = route.request().postDataJSON()
    await route.fulfill({
      json: {
        id: 9,
        target_type: savedMark?.target_type,
        target_id: savedMark?.target_id,
        target_key: savedMark?.target_key,
        topic_id: null,
        label: savedMark?.label,
        note: savedMark?.note,
        updated_at: '2026-06-29T05:00:00',
      },
    })
  })
}

test.beforeEach(async ({ page }) => {
  await mockDiscoveryApi(page)
})

async function openDiscovery(page: Page) {
  await page.goto('/')
  await page.locator('.mode-switch button').nth(1).click()
}

test('marks a frontier seed as known from the cognition boundary queue and closes it', async ({ page }) => {
  await openDiscovery(page)

  const queue = page.locator('.boundary-queue')
  await expect(queue).toBeVisible()
  await expect(queue.locator('.boundary-list li')).toHaveCount(2)

  const queueItem = page.locator('.boundary-list li').filter({ hasText: 'New nuclear battery' })
  await expect(queueItem).toContainText('New nuclear battery')
  await expect(queueItem.getByRole('button').first()).toBeVisible()

  await queueItem.locator('.boundary-got-it').click()

  await expect(page.locator('.boundary-list li').filter({ hasText: 'New nuclear battery' })).toHaveCount(0)
  await expect.poll(() => savedMark).toMatchObject({
    target_type: 'seed',
    target_id: 0,
    target_key: 'https://example.com/energy-seed',
    label: 'known',
  })
})

test('keeps discovery report visible when cognition marking fails', async ({ page }) => {
  await page.route('**/api/cognition/marks', async (route) => {
    if (route.request().method() === 'PUT') {
      await route.fulfill({ status: 500, json: { detail: 'mark service unavailable' } })
      return
    }
    await route.fallback()
  })
  await openDiscovery(page)

  await page.locator('.boundary-list li').filter({ hasText: 'New nuclear battery' }).locator('.boundary-got-it').click()

  await expect(page.locator('.country-compare-error')).toContainText('mark service unavailable')
  await expect(page.locator('.boundary-queue')).toBeVisible()
  await expect(page.locator('.boundary-list')).toContainText('New nuclear battery')
  await expect(page.locator('.discovery-report')).toContainText('Latest frontier report')
})

test('collapses rest seeds and does not duplicate boundary-queue seeds', async ({ page }) => {
  const manySeeds = Array.from({ length: 12 }, (_, i) => ({
    title: `Seed number ${i}`,
    url: `https://example.com/seed-${i}`,
    domain: 'finance',
    domain_label: 'Finance',
    signal: 90 - i,
    delta: 5,
    is_new: false,
    what: `Seed ${i} summary`,
    why: `Seed ${i} reason`,
    still_niche: true,
  }))
  await page.route('**/api/discovery/latest', async (route) => {
    await route.fulfill({
      json: { markdown: '## Latest frontier report', run_id: '20260702T135734Z', seeds: manySeeds },
    })
  })

  await openDiscovery(page)

  await expect(page.locator('.boundary-list li')).toHaveCount(10)
  await expect(page.locator('.rest-seeds .stream-row')).toHaveCount(2)
  await expect(page.locator('.rest-seeds .stream-row').first()).not.toBeVisible()

  await page.locator('.rest-seeds-summary').click()
  await expect(page.locator('.rest-seeds .stream-row').first()).toBeVisible()
  const queueTitles = await page.locator('.boundary-list li strong').allInnerTexts()
  const restTitles = await page.locator('.rest-seeds .stream-title').allInnerTexts()
  for (const title of restTitles) {
    expect(queueTitles).not.toContain(title)
  }
})

test('shows profile evidence and local workflow prompts in boundary cards', async ({ page }) => {
  await openDiscovery(page)

  const firstItem = page.locator('.boundary-list li').first()
  await expect(firstItem).toContainText('New nuclear battery')
  await expect(firstItem).toContainText('画像依据')
  await expect(firstItem).toContainText('confidence 58%')
  await expect(firstItem).toContainText('分析工作流')
  await expect(firstItem).toContainText('先拆清能源类型、电力供给、成本曲线和替代能源')
  await expect(firstItem).toContainText('适合机制补课')

  const financeItem = page.locator('.boundary-list li').filter({ hasText: 'GPU cluster financing' })
  await expect(financeItem).toContainText('用财报、现金流、成本和需求曲线追问')
})

test('shows seed summary, report connection and suggested path in boundary cards', async ({ page }) => {
  await openDiscovery(page)

  const item = page.locator('.boundary-list li').filter({ hasText: 'New nuclear battery' })
  await expect(item).toContainText('摘要')
  await expect(item).toContainText('Small nuclear storage enters pilot')
  await expect(item).toContainText('相关日报线索')
  await expect(item).toContainText('认知时间树：Energy')
  await expect(item).toContainText('Older report seed')
  await expect(item).toContainText('深入理由')
  await expect(item).toContainText('Energy is outside the current cognition boundary')
  await expect(item).toContainText('为什么现在重要')
  await expect(item).toContainText('建议路径')
  await expect(item).toContainText('送进事件分析台')
})

test('loads historical discovery reports without starting a new discovery job', async ({ page }) => {
  await openDiscovery(page)

  const archiveSelect = page.locator('.discovery-archive-selector select')
  await expect(archiveSelect.locator('option')).toHaveCount(3)

  await archiveSelect.selectOption('20260630T043006Z')

  await expect(page.locator('.discovery-report-kind')).toBeVisible()
  await expect(page.locator('.discovery-report')).toContainText('Historical frontier report')
  await expect(page.locator('.boundary-list')).toContainText('Historical grid bottleneck')
  await expect.poll(() => startedDiscoveryJobs).toBe(0)
})

test('shows a local cognition timeline tree from archived reports', async ({ page }) => {
  await openDiscovery(page)

  const tree = page.locator('.cognition-timeline-tree')
  await expect(tree).toBeVisible()
  await expect(tree.locator('.timeline-tree-note')).not.toBeVisible()

  await tree.locator('summary').click()

  await expect(tree.locator('.timeline-tree-note')).toBeVisible()
  await expect(tree).toContainText('Energy')
  await expect(tree).toContainText('local similarity signal')
  await expect(tree).toContainText('Historical grid bottleneck')
  await expect(tree).toContainText('New nuclear battery moves from lab to pilot')
  await expect(tree.locator('.timeline-go').first()).toBeVisible()
  await expect(page.getByText('cause')).toHaveCount(0)
})
