<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, onMounted, ref, watch } from 'vue'
import {
  createAcademicJob,
  createCrossSynthesisJob,
  createDeepAnalysisJob,
  createSearchJob,
  createSentimentJob,
  errorMessage,
  fetchArticles,
  fetchAcademic,
  fetchCountryCompare,
  fetchCrossSynthesis,
  fetchLocalEvents,
  fetchSearchJob,
  fetchSentiment,
  fetchTopic,
  fetchTopics,
  isNetworkError,
  rerunSearchJob,
} from './api/dossierApi'
import type {
  AcademicFoundationalPaper,
  AcademicLayer,
  AcademicPaper,
  Article,
  CountryCompare,
  CountryCompareCountry,
  CrossSynthesis,
  DeepAnalysisResult,
  EntityGroup,
  EvidenceArticle,
  Keyword,
  LocalEvent,
  LocalEventsPayload,
  SearchJob,
  SearchResponse,
  SentimentLayer,
  SentimentPost,
  TopicDetail,
  TopicSummary,
} from './types/dossier'

const topics = ref<TopicSummary[]>([])
const selectedTopicId = ref<number | null>(null)
const detail = ref<TopicDetail | null>(null)
const localData = ref<LocalEventsPayload | null>(null)
const articles = ref<Article[]>([])
const totalArticles = ref(0)
const loading = ref(true)
const articleLoading = ref(false)
const localLoading = ref(false)
const countryCompareLoading = ref(false)
const searching = ref(false)
const deepAnalyzing = ref(false)
const crossSynthesisAnalyzing = ref(false)
const academicAnalyzing = ref(false)
const sentimentAnalyzing = ref(false)
const crossSynthesisLoading = ref(false)
const academicLoading = ref(false)
const sentimentLoading = ref(false)
const error = ref('')
const query = ref('')
const eventSearch = ref('美伊战争')
const selectedEventIndex = ref(0)
const activeWorkspaceTab = ref<'media' | 'academic' | 'sentiment' | 'cross' | 'llm'>('media')
const expandedTimelineIndex = ref<number | null>(null)
const searchMessage = ref('')
const searchSteps = ref<{ key: string; label: string; status: string }[]>([])
const searchWarnings = ref<string[]>([])
const countryCompare = ref<CountryCompare | null>(null)
const countryCompareError = ref('')
const countryCompareEventKey = ref('')
const showArticles = ref(false)
const activeJobId = ref('')
const activeDeepJobId = ref('')
const activeCrossSynthesisJobId = ref('')
const activeAcademicJobId = ref('')
const activeSentimentJobId = ref('')
const terminalJob = ref<SearchJob | null>(null)
const deepJob = ref<SearchJob | null>(null)
const deepMessage = ref('')
const deepSteps = ref<{ key: string; label: string; status: string }[]>([])
const crossSynthesisLayer = ref<CrossSynthesis | null>(null)
const crossSynthesisJob = ref<SearchJob | null>(null)
const crossSynthesisMessage = ref('')
const crossSynthesisError = ref('')
const crossSynthesisSteps = ref<{ key: string; label: string; status: string }[]>([])
const academicLayer = ref<AcademicLayer | null>(null)
const academicJob = ref<SearchJob | null>(null)
const academicMessage = ref('')
const academicError = ref('')
const academicSteps = ref<{ key: string; label: string; status: string }[]>([])
const sentimentLayer = ref<SentimentLayer | null>(null)
const sentimentJob = ref<SearchJob | null>(null)
const sentimentMessage = ref('')
const sentimentError = ref('')
const sentimentSteps = ref<{ key: string; label: string; status: string }[]>([])
const sourceTierFilter = ref('all')
const sourceMatrixSort = ref('tier')
const articleCategoryFilter = ref('all')
const collectDiagnostics = ref<SearchResponse['collect'] | null>(null)
const pageSize = 80
const deepEnrichLimit = 30
const academicTopN = 30
const sentimentLimit = 25
const llmAnalysisMarker = '<!-- analysis-source: llm -->'
const workspaceTabs = [
  { key: 'media', label: '媒体' },
  { key: 'academic', label: '学界' },
  { key: 'sentiment', label: '民间情绪' },
  { key: 'cross', label: '三方对照' },
  { key: 'llm', label: 'LLM 深度分析' },
] as const

const stepStatusLabels: Record<string, string> = {
  pending: '等待中',
  running: '进行中',
  done: '已完成',
  warning: '已完成，有提示',
  empty: '没有新数据',
  skipped: '已跳过',
  failed: '失败',
  interrupted: '已中断',
}

const selectedTopic = computed(() =>
  topics.value.find((topic) => topic.id === selectedTopicId.value) || detail.value,
)

const storedAnalysisText = computed(() => detail.value?.analysis?.content_md || '')
const hasLlmAnalysis = computed(() => storedAnalysisText.value.includes(llmAnalysisMarker))
const analysisModeLabel = computed(() =>
  hasLlmAnalysis.value ? 'LLM 深度分析' : '本地规则模式',
)

const majorEvents = computed<LocalEvent[]>(() => {
  if (!hasLlmAnalysis.value && localData.value?.events.length) return localData.value.events
  return (detail.value?.timeline || []).map((item) => ({
    date: item.date,
    title_zh: item.title_zh,
    summary_zh: item.summary_zh,
    article_ids: item.article_ids,
    score: 0,
    source_count: 0,
    article_count: item.article_ids.length,
    stance: hasLlmAnalysis.value ? 'LLM 综合' : '综合判断',
  }))
})

const selectedEvent = computed(() => majorEvents.value[selectedEventIndex.value] || null)
const selectedEventKey = computed(() =>
  selectedEvent.value
    ? `${selectedTopicId.value || 'topic'}:${selectedEventIndex.value}:${selectedEvent.value.article_ids.join(',')}`
    : '',
)
const visibleCountryCompare = computed(() =>
  countryCompareEventKey.value && countryCompareEventKey.value === selectedEventKey.value ? countryCompare.value : null,
)
const countryCards = computed(() => visibleCountryCompare.value?.countries || [])
const firstReporterTimeline = computed(() => visibleCountryCompare.value?.first_reporters || [])
const hasCountryCompare = computed(() => Boolean(visibleCountryCompare.value))
const framing = computed(() =>
  hasLlmAnalysis.value ? detail.value?.framing || [] : localData.value?.framing || detail.value?.framing || [],
)
const analysisText = computed(() =>
  hasLlmAnalysis.value
    ? detail.value?.analysis?.content_md || ''
    : localData.value?.analysis_md || detail.value?.analysis?.content_md || '',
)
const displayAnalysisText = computed(() => analysisText.value.replace(llmAnalysisMarker, '').trim())
const safeAnalysisHtml = computed(() => {
  if (!displayAnalysisText.value) return ''
  const html = marked.parse(displayAnalysisText.value, { async: false, breaks: true, gfm: true }) as string
  return DOMPurify.sanitize(html)
})
const safeAcademicSummaryHtml = computed(() => {
  const text = academicLayer.value?.summary_md?.trim()
  if (!text) return ''
  const html = marked.parse(text, { async: false, breaks: true, gfm: true }) as string
  return DOMPurify.sanitize(html)
})
const safeSentimentSummaryHtml = computed(() => {
  const text = sentimentLayer.value?.summary_md?.trim()
  if (!text) return ''
  const html = marked.parse(text, { async: false, breaks: true, gfm: true }) as string
  return DOMPurify.sanitize(html)
})
const safeCrossSynthesisHtml = computed(() => {
  const text = crossSynthesisLayer.value?.content_md?.trim()
  if (!text) return ''
  const html = marked.parse(text, { async: false, breaks: true, gfm: true }) as string
  return DOMPurify.sanitize(html)
})
const crossVoicesUsed = computed(() => crossSynthesisLayer.value?.voices_used || [])
const crossChainItems = computed(() => {
  const chain = crossSynthesisLayer.value?.chain || {}
  return ['media', 'academic', 'sentiment'].map((voice) => ({
    key: voice,
    label: voiceLabel(voice),
    status: chain[voice]?.status || 'pending',
    error: chain[voice]?.error || '',
  }))
})
const hasCrossSynthesis = computed(() => Boolean(crossSynthesisLayer.value?.content_md?.trim()))
const academicPapers = computed(() => academicLayer.value?.papers || [])
const academicSchools = computed(() => academicLayer.value?.schools || [])
const academicFoundationalPapers = computed(() => academicLayer.value?.foundational_papers || [])
const academicCitationEdges = computed(() => academicLayer.value?.graph?.edges || [])
const hasAcademicLayer = computed(() => Boolean(academicLayer.value))
const sentimentPosts = computed(() => sentimentLayer.value?.posts || [])
const hasSentimentLayer = computed(() => Boolean(sentimentLayer.value))
const sentimentPostItems = computed(() => sentimentPosts.value.filter((post) => (post.kind || 'post') !== 'comment'))
const sentimentCommentItems = computed(() => sentimentPosts.value.filter((post) => post.kind === 'comment'))
const sentimentCommentsByParent = computed(() => {
  const groups = new Map<string, SentimentPost[]>()
  for (const comment of sentimentCommentItems.value) {
    const parent = String(comment.parent_post_id || '')
    if (!parent) continue
    if (!groups.has(parent)) groups.set(parent, [])
    groups.get(parent)?.push(comment)
  }
  return groups
})
const sentimentPlatformGroups = computed(() => {
  const groups = new Map<string, SentimentPost[]>()
  for (const post of sentimentPostItems.value) {
    const platform = post.platform || 'unknown'
    if (!groups.has(platform)) groups.set(platform, [])
    groups.get(platform)?.push(post)
  }
  return [...groups.entries()]
    .map(([platform, posts]) => ({ platform, label: sentimentPlatformLabel(platform), posts }))
    .sort((a, b) => sentimentPlatformRank(a.platform) - sentimentPlatformRank(b.platform))
})
const sentimentPlatformLabels = computed(() =>
  (sentimentLayer.value?.platforms?.length ? sentimentLayer.value.platforms : sentimentPlatformGroups.value.map((group) => group.platform))
    .map(sentimentPlatformLabel)
    .join(' / '),
)
const stancePeriods = computed(() => localData.value?.stance_evolution || [])
const criteria = computed(() => localData.value?.criteria || [])
const keywords = computed(() => localData.value?.keywords || [])
const entities = computed(() => localData.value?.entities || [])
const entityGroups = computed<EntityGroup[]>(() => localData.value?.entity_groups || [])
const authorityTierKeys = new Set(['wire', 'official', 'professional', 'mainstream'])
const sourceTierOptions = computed(() => {
  const matrix = selectedEvent.value?.source_matrix || []
  const seen = new Map<string, string>()
  for (const source of matrix) {
    seen.set(source.tier || 'other', source.tier_label || '其他来源')
  }
  const hasAuthority = [...seen.keys()].some((key) => authorityTierKeys.has(key))
  return [
    { key: 'all', label: '全部来源' },
    ...(hasAuthority ? [{ key: 'authority', label: '权威来源' }] : []),
    ...[...seen.entries()].map(([key, label]) => ({ key, label })),
  ]
})

const visibleSourceMatrix = computed(() => {
  const matrix = [...(selectedEvent.value?.source_matrix || [])]
  const filtered =
    sourceTierFilter.value === 'all'
      ? matrix
      : sourceTierFilter.value === 'authority'
        ? matrix.filter((source) => authorityTierKeys.has(source.tier || 'other'))
      : matrix.filter((source) => (source.tier || 'other') === sourceTierFilter.value)

  return filtered.sort((a, b) => {
    if (sourceMatrixSort.value === 'first') {
      return dateValue(a.first_published_at) - dateValue(b.first_published_at)
    }
    if (sourceMatrixSort.value === 'count') {
      return b.article_count - a.article_count || dateValue(a.first_published_at) - dateValue(b.first_published_at)
    }
    if (sourceMatrixSort.value === 'stance') {
      return a.dominant_stance.localeCompare(b.dominant_stance, 'zh-CN') || b.article_count - a.article_count
    }
    return tierRank(a.tier) - tierRank(b.tier) || b.article_count - a.article_count
  })
})

const articleCategoryGroups = computed(() => {
  const groups = new Map<string, Article[]>()
  for (const article of filteredArticles.value) {
    const key = article.category || '行动进展'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)?.push(article)
  }
  return [...groups.entries()]
    .map(([category, items]) => ({ category, items }))
    .sort((a, b) => b.items.length - a.items.length || a.category.localeCompare(b.category, 'zh-CN'))
})

const visibleArticleGroups = computed(() => {
  if (articleCategoryFilter.value === 'all') return articleCategoryGroups.value
  return articleCategoryGroups.value.filter((group) => group.category === articleCategoryFilter.value)
})

const articleCategoryOptions = computed(() => [
  { key: 'all', label: '全部分类' },
  ...articleCategoryGroups.value.map((group) => ({
    key: group.category,
    label: `${group.category} ${group.items.length}`,
  })),
])

const filteredArticles = computed(() => {
  const needle = query.value.trim().toLowerCase()
  if (!needle) return articles.value
  return articles.value.filter((article) =>
    [
      article.title,
      article.title_zh,
      article.source,
      article.snippet,
      article.snippet_zh,
      article.stance,
      article.stance_summary,
    ]
      .join(' ')
      .toLowerCase()
      .includes(needle),
  )
})

const stanceGroups = computed(() => {
  const counts = new Map<string, number>()
  for (const article of articles.value) {
    const key = article.stance || (article.enriched ? '未标注' : '本地待判定')
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6)
})

onMounted(async () => {
  await loadTopics()
})

watch(selectedTopicId, async (id) => {
  if (id) {
    localData.value = null
    resetCountryCompare()
    resetCrossSynthesisState()
    resetAcademicState()
    resetSentimentState()
    selectedEventIndex.value = 0
    expandedTimelineIndex.value = null
    await Promise.all([
      loadTopic(id),
      loadArticles(id),
      loadLocalEvents(id),
      loadCrossSynthesisLayer(id),
      loadAcademicLayer(id),
      loadSentimentLayer(id),
    ])
  }
})

watch(majorEvents, () => {
  if (selectedEventIndex.value >= majorEvents.value.length) {
    selectedEventIndex.value = 0
  }
  if (expandedTimelineIndex.value !== null && expandedTimelineIndex.value >= majorEvents.value.length) {
    expandedTimelineIndex.value = null
  }
})

watch(selectedEventIndex, () => {
  sourceTierFilter.value = 'all'
  sourceMatrixSort.value = 'tier'
  resetCountryCompare()
})

async function loadTopics(preferTopicId?: number) {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchTopics()
    topics.value = data
    selectedTopicId.value = preferTopicId || selectedTopicId.value || data[0]?.id || null
  } catch (err) {
    error.value = readableError(err)
  } finally {
    loading.value = false
  }
}

async function loadTopic(id: number) {
  detail.value = await fetchTopic(id)
}

async function loadArticles(id: number) {
  articleLoading.value = true
  try {
    const data = await fetchArticles(id, pageSize)
    articles.value = data.items
    totalArticles.value = data.total
  } finally {
    articleLoading.value = false
  }
}

async function loadLocalEvents(id: number) {
  localLoading.value = true
  try {
    localData.value = await fetchLocalEvents(id)
  } finally {
    localLoading.value = false
  }
}

async function loadAcademicLayer(id: number) {
  academicLoading.value = true
  academicError.value = ''
  try {
    academicLayer.value = await fetchAcademic(id)
  } catch (err) {
    academicError.value = readableError(err)
    academicLayer.value = null
  } finally {
    academicLoading.value = false
  }
}

async function loadSentimentLayer(id: number) {
  sentimentLoading.value = true
  sentimentError.value = ''
  try {
    sentimentLayer.value = await fetchSentiment(id)
  } catch (err) {
    sentimentError.value = readableError(err)
    sentimentLayer.value = null
  } finally {
    sentimentLoading.value = false
  }
}

async function loadCrossSynthesisLayer(id: number) {
  crossSynthesisLoading.value = true
  crossSynthesisError.value = ''
  try {
    crossSynthesisLayer.value = await fetchCrossSynthesis(id)
  } catch (err) {
    crossSynthesisError.value = readableError(err)
    crossSynthesisLayer.value = null
  } finally {
    crossSynthesisLoading.value = false
  }
}

async function loadCountryCompareForSelectedEvent() {
  const topicId = selectedTopicId.value
  const event = selectedEvent.value
  if (!topicId || !event || countryCompareLoading.value) return
  countryCompareLoading.value = true
  countryCompareError.value = ''
  try {
    countryCompare.value = await fetchCountryCompare(topicId, event.article_ids)
    countryCompareEventKey.value = selectedEventKey.value
  } catch (err) {
    countryCompareError.value = readableError(err)
  } finally {
    countryCompareLoading.value = false
  }
}

function resetCountryCompare() {
  countryCompare.value = null
  countryCompareError.value = ''
  countryCompareEventKey.value = ''
}

function resetCrossSynthesisState() {
  crossSynthesisLayer.value = null
  crossSynthesisJob.value = null
  crossSynthesisMessage.value = ''
  crossSynthesisError.value = ''
  crossSynthesisSteps.value = []
  activeCrossSynthesisJobId.value = ''
}

function resetAcademicState() {
  academicLayer.value = null
  academicJob.value = null
  academicMessage.value = ''
  academicError.value = ''
  academicSteps.value = []
  activeAcademicJobId.value = ''
}

function resetSentimentState() {
  sentimentLayer.value = null
  sentimentJob.value = null
  sentimentMessage.value = ''
  sentimentError.value = ''
  sentimentSteps.value = []
  activeSentimentJobId.value = ''
}

function toggleTimelineEvent(index: number) {
  selectedEventIndex.value = index
  expandedTimelineIndex.value = expandedTimelineIndex.value === index ? null : index
}

async function runEventSearch() {
  const term = eventSearch.value.trim()
  if (!term) return
  searching.value = true
  error.value = ''
  searchMessage.value = ''
  searchWarnings.value = []
  terminalJob.value = null
  collectDiagnostics.value = null
  searchSteps.value = [
    { key: 'topic', label: '创建/复用专题', status: 'running' },
    { key: 'collect', label: '采集新闻', status: 'pending' },
    { key: 'analyze', label: '本地分析', status: 'pending' },
  ]
  try {
    const job = await createSearchJob(term)
    activeJobId.value = job.id
    searchSteps.value = job.steps || searchSteps.value
    searchMessage.value = `任务已提交：${job.id.slice(0, 8)}`
    const res = await waitForSearchJob(job.id)
    await finishSearchJob(res)
  } catch (err) {
    error.value = readableError(err)
    searchSteps.value = searchSteps.value.map((step) =>
      step.status === 'running' ? { ...step, status: 'failed' } : step,
    )
  } finally {
    searching.value = false
    activeJobId.value = ''
  }
}

async function rerunTerminalJob() {
  const job = terminalJob.value
  if (!job || !canRerunJob(job) || searching.value) return
  searching.value = true
  error.value = ''
  searchMessage.value = `正在重新提交任务 ${job.id.slice(0, 8)}...`
  searchWarnings.value = []
  collectDiagnostics.value = null
  try {
    const newJob = await rerunSearchJob(job.id)
    activeJobId.value = newJob.id
    terminalJob.value = null
    searchSteps.value = newJob.steps || []
    searchMessage.value = `已重新提交：${newJob.id.slice(0, 8)}`
    const res = await waitForSearchJob(newJob.id)
    await finishSearchJob(res)
  } catch (err) {
    error.value = readableError(err)
    searchSteps.value = searchSteps.value.map((step) =>
      step.status === 'running' ? { ...step, status: 'failed' } : step,
    )
  } finally {
    searching.value = false
    activeJobId.value = ''
  }
}

async function runDeepAnalysis() {
  const topicId = selectedTopicId.value
  if (!topicId || deepAnalyzing.value) return
  deepAnalyzing.value = true
  error.value = ''
  deepMessage.value = ''
  deepJob.value = null
  deepSteps.value = [
    { key: 'enrich', label: 'LLM 富化报道', status: 'running' },
    { key: 'synthesize', label: 'LLM 综合分析', status: 'pending' },
    { key: 'persist', label: '写入专题档案', status: 'pending' },
  ]
  try {
    const job = await createDeepAnalysisJob(topicId, deepEnrichLimit)
    activeDeepJobId.value = job.id
    deepSteps.value = job.steps || deepSteps.value
    deepMessage.value = `深度分析任务已提交：${job.id.slice(0, 8)}`
    const resultJob = await waitForDeepAnalysisJob(job.id)
    await finishDeepAnalysisJob(resultJob)
  } catch (err) {
    error.value = readableError(err)
    deepSteps.value = deepSteps.value.map((step) =>
      step.status === 'running' ? { ...step, status: 'failed' } : step,
    )
  } finally {
    deepAnalyzing.value = false
    activeDeepJobId.value = ''
  }
}

async function runAcademicAnalysis() {
  const topicId = selectedTopicId.value
  if (!topicId || academicAnalyzing.value) return
  academicAnalyzing.value = true
  academicError.value = ''
  academicMessage.value = ''
  academicJob.value = null
  academicSteps.value = [
    { key: 'fetch', label: '拉取 OpenAlex 论文', status: 'running' },
    { key: 'graph', label: '构建引用图与学派', status: 'pending' },
    { key: 'synthesize', label: '综合学界共识', status: 'pending' },
    { key: 'persist', label: '写入学界层', status: 'pending' },
  ]
  try {
    const job = await createAcademicJob(topicId, academicTopN)
    activeAcademicJobId.value = job.id
    academicSteps.value = job.steps || academicSteps.value
    academicMessage.value = `学界任务已提交：${job.id.slice(0, 8)}`
    const resultJob = await waitForAcademicJob(job.id)
    await finishAcademicJob(resultJob)
  } catch (err) {
    academicError.value = readableError(err)
    academicSteps.value = academicSteps.value.map((step) =>
      step.status === 'running' ? { ...step, status: 'failed' } : step,
    )
  } finally {
    academicAnalyzing.value = false
    activeAcademicJobId.value = ''
  }
}

async function runSentimentAnalysis() {
  const topicId = selectedTopicId.value
  if (!topicId || sentimentAnalyzing.value) return
  sentimentAnalyzing.value = true
  sentimentError.value = ''
  sentimentMessage.value = ''
  sentimentJob.value = null
  sentimentSteps.value = [
    { key: 'fetch', label: '拉取 Reddit 民间讨论', status: 'running' },
    { key: 'summarize', label: '批判性总结民间情绪', status: 'pending' },
    { key: 'persist', label: '写入民间情绪层', status: 'pending' },
  ]
  try {
    const job = await createSentimentJob(topicId, sentimentLimit)
    activeSentimentJobId.value = job.id
    sentimentSteps.value = job.steps || sentimentSteps.value
    sentimentMessage.value = `民间情绪任务已提交：${job.id.slice(0, 8)}`
    const resultJob = await waitForSentimentJob(job.id)
    await finishSentimentJob(resultJob)
  } catch (err) {
    sentimentError.value = readableError(err)
    sentimentSteps.value = sentimentSteps.value.map((step) =>
      step.status === 'running' ? { ...step, status: 'failed' } : step,
    )
  } finally {
    sentimentAnalyzing.value = false
    activeSentimentJobId.value = ''
  }
}

async function runCrossSynthesis() {
  const topicId = selectedTopicId.value
  if (!topicId || crossSynthesisAnalyzing.value) return
  crossSynthesisAnalyzing.value = true
  crossSynthesisError.value = ''
  crossSynthesisMessage.value = ''
  crossSynthesisJob.value = null
  crossSynthesisSteps.value = [
    { key: 'gather', label: '汇总媒体/学界/民间声部', status: 'running' },
    { key: 'synthesize', label: '综合三方对照', status: 'pending' },
    { key: 'persist', label: '写入三方对照', status: 'pending' },
  ]
  try {
    const job = await createCrossSynthesisJob(topicId)
    activeCrossSynthesisJobId.value = job.id
    crossSynthesisSteps.value = job.steps || crossSynthesisSteps.value
    crossSynthesisMessage.value = `三方对照任务已提交：${job.id.slice(0, 8)}`
    const resultJob = await waitForCrossSynthesisJob(job.id)
    await finishCrossSynthesisJob(resultJob)
  } catch (err) {
    crossSynthesisError.value = readableError(err)
    crossSynthesisSteps.value = crossSynthesisSteps.value.map((step) =>
      step.status === 'running' ? { ...step, status: 'failed' } : step,
    )
  } finally {
    crossSynthesisAnalyzing.value = false
    activeCrossSynthesisJobId.value = ''
  }
}

async function finishSearchJob(job: SearchJob) {
  terminalJob.value = job
  if (!job.result) {
    throw new Error(job.error || '搜索任务未返回结果')
  }
  const result = job.result
  const topicId = result.topic.id
  localData.value = {
    events: result.events,
    framing: result.framing,
    analysis_md: result.analysis_md,
    stance_evolution: result.stance_evolution,
    keywords: result.keywords,
    entities: result.entities,
    entity_groups: result.entity_groups,
    criteria: result.criteria,
  }
  selectedEventIndex.value = 0
  searchSteps.value = result.steps || []
  searchWarnings.value = result.collect.errors || []
  collectDiagnostics.value = result.collect
  searchMessage.value = `采集 ${result.collect.raw} 条，保留 ${result.collect.kept} 条，新增 ${result.collect.new_articles} 篇。`
  await loadTopics(topicId)
  await Promise.all([loadTopic(topicId), loadArticles(topicId)])
}

async function finishDeepAnalysisJob(job: SearchJob) {
  deepJob.value = job
  if (!job.result) {
    throw new Error(job.error || '深度分析任务未返回结果')
  }
  if (!isDeepAnalysisResult(job.result)) {
    throw new Error('深度分析任务返回了未知结果')
  }
  if (job.status !== 'done') {
    throw new Error(job.error || `深度分析任务${stepStatusText(job.status)}`)
  }
  const result = job.result
  localData.value = null
  selectedEventIndex.value = 0
  deepSteps.value = job.steps || []
  deepMessage.value =
    `LLM 深度分析完成：富化 ${result.enrich.processed} 篇，` +
    `综合 ${result.synthesize.input_articles} 篇，生成 ${result.synthesize.timeline} 个节点。`
  await loadTopics(result.topic_id)
  await Promise.all([loadTopic(result.topic_id), loadArticles(result.topic_id), loadLocalEvents(result.topic_id)])
}

async function finishAcademicJob(job: SearchJob) {
  academicJob.value = job
  if (job.status !== 'done') {
    throw new Error(job.error || `学界任务${stepStatusText(job.status)}`)
  }
  if (job.result && !isAcademicLayer(job.result)) {
    throw new Error('学界任务返回了未知结果')
  }
  academicSteps.value = job.steps || []
  const topicId = selectedTopicId.value
  if (topicId) {
    await loadAcademicLayer(topicId)
  } else if (isAcademicLayer(job.result)) {
    academicLayer.value = job.result
  }
  const papers = academicLayer.value?.papers.length ?? 0
  const edges = academicLayer.value?.graph?.edges.length ?? 0
  academicMessage.value = `学界视角已更新：${papers} 篇论文，${edges} 条内部引用。`
}

async function finishSentimentJob(job: SearchJob) {
  sentimentJob.value = job
  if (job.status !== 'done' && job.status !== 'empty') {
    throw new Error(job.error || `民间情绪任务${stepStatusText(job.status)}`)
  }
  if (job.result && !isSentimentLayer(job.result)) {
    throw new Error('民间情绪任务返回了未知结果')
  }
  sentimentSteps.value = job.steps || []
  const topicId = selectedTopicId.value
  if (topicId) {
    await loadSentimentLayer(topicId)
  } else if (isSentimentLayer(job.result)) {
    sentimentLayer.value = job.result
  }
  const posts = sentimentLayer.value?.posts.length ?? 0
  sentimentMessage.value =
    posts > 0
      ? `民间情绪已更新：${posts} 条 Reddit 讨论。`
      : '民间情绪任务完成，但没有抓到可用帖子。'
}

async function finishCrossSynthesisJob(job: SearchJob) {
  crossSynthesisJob.value = job
  if (job.status !== 'done') {
    throw new Error(job.error || `三方对照任务${stepStatusText(job.status)}`)
  }
  if (job.result && !isCrossSynthesis(job.result)) {
    throw new Error('三方对照任务返回了未知结果')
  }
  crossSynthesisSteps.value = job.steps || []
  const topicId = selectedTopicId.value
  if (topicId) {
    await loadCrossSynthesisLayer(topicId)
  } else if (isCrossSynthesis(job.result)) {
    crossSynthesisLayer.value = job.result
  }
  const voices = crossVoicesUsed.value.length
  crossSynthesisMessage.value =
    voices > 0
      ? `三方对照已更新：使用 ${voices} 个声部。`
      : '三方对照已更新，但当前没有可用声部数据。'
}

async function waitForSearchJob(jobId: string) {
  const terminal = new Set(['done', 'empty', 'failed', 'interrupted'])
  for (;;) {
    const job = await fetchSearchJob(jobId)
    searchSteps.value = job.steps || searchSteps.value
    if (job.status === 'running' || job.status === 'queued') {
      searchMessage.value = `任务 ${jobId.slice(0, 8)} 正在${job.status === 'queued' ? '排队' : '执行'}...`
    }
    if (terminal.has(job.status)) {
      return job
    }
    await delay(1200)
  }
}

async function waitForDeepAnalysisJob(jobId: string) {
  const terminal = new Set(['done', 'empty', 'failed', 'interrupted'])
  for (;;) {
    const job = await fetchSearchJob(jobId)
    deepSteps.value = job.steps || deepSteps.value
    if (job.status === 'running' || job.status === 'queued') {
      deepMessage.value = `深度分析 ${jobId.slice(0, 8)} 正在${job.status === 'queued' ? '排队' : '执行'}...`
    }
    if (terminal.has(job.status)) {
      return job
    }
    await delay(1500)
  }
}

async function waitForAcademicJob(jobId: string) {
  const terminal = new Set(['done', 'empty', 'failed', 'interrupted'])
  for (;;) {
    const job = await fetchSearchJob(jobId)
    academicSteps.value = job.steps || academicSteps.value
    if (job.status === 'running' || job.status === 'queued') {
      academicMessage.value = `学界任务 ${jobId.slice(0, 8)} 正在${job.status === 'queued' ? '排队' : '执行'}...`
    }
    if (terminal.has(job.status)) {
      return job
    }
    await delay(1800)
  }
}

async function waitForSentimentJob(jobId: string) {
  const terminal = new Set(['done', 'empty', 'failed', 'interrupted'])
  for (;;) {
    const job = await fetchSearchJob(jobId)
    sentimentSteps.value = job.steps || sentimentSteps.value
    if (job.status === 'running' || job.status === 'queued') {
      sentimentMessage.value = `民间情绪任务 ${jobId.slice(0, 8)} 正在${job.status === 'queued' ? '排队' : '执行'}...`
    }
    if (terminal.has(job.status)) {
      return job
    }
    await delay(1800)
  }
}

async function waitForCrossSynthesisJob(jobId: string) {
  const terminal = new Set(['done', 'empty', 'failed', 'interrupted'])
  for (;;) {
    const job = await fetchSearchJob(jobId)
    crossSynthesisSteps.value = job.steps || crossSynthesisSteps.value
    if (job.status === 'running' || job.status === 'queued') {
      crossSynthesisMessage.value = `三方对照任务 ${jobId.slice(0, 8)} 正在${job.status === 'queued' ? '排队' : '执行'}...`
    }
    if (terminal.has(job.status)) {
      return job
    }
    await delay(1800)
  }
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function canRerunJob(job: SearchJob | null) {
  return job?.status === 'interrupted' || job?.status === 'failed'
}

function isDeepAnalysisResult(result: SearchJob['result']): result is DeepAnalysisResult {
  return Boolean(result && 'topic_id' in result && 'synthesize' in result && 'enrich' in result)
}

function isAcademicLayer(result: SearchJob['result']): result is AcademicLayer {
  return Boolean(result && 'papers' in result && 'graph' in result && 'schools' in result && 'summary_md' in result)
}

function isSentimentLayer(result: SearchJob['result']): result is SentimentLayer {
  return Boolean(result && 'posts' in result && 'warning' in result && 'platform' in result)
}

function isCrossSynthesis(result: SearchJob['result']): result is CrossSynthesis {
  return Boolean(result && 'content_md' in result && 'voices_used' in result && 'generated_at' in result)
}

function dateValue(value: string | null) {
  if (!value) return Number.MAX_SAFE_INTEGER
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? Number.MAX_SAFE_INTEGER : time
}

function tierRank(tier: string) {
  const order = ['wire', 'official', 'professional', 'mainstream', 'aggregator', 'other']
  const index = order.indexOf(tier || 'other')
  return index >= 0 ? index : order.length
}

function showAuthoritySources() {
  sourceTierFilter.value = 'authority'
  sourceMatrixSort.value = 'tier'
}

function showEarliestSources() {
  sourceTierFilter.value = 'all'
  sourceMatrixSort.value = 'first'
}

function showMostCoveredSources() {
  sourceTierFilter.value = 'all'
  sourceMatrixSort.value = 'count'
}

function fmtDate(value: string | null, withTime = false) {
  if (!value) return '未知时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value.slice(0, 10)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  }).format(date)
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`
}

function scoreText(value: number) {
  if (value <= 0) return '未评分'
  return percent(value)
}

function importanceText(event: LocalEvent) {
  return event.importance_label ? `${event.importance_label}关键性` : scoreText(event.score)
}

function coverageText(event: LocalEvent) {
  return event.coverage_label || `${event.source_count} 个来源`
}

function stepStatusText(status: string) {
  return stepStatusLabels[status] || status
}

function titleFor(article: Article) {
  return article.title_zh || article.title || '未命名报道'
}

function snippetFor(article: Article) {
  return article.snippet_zh || article.snippet || article.stance_summary || '暂无摘要'
}

function keywordSize(keyword: Keyword) {
  return `${12 + Math.round(keyword.weight * 10)}px`
}

function evidenceSnippet(article: EvidenceArticle) {
  return article.snippet || '暂无摘要，仅保留标题、来源与链接。'
}

function academicAuthors(paper: AcademicPaper) {
  if (!paper.authors?.length) return 'Unknown authors'
  return paper.authors.slice(0, 3).join(', ')
}

function academicVenue(paper: AcademicPaper) {
  return paper.venue || 'Unknown venue'
}

function isFoundationalPaper(paper: AcademicPaper) {
  return academicFoundationalPapers.value.some((item) => item.openalex_id === paper.openalex_id)
}

function foundationalStats(paper: AcademicPaper) {
  return academicFoundationalPapers.value.find((item) => item.openalex_id === paper.openalex_id)
}

function academicPaperUrl(paper: AcademicPaper | AcademicFoundationalPaper) {
  if ('url' in paper && paper.url) return paper.url
  return paper.openalex_id
}

function sentimentPostDate(post: SentimentPost) {
  const raw = String(post.created_utc || '').trim()
  if (!raw) return '未知时间'
  const numeric = Number(raw)
  if (!Number.isNaN(numeric) && numeric > 0) {
    return fmtDate(new Date(numeric * 1000).toISOString(), true)
  }
  return fmtDate(raw, true)
}

function sentimentSnippet(post: SentimentPost) {
  return post.selftext_snippet || '暂无正文摘录；仅保留标题、子版块、赞数、评论数与链接。'
}

function sentimentCommentsForPost(post: SentimentPost) {
  return sentimentCommentsByParent.value.get(String(post.id || '')) || []
}

function sentimentPlatformLabel(platform: string) {
  const labels: Record<string, string> = {
    reddit: 'Reddit',
    bilibili: 'B站',
    xiaohongshu: '小红书',
    xueqiu: '雪球',
    unknown: '未知平台',
  }
  return labels[platform] || platform
}

function sentimentPlatformRank(platform: string) {
  const ranks: Record<string, number> = {
    reddit: 1,
    bilibili: 2,
    xiaohongshu: 3,
    xueqiu: 4,
  }
  return ranks[platform] || 99
}

function sentimentCommunityLabel(post: SentimentPost) {
  if (post.platform === 'reddit') return `r/${post.subreddit || 'unknown'}`
  return post.subreddit || sentimentPlatformLabel(post.platform)
}

function voiceLabel(voice: string) {
  const labels: Record<string, string> = {
    media: '媒体',
    academic: '学界',
    sentiment: '民间',
  }
  return labels[voice] || voice
}

function collectSummary(collect: SearchResponse['collect'] | null) {
  if (!collect) return ''
  const sourcePart = collect.source_count !== undefined ? `，覆盖 ${collect.source_count} 个来源` : ''
  const span = collect.time_span?.start && collect.time_span?.end
    ? `，时间跨度 ${fmtDate(collect.time_span.start)} 至 ${fmtDate(collect.time_span.end)}`
    : ''
  return `采集 ${collect.raw} 条，保留 ${collect.kept} 条，新增 ${collect.new_articles} 篇${sourcePart}${span}。`
}

function countryFlag(code: string) {
  if (!/^[A-Z]{2}$/.test(code)) return code
  return String.fromCodePoint(...[...code].map((char) => char.charCodeAt(0) + 127397))
}

function topStanceEntries(country: CountryCompareCountry) {
  return Object.entries(country.stance_distribution)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-CN'))
    .slice(0, 5)
}

function outletSummary(country: CountryCompareCountry) {
  if (!country.outlets.length) return '暂无本地媒体'
  return country.outlets.slice(0, 5).join('、')
}

function countryCoverageNote(country: CountryCompareCountry) {
  if (country.article_count > 0) return ''
  return country.is_party ? '当事方，暂无本地媒体报道' : '暂无本地媒体报道'
}

function readableError(err: unknown) {
  if (isNetworkError(err)) {
    return '无法连接到后端服务'
  }
  return errorMessage(err)
}
</script>

<template>
  <main class="shell">
    <section class="topbar">
      <div>
        <p class="eyebrow">Dossier Intelligence</p>
        <h1>事件搜索与发展时间轴</h1>
      </div>
      <select v-model="selectedTopicId" class="topic-select" aria-label="选择专题">
        <option v-for="topic in topics" :key="topic.id" :value="topic.id">
          #{{ topic.id }} {{ topic.name }}
        </option>
      </select>
    </section>

    <section class="search-panel">
      <div>
        <p class="eyebrow">Search To Collect</p>
        <h2>输入一个事件线索，点击后再采集与分析</h2>
      </div>
      <div class="search-action">
        <input
          v-model="eventSearch"
          class="event-input"
          placeholder="例如：美伊战争、DeepSeek、红海危机"
          @keyup.enter="runEventSearch"
        />
        <button :disabled="searching" @click="runEventSearch">
          {{ searching ? '任务执行中...' : '搜集并生成时间轴' }}
        </button>
      </div>
      <p v-if="activeJobId" class="search-message">当前任务：{{ activeJobId.slice(0, 8) }}</p>
      <p v-if="searchMessage" class="search-message">{{ searchMessage }}</p>
      <div v-if="searchSteps.length" class="step-list">
        <span v-for="step in searchSteps" :key="step.key" :class="`step-${step.status}`">
          {{ step.label }} · {{ stepStatusText(step.status) }}
        </span>
      </div>
      <div v-if="searchWarnings.length" class="warning-list">
        <p v-for="warning in searchWarnings" :key="warning">{{ warning }}</p>
      </div>
      <div v-if="collectDiagnostics?.requests?.length" class="collect-diagnostics">
        <div class="evidence-header">
          <strong>采集诊断</strong>
          <span>{{ collectSummary(collectDiagnostics) }}</span>
        </div>
        <article v-for="request in collectDiagnostics.requests" :key="request.id">
          <b>{{ request.collector }}</b>
          <span>{{ request.query }}</span>
          <em>{{ request.raw_count }} 条返回 / {{ request.kept_count }} 条保留</em>
          <small v-if="request.error">{{ request.error }}</small>
        </article>
      </div>
      <div v-if="canRerunJob(terminalJob)" class="rerun-panel">
        <span>任务 {{ terminalJob?.id.slice(0, 8) }} {{ stepStatusText(terminalJob?.status || '') }}。</span>
        <button type="button" class="ghost-button" :disabled="searching" @click="rerunTerminalJob">
          重新运行
        </button>
      </div>
    </section>

    <section v-if="error" class="notice error">
      后端暂时不可用：{{ error }}。需要先运行
      <code>uvicorn app.api:app --app-dir backend --reload</code>
    </section>

    <section v-else-if="loading" class="notice">正在读取本地专题库...</section>

    <section v-else-if="!selectedTopic" class="notice">
      还没有专题。可以先搜索一个事件线索，或运行 <code>python backend/cli.py init-seeds</code>。
    </section>

    <template v-else>
      <section class="summary-band">
        <div class="topic-copy">
          <p class="status">{{ selectedTopic.status }} · {{ analysisModeLabel }}</p>
          <h2>{{ selectedTopic.name }}</h2>
          <p class="description">
            关键节点不再固定为 14 个。系统按权威来源、报道扩散、未来影响信号、持续时间和主题相关度排序，展示当前最值得关注的事件链。
          </p>
          <div class="deep-actions">
            <button type="button" class="cross-primary-button" :disabled="crossSynthesisAnalyzing" @click="runCrossSynthesis">
              {{ crossSynthesisAnalyzing ? '三方对照生成中...' : hasCrossSynthesis ? '刷新三方对照' : '三方对照' }}
            </button>
            <button type="button" class="ghost-button" :disabled="academicAnalyzing" @click="runAcademicAnalysis">
              {{ academicAnalyzing ? '学界分析中...' : '学界视角' }}
            </button>
            <button type="button" class="ghost-button" :disabled="sentimentAnalyzing" @click="runSentimentAnalysis">
              {{ sentimentAnalyzing ? '民间情绪分析中...' : '民间情绪' }}
            </button>
            <button type="button" :disabled="deepAnalyzing" @click="runDeepAnalysis">
              {{ deepAnalyzing ? '深度分析中...' : '深度分析（LLM）' }}
            </button>
            <span>{{ hasLlmAnalysis ? '当前展示 LLM 生成结果' : '当前展示本地规则结果' }}</span>
          </div>
          <p v-if="activeDeepJobId" class="search-message">深度任务：{{ activeDeepJobId.slice(0, 8) }}</p>
          <p v-if="deepMessage" class="search-message">{{ deepMessage }}</p>
          <div v-if="deepSteps.length" class="step-list deep-step-list">
            <span v-for="step in deepSteps" :key="step.key" :class="`step-${step.status}`">
              {{ step.label }} · {{ stepStatusText(step.status) }}
            </span>
          </div>
          <p v-if="activeCrossSynthesisJobId" class="search-message">三方对照任务：{{ activeCrossSynthesisJobId.slice(0, 8) }}</p>
          <p v-if="crossSynthesisMessage" class="search-message">{{ crossSynthesisMessage }}</p>
          <p v-if="crossSynthesisError" class="search-message academic-error">{{ crossSynthesisError }}</p>
          <div v-if="crossSynthesisSteps.length" class="step-list deep-step-list">
            <span v-for="step in crossSynthesisSteps" :key="step.key" :class="`step-${step.status}`">
              {{ step.label }} · {{ stepStatusText(step.status) }}
            </span>
          </div>
          <p v-if="activeAcademicJobId" class="search-message">学界任务：{{ activeAcademicJobId.slice(0, 8) }}</p>
          <p v-if="academicMessage" class="search-message">{{ academicMessage }}</p>
          <p v-if="academicError" class="search-message academic-error">{{ academicError }}</p>
          <div v-if="academicSteps.length" class="step-list deep-step-list">
            <span v-for="step in academicSteps" :key="step.key" :class="`step-${step.status}`">
              {{ step.label }} · {{ stepStatusText(step.status) }}
            </span>
          </div>
          <p v-if="activeSentimentJobId" class="search-message">民间情绪任务：{{ activeSentimentJobId.slice(0, 8) }}</p>
          <p v-if="sentimentMessage" class="search-message">{{ sentimentMessage }}</p>
          <p v-if="sentimentError" class="search-message academic-error">{{ sentimentError }}</p>
          <div v-if="sentimentSteps.length" class="step-list deep-step-list">
            <span v-for="step in sentimentSteps" :key="step.key" :class="`step-${step.status}`">
              {{ step.label }} · {{ stepStatusText(step.status) }}
            </span>
          </div>
          <div class="chips">
            <span v-for="term in selectedTopic.queries" :key="term">{{ term }}</span>
          </div>
        </div>

        <div class="metrics">
          <div>
            <strong>{{ selectedTopic.article_count }}</strong>
            <span>报道</span>
          </div>
          <div>
            <strong>{{ selectedTopic.source_count }}</strong>
            <span>来源</span>
          </div>
          <div>
            <strong>{{ majorEvents.length }}</strong>
            <span>关键节点</span>
          </div>
          <div>
            <strong>{{ fmtDate(selectedTopic.latest_published_at) }}</strong>
            <span>最新报道</span>
          </div>
        </div>
      </section>

      <nav class="workspace-tabs" aria-label="专题视图导航">
        <button
          v-for="tab in workspaceTabs"
          :key="tab.key"
          type="button"
          :class="{ active: activeWorkspaceTab === tab.key, featured: tab.key === 'cross' }"
          @click="activeWorkspaceTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>

      <section class="workspace">
        <section :class="['feed-pane', { 'tab-pane-wide': activeWorkspaceTab !== 'media' }]">
          <template v-if="activeWorkspaceTab === 'media'">
          <div class="pane-header">
            <div>
              <p class="eyebrow">Event Timeline</p>
              <h2>事件发展轴</h2>
            </div>
            <input v-model="query" class="search" placeholder="筛选报道标题、来源、摘要" />
          </div>

          <p v-if="localLoading" class="muted">正在用本地规则计算重大事件...</p>
          <div v-else-if="majorEvents.length" class="timeline-visual">
            <article
              v-for="(event, index) in majorEvents"
              :key="`${event.date}-${event.title_zh}`"
              :class="['timeline-item', { active: index === selectedEventIndex, expanded: index === expandedTimelineIndex }]"
            >
              <button class="timeline-node" type="button" @click="toggleTimelineEvent(index)">
                <span class="node-dot" />
                <time>{{ fmtDate(event.date) }}</time>
                <strong>{{ event.title_zh }}</strong>
                <em>{{ hasLlmAnalysis ? 'LLM 生成' : `${importanceText(event)} · ${coverageText(event)}` }}</em>
              </button>
              <div v-if="index === expandedTimelineIndex" class="timeline-inline-detail">
                <p>{{ event.summary_zh }}</p>
                <div class="event-tags compact-tags">
                  <span v-if="hasLlmAnalysis" class="llm-badge">LLM 生成</span>
                  <span>{{ event.category || '进展/报道' }}</span>
                  <span>{{ event.article_count }} 篇报道</span>
                  <span>{{ event.source_count }} 个来源</span>
                  <span>{{ event.stance }}</span>
                </div>
                <div v-if="event.selection_basis?.length" class="basis-list">
                  <strong>入选依据</strong>
                  <span v-for="basis in event.selection_basis" :key="basis">{{ basis }}</span>
                </div>
                <div v-if="event.sources?.length" class="source-list">
                  <strong>主要来源</strong>
                  <span v-for="source in event.sources" :key="source.name">
                    {{ source.name }} {{ source.count }} · {{ source.tier_label || '其他来源' }}
                  </span>
                </div>
                <p v-if="event.category_reason" class="event-reason">
                  阶段依据：{{ event.category_reason }}
                </p>
              </div>
            </article>
          </div>
          <p v-else class="muted">目前文章还不足以聚合出关键节点。请搜索并采集更多报道。</p>

          <article v-if="selectedEvent" class="event-detail">
            <div class="event-title-row">
              <div>
                <p class="eyebrow">Selected Node</p>
                <h2>{{ selectedEvent.title_zh }}</h2>
              </div>
              <div class="event-actions">
                <span class="score">{{ hasLlmAnalysis ? 'LLM 生成' : `${importanceText(selectedEvent)} · ${coverageText(selectedEvent)}` }}</span>
                <button
                  type="button"
                  class="ghost-button country-trigger"
                  :disabled="countryCompareLoading"
                  @click="loadCountryCompareForSelectedEvent"
                >
                  {{ countryCompareLoading ? '读取中...' : '各国怎么报道' }}
                </button>
              </div>
            </div>
            <p>{{ selectedEvent.summary_zh }}</p>
            <div class="event-tags">
              <span v-if="hasLlmAnalysis" class="llm-badge">LLM 生成</span>
              <span>{{ selectedEvent.category || '进展/报道' }}</span>
              <span>{{ importanceText(selectedEvent) }}</span>
              <span>{{ coverageText(selectedEvent) }}</span>
              <span>{{ selectedEvent.source_count }} 个来源</span>
              <span>{{ selectedEvent.article_count }} 篇报道</span>
              <span>{{ selectedEvent.stance }}</span>
              <span v-if="selectedEvent.evidence?.date_span_days">
                持续 {{ selectedEvent.evidence.date_span_days }} 天
              </span>
            </div>
            <p v-if="selectedEvent.category_reason" class="event-reason">
              阶段依据：{{ selectedEvent.category_reason }}
            </p>
            <p v-if="!hasLlmAnalysis" class="event-caveat">
              证据范围：当前仅使用标题、摘要、来源、发布时间和链接进行本地规则判断，不等同于全文事实核查。
            </p>
            <p v-else class="event-caveat llm-caveat">
              证据范围：该节点由 LLM 基于已富化报道综合生成，仍应回到原始报道核对事实与上下文。
            </p>

            <div v-if="selectedEvent.selection_basis?.length" class="basis-list">
              <strong>入选依据</strong>
              <span v-for="basis in selectedEvent.selection_basis" :key="basis">{{ basis }}</span>
            </div>

            <div v-if="selectedEvent.location_signals?.length" class="basis-list">
              <strong>地点线索</strong>
              <span v-for="place in selectedEvent.location_signals" :key="place.term">
                {{ place.term }} {{ place.count }}
              </span>
            </div>

            <div v-if="selectedEvent.sources?.length" class="source-list">
              <strong>主要来源</strong>
              <span v-for="source in selectedEvent.sources" :key="source.name">
                {{ source.name }} {{ source.count }} · {{ source.tier_label || '其他来源' }}
              </span>
            </div>

            <div v-if="selectedEvent.source_tiers?.length" class="source-list">
              <strong>来源层级</strong>
              <span v-for="tier in selectedEvent.source_tiers" :key="tier.key">
                {{ tier.label }} {{ tier.count }}
              </span>
            </div>

            <div v-if="selectedEvent.source_matrix?.length" class="source-matrix">
              <div class="evidence-header">
                <strong>来源矩阵</strong>
                <span>显示 {{ visibleSourceMatrix.length }} / {{ selectedEvent.source_matrix.length }} 个来源</span>
              </div>
              <div class="source-matrix-tools">
                <button type="button" class="ghost-button" @click="showAuthoritySources">权威来源</button>
                <button type="button" class="ghost-button" @click="showEarliestSources">首见来源</button>
                <button type="button" class="ghost-button" @click="showMostCoveredSources">报道最多</button>
                <label>
                  <span>层级</span>
                  <select v-model="sourceTierFilter" aria-label="来源层级筛选">
                    <option v-for="option in sourceTierOptions" :key="option.key" :value="option.key">
                      {{ option.label }}
                    </option>
                  </select>
                </label>
                <label>
                  <span>排序</span>
                  <select v-model="sourceMatrixSort" aria-label="来源矩阵排序">
                    <option value="tier">来源层级</option>
                    <option value="first">首见时间</option>
                    <option value="count">报道数量</option>
                    <option value="stance">主导立场</option>
                  </select>
                </label>
              </div>
              <div class="source-matrix-table">
                <div class="source-matrix-head">
                  <span>来源</span>
                  <span>首见时间</span>
                  <span>分类/立场</span>
                  <span>报道</span>
                </div>
                <article v-for="source in visibleSourceMatrix" :key="source.source">
                  <div>
                    <strong>{{ source.source }}</strong>
                    <small>{{ source.tier_label || '其他来源' }}</small>
                  </div>
                  <time>{{ fmtDate(source.first_published_at, true) }}</time>
                  <span>{{ source.dominant_category || '行动进展' }} · {{ source.dominant_stance || '中性观察' }}</span>
                  <b>{{ source.article_count }}</b>
                  <p>{{ source.representative_title }}</p>
                </article>
                <p v-if="!visibleSourceMatrix.length" class="source-matrix-empty">当前筛选下没有来源。</p>
              </div>
            </div>

            <div v-if="selectedEvent.evidence?.first_sources?.length" class="first-source-list">
              <strong>首批来源</strong>
              <article v-for="source in selectedEvent.evidence.first_sources" :key="`${source.name}-${source.title}`">
                <span>{{ fmtDate(source.published_at, true) }}</span>
                <b>{{ source.name }}</b>
                <em>{{ source.tier_label || '其他来源' }}</em>
                <p>{{ source.title }}</p>
              </article>
            </div>

            <div v-if="selectedEvent.evidence_articles?.length" class="evidence-list">
              <div class="evidence-header">
                <strong>证据报道</strong>
                <span>展示前 {{ selectedEvent.evidence_articles.length }} 篇关联报道</span>
              </div>
              <article v-for="article in selectedEvent.evidence_articles" :key="article.id">
                <div>
                  <time>{{ fmtDate(article.published_at, true) }}</time>
                  <span>{{ article.source || '未知来源' }}</span>
                  <span>{{ article.collector || 'unknown' }}</span>
                  <span>{{ article.category || '行动进展' }}</span>
                  <span>相关度 {{ percent(article.relevance) }}</span>
                </div>
                <h3>
                  <a :href="article.url" target="_blank" rel="noreferrer">{{ article.title }}</a>
                </h3>
                <p>{{ evidenceSnippet(article) }}</p>
              </article>
            </div>

            <section class="country-compare-panel">
              <div class="evidence-header">
                <div>
                  <strong>各国怎么报道</strong>
                  <span v-if="hasCountryCompare">
                    {{ visibleCountryCompare?.article_scope_count || 0 }} 篇关联报道 ·
                    另有 {{ visibleCountryCompare?.unmapped_count || 0 }} 篇未识别来源国
                  </span>
                  <span v-else>按当前事件的关联报道生成多国媒体对比</span>
                </div>
                <button
                  type="button"
                  class="ghost-button"
                  :disabled="countryCompareLoading"
                  @click="loadCountryCompareForSelectedEvent"
                >
                  {{ hasCountryCompare ? '刷新对比' : '生成对比' }}
                </button>
              </div>

              <p v-if="countryCompareError" class="country-compare-error">
                {{ countryCompareError }}
              </p>
              <p v-else-if="countryCompareLoading" class="muted">正在读取多国对比...</p>

              <template v-else-if="visibleCountryCompare">
                <p v-if="visibleCountryCompare.unmapped_count > 0" class="coverage-gap">
                  另有 {{ visibleCountryCompare.unmapped_count }} 篇报道暂未能根据媒体名识别来源国家。
                </p>

                <div class="first-reporters">
                  <div class="evidence-header">
                    <strong>谁先报</strong>
                    <span>{{ firstReporterTimeline.length }} 条首报线索</span>
                  </div>
                  <ol v-if="firstReporterTimeline.length">
                    <li v-for="reporter in firstReporterTimeline" :key="`${reporter.article_id}-${reporter.outlet}`">
                      <time>{{ fmtDate(reporter.date, true) }}</time>
                      <b>{{ countryFlag(reporter.country_code) }} {{ reporter.country_name }}</b>
                      <span>{{ reporter.outlet }}</span>
                      <p>{{ reporter.title }}</p>
                    </li>
                  </ol>
                  <p v-else class="source-matrix-empty">当前事件没有可排序的首报记录。</p>
                </div>

                <div class="country-card-grid">
                  <article
                    v-for="country in countryCards"
                    :key="country.code"
                    :class="['country-card', { party: country.is_party, empty: country.article_count === 0 }]"
                  >
                    <div class="country-card-head">
                      <div>
                        <strong>{{ countryFlag(country.code) }} {{ country.name }}</strong>
                        <small>{{ country.code }}</small>
                      </div>
                      <span>{{ country.article_count }} 篇</span>
                    </div>
                    <div class="country-badges">
                      <span v-if="country.is_party">当事方</span>
                      <span v-if="country.is_g20">G20</span>
                      <span v-if="country.party_mention_count">提及 {{ country.party_mention_count }}</span>
                    </div>
                    <p v-if="countryCoverageNote(country)" class="country-empty-note">
                      {{ countryCoverageNote(country) }}
                    </p>
                    <div v-if="topStanceEntries(country).length" class="stance-pills country-stances">
                      <span v-for="[label, count] in topStanceEntries(country)" :key="label">
                        {{ label }} {{ count }}
                      </span>
                    </div>
                    <p class="country-outlets">
                      <b>媒体</b>
                      {{ outletSummary(country) }}
                    </p>
                    <p v-if="country.first_report" class="country-first-report">
                      <b>首报</b>
                      {{ fmtDate(country.first_report.date, true) }} · {{ country.first_report.outlet }}
                    </p>
                    <ul v-if="country.sample_titles.length" class="country-samples">
                      <li v-for="title in country.sample_titles.slice(0, 3)" :key="title">{{ title }}</li>
                    </ul>
                  </article>
                </div>
              </template>
            </section>

            <div class="breakdown-grid">
              <div v-for="item in selectedEvent.score_breakdown" :key="item.label">
                <div class="breakdown-head">
                  <strong>{{ item.label }}</strong>
                  <span>{{ percent(item.value) }}</span>
                </div>
                <i :style="{ width: percent(item.value) }" />
                <p>{{ item.reason }}</p>
              </div>
            </div>
          </article>

          <section class="criteria-panel">
            <p class="eyebrow">Selection Criteria</p>
            <h2>关键节点判定标准</h2>
            <div v-if="criteria.length" class="criteria-grid">
              <article v-for="item in criteria" :key="item.key">
                <strong>{{ item.label }} · {{ percent(item.weight) }}</strong>
                <p>{{ item.description }}</p>
              </article>
            </div>
            <p v-else-if="hasLlmAnalysis" class="muted">
              当前时间线由 LLM 深度分析生成，综合依据来自已富化报道的标题、摘要、来源、时间与单篇立场判断。
            </p>
          </section>
          </template>

          <section v-if="activeWorkspaceTab === 'cross'" class="wide-panel cross-synthesis-panel">
            <div class="pane-header compact">
              <div>
                <p class="eyebrow">Cross Synthesis</p>
                <h2>三方对照</h2>
              </div>
              <button type="button" class="cross-primary-button" :disabled="crossSynthesisAnalyzing" @click="runCrossSynthesis">
                {{ crossSynthesisAnalyzing ? '生成中...' : hasCrossSynthesis ? '刷新三方对照' : '生成三方对照' }}
              </button>
            </div>

            <div class="cross-synthesis-note">
              <strong>媒体 / 学界 / 民间的交叉校验</strong>
              <span>点击后会依次尝试更新媒体、学界、民间声部；单个声部失败不会阻断最终综合。</span>
              <span>综合共识、矛盾、盲区、机制链条和批判提示；民间情绪始终按非事实源处理。</span>
            </div>

            <p v-if="activeCrossSynthesisJobId" class="search-message">三方对照任务：{{ activeCrossSynthesisJobId.slice(0, 8) }}</p>
            <p v-if="crossSynthesisMessage" class="search-message">{{ crossSynthesisMessage }}</p>
            <div v-if="crossSynthesisSteps.length" class="step-list deep-step-list">
              <span v-for="step in crossSynthesisSteps" :key="step.key" :class="`step-${step.status}`">
                {{ step.label }} · {{ stepStatusText(step.status) }}
              </span>
            </div>

            <div v-if="hasCrossSynthesis || crossSynthesisSteps.length" class="cross-chain-status">
              <article v-for="item in crossChainItems" :key="item.key" :class="`chain-${item.status}`">
                <strong>{{ item.label }}</strong>
                <span>{{ stepStatusText(item.status) }}</span>
                <p v-if="item.error">{{ item.error }}</p>
              </article>
            </div>

            <p v-if="crossSynthesisLoading" class="muted">正在读取三方对照...</p>
            <p v-else-if="crossSynthesisError" class="country-compare-error">{{ crossSynthesisError }}</p>

            <template v-else>
              <div class="voice-badges">
                <span v-if="!crossVoicesUsed.length">暂无可用声部</span>
                <span v-for="voice in crossVoicesUsed" :key="voice">{{ voiceLabel(voice) }}</span>
              </div>

              <div v-if="safeCrossSynthesisHtml" class="analysis markdown-body cross-synthesis-summary" v-html="safeCrossSynthesisHtml" />
              <p v-else class="muted">请先运行媒体/学界/民间分析，再生成三方对照。</p>
            </template>
          </section>

          <section v-if="activeWorkspaceTab === 'media'" class="wide-panel framing-panel">
            <div class="pane-header compact">
              <div>
                <p class="eyebrow">Framing</p>
                <h2>各方态度</h2>
              </div>
              <span v-if="hasLlmAnalysis" class="llm-badge">LLM 生成</span>
            </div>
            <div v-if="framing.length" class="framing-list wide-framing-list">
              <article v-for="item in framing" :key="`${item.party}-${item.stance}`">
                <span>{{ item.stance }}</span>
                <strong>{{ item.party }}</strong>
                <p>{{ item.summary_zh }}</p>
              </article>
            </div>
            <p v-else class="muted">还没有足够样本形成态度分组。</p>
          </section>

          <section v-if="activeWorkspaceTab === 'academic'" class="wide-panel academic-panel">
            <div class="pane-header compact">
              <div>
                <p class="eyebrow">Academic Layer</p>
                <h2>学界视角</h2>
              </div>
              <button type="button" class="ghost-button" :disabled="academicAnalyzing" @click="runAcademicAnalysis">
                {{ academicAnalyzing ? '分析中...' : hasAcademicLayer ? '刷新学界层' : '生成学界层' }}
              </button>
            </div>

            <p v-if="activeAcademicJobId" class="search-message">学界任务：{{ activeAcademicJobId.slice(0, 8) }}</p>
            <p v-if="academicMessage" class="search-message">{{ academicMessage }}</p>
            <div v-if="academicSteps.length" class="step-list deep-step-list">
              <span v-for="step in academicSteps" :key="step.key" :class="`step-${step.status}`">
                {{ step.label }} · {{ stepStatusText(step.status) }}
              </span>
            </div>

            <p v-if="academicLoading" class="muted">正在读取学界层...</p>
            <p v-else-if="academicError" class="country-compare-error">{{ academicError }}</p>

            <template v-else>
              <div class="academic-metrics">
                <div>
                  <strong>{{ academicPapers.length }}</strong>
                  <span>论文</span>
                </div>
                <div>
                  <strong>{{ academicCitationEdges.length }}</strong>
                  <span>内部引用</span>
                </div>
                <div>
                  <strong>{{ academicSchools.length }}</strong>
                  <span>学派/主题群</span>
                </div>
                <div>
                  <strong>{{ academicFoundationalPapers.length }}</strong>
                  <span>奠基论文</span>
                </div>
              </div>

              <p v-if="!academicPapers.length" class="muted">
                暂无学界论文。点击“生成学界层”后会从 OpenAlex 拉取相关论文并构建引用图。
              </p>

              <div v-if="safeAcademicSummaryHtml" class="analysis markdown-body academic-summary" v-html="safeAcademicSummaryHtml" />
              <p v-else class="muted">暂无学界综合摘要。</p>

              <div v-if="academicFoundationalPapers.length" class="academic-section">
                <div class="evidence-header">
                  <strong>奠基论文</strong>
                  <span>按样本内部入度与被引量排序</span>
                </div>
                <div class="academic-paper-grid">
                  <article v-for="paper in academicFoundationalPapers" :key="paper.openalex_id" class="academic-paper foundation">
                    <div>
                      <span class="llm-badge">奠基</span>
                      <b>{{ paper.year || '未知年份' }}</b>
                      <b>被引 {{ paper.cited_by_count }}</b>
                      <b>内部引用 {{ paper.internal_citations }}</b>
                    </div>
                    <h3>
                      <a :href="academicPaperUrl(paper)" target="_blank" rel="noreferrer">{{ paper.title }}</a>
                    </h3>
                  </article>
                </div>
              </div>

              <div v-if="academicSchools.length" class="academic-section">
                <div class="evidence-header">
                  <strong>学派/主题群</strong>
                  <span>{{ academicSchools.length }} 组</span>
                </div>
                <div class="academic-school-grid">
                  <article v-for="school in academicSchools" :key="school.name" class="academic-school">
                    <div class="country-card-head">
                      <strong>{{ school.name }}</strong>
                      <span>{{ school.paper_count }} 篇</span>
                    </div>
                    <p v-if="school.years.length">{{ school.years[0] }} - {{ school.years[school.years.length - 1] }}</p>
                    <div v-if="school.concepts.length" class="country-badges">
                      <span v-for="concept in school.concepts.slice(0, 5)" :key="concept">{{ concept }}</span>
                    </div>
                    <ul v-if="school.top_papers.length" class="country-samples">
                      <li v-for="paper in school.top_papers.slice(0, 3)" :key="paper.openalex_id">
                        {{ paper.title }} · {{ paper.year || '未知年份' }}
                      </li>
                    </ul>
                  </article>
                </div>
              </div>

              <div class="academic-section">
                <div class="evidence-header">
                  <strong>引用图</strong>
                  <span>{{ academicCitationEdges.length }} 条样本内部引用</span>
                </div>
                <p v-if="!academicCitationEdges.length" class="source-matrix-empty">暂无内部引用关系。</p>
                <div v-else class="academic-edge-list">
                  <span v-for="edge in academicCitationEdges.slice(0, 16)" :key="`${edge.citing_openalex_id}-${edge.cited_openalex_id}`">
                    {{ edge.citing_openalex_id.split('/').pop() }} → {{ edge.cited_openalex_id.split('/').pop() }}
                  </span>
                </div>
              </div>

              <div v-if="academicPapers.length" class="academic-section">
                <div class="evidence-header">
                  <strong>论文列表</strong>
                  <span>{{ academicPapers.length }} 篇</span>
                </div>
                <div class="academic-paper-list">
                  <article v-for="paper in academicPapers" :key="paper.openalex_id" class="academic-paper">
                    <div>
                      <span v-if="isFoundationalPaper(paper)" class="llm-badge">
                        奠基 {{ foundationalStats(paper)?.internal_citations || 0 }}
                      </span>
                      <b>{{ paper.year || '未知年份' }}</b>
                      <b>被引 {{ paper.cited_by_count }}</b>
                      <span>{{ academicVenue(paper) }}</span>
                    </div>
                    <h3>
                      <a :href="academicPaperUrl(paper)" target="_blank" rel="noreferrer">{{ paper.title }}</a>
                    </h3>
                    <p>{{ academicAuthors(paper) }}</p>
                  </article>
                </div>
              </div>
            </template>
          </section>

          <section v-if="activeWorkspaceTab === 'sentiment'" class="wide-panel sentiment-panel">
            <div class="pane-header compact">
              <div>
                <p class="eyebrow">Public Sentiment</p>
                <h2>民间情绪</h2>
              </div>
              <button type="button" class="ghost-button" :disabled="sentimentAnalyzing" @click="runSentimentAnalysis">
                {{ sentimentAnalyzing ? '分析中...' : hasSentimentLayer ? '刷新民间情绪' : '生成民间情绪' }}
              </button>
            </div>

            <div class="sentiment-warning">
              <strong>民间情绪 · 最该被怀疑的一角</strong>
              <span>Reddit 样本以情绪、站队和看热闹为主；高赞≠事实，只能作为待核实线索。</span>
            </div>

            <p v-if="activeSentimentJobId" class="search-message">民间情绪任务：{{ activeSentimentJobId.slice(0, 8) }}</p>
            <p v-if="sentimentMessage" class="search-message">{{ sentimentMessage }}</p>
            <div v-if="sentimentSteps.length" class="step-list deep-step-list">
              <span v-for="step in sentimentSteps" :key="step.key" :class="`step-${step.status}`">
                {{ step.label }} · {{ stepStatusText(step.status) }}
              </span>
            </div>

            <p v-if="sentimentLoading" class="muted">正在读取民间情绪层...</p>
            <p v-else-if="sentimentError" class="country-compare-error">{{ sentimentError }}</p>

            <template v-else>
                <div class="academic-metrics sentiment-metrics">
                <div>
                  <strong>{{ sentimentPostItems.length }}</strong>
                  <span>平台帖子</span>
                </div>
                <div>
                  <strong>{{ sentimentCommentItems.length }}</strong>
                  <span>高赞评论</span>
                </div>
                <div>
                  <strong>{{ sentimentPlatformLabels || '待生成' }}</strong>
                  <span>覆盖平台</span>
                </div>
                <div>
                  <strong>{{ sentimentLayer?.queries?.reddit || sentimentLayer?.query || '待生成' }}</strong>
                  <span>Reddit 英文查询</span>
                </div>
                <div>
                  <strong>{{ sentimentLayer?.queries?.chinese || selectedTopic.name }}</strong>
                  <span>中文平台查询</span>
                </div>
              </div>

              <div v-if="sentimentLayer?.errors?.length" class="sentiment-platform-errors">
                <p v-for="item in sentimentLayer.errors" :key="`${item.platform}-${item.error}`">
                  {{ sentimentPlatformLabel(item.platform) }} 暂不可用：{{ item.error }}
                </p>
              </div>

              <p v-if="!sentimentPosts.length" class="muted">
                暂无民间平台样本。点击“生成民间情绪”会调用本地 OpenCLI；如果 Chrome、扩展或平台登录不可用，错误会显示在这里。
              </p>

              <div v-if="safeSentimentSummaryHtml" class="analysis markdown-body academic-summary sentiment-summary" v-html="safeSentimentSummaryHtml" />
              <p v-else class="muted">暂无民间情绪摘要。</p>

              <div v-if="sentimentPosts.length" class="academic-section">
                <div class="evidence-header">
                  <strong>多平台讨论样本</strong>
                  <span>{{ sentimentPostItems.length }} 条帖子 · {{ sentimentCommentItems.length }} 条评论</span>
                </div>
                <div class="sentiment-platform-groups">
                  <section v-for="group in sentimentPlatformGroups" :key="group.platform" class="sentiment-platform-group">
                    <div class="country-card-head">
                      <strong>{{ group.label }}</strong>
                      <span>{{ group.posts.length }} 条</span>
                    </div>
                    <div class="sentiment-post-list">
                      <article v-for="post in group.posts" :key="`${post.platform}-${post.url}-${post.title}`" class="sentiment-post">
                        <div>
                          <span>{{ sentimentCommunityLabel(post) }}</span>
                          <b>{{ post.score }} 赞</b>
                          <b>{{ post.num_comments }} 评论</b>
                          <time>{{ sentimentPostDate(post) }}</time>
                        </div>
                        <h3>
                          <a :href="post.url" target="_blank" rel="noreferrer">{{ post.title || '未命名讨论' }}</a>
                        </h3>
                        <p>{{ sentimentSnippet(post) }}</p>
                        <small>作者：{{ post.author || 'unknown' }} · {{ group.label }} 情绪样本，非事实来源</small>
                        <details v-if="sentimentCommentsForPost(post).length" class="sentiment-comments">
                          <summary>{{ sentimentCommentsForPost(post).length }} 条高赞评论</summary>
                          <article
                            v-for="comment in sentimentCommentsForPost(post)"
                            :key="`${comment.platform}-${comment.id}-${comment.title}`"
                            class="sentiment-comment"
                          >
                            <div>
                              <span>评论</span>
                              <b>{{ comment.score }} 赞</b>
                              <time>{{ sentimentPostDate(comment) }}</time>
                            </div>
                            <p>{{ sentimentSnippet(comment) }}</p>
                            <small>作者：{{ comment.author || 'unknown' }} · 评论样本，非事实来源</small>
                          </article>
                        </details>
                      </article>
                    </div>
                  </section>
                </div>
              </div>
            </template>
          </section>

          <section v-if="activeWorkspaceTab === 'llm'" class="wide-panel llm-panel">
            <div class="pane-header compact">
              <div>
                <p class="eyebrow">Deep Analysis</p>
                <h2>{{ hasLlmAnalysis ? 'LLM 批判分析' : '本地规则说明' }}</h2>
              </div>
              <div class="event-actions">
                <span v-if="hasLlmAnalysis" class="llm-badge">LLM 生成</span>
                <button type="button" :disabled="deepAnalyzing" @click="runDeepAnalysis">
                  {{ deepAnalyzing ? '深度分析中...' : '深度分析（LLM）' }}
                </button>
              </div>
            </div>

            <p v-if="activeDeepJobId" class="search-message">深度任务：{{ activeDeepJobId.slice(0, 8) }}</p>
            <p v-if="deepMessage" class="search-message">{{ deepMessage }}</p>
            <div v-if="deepSteps.length" class="step-list deep-step-list">
              <span v-for="step in deepSteps" :key="step.key" :class="`step-${step.status}`">
                {{ step.label }} · {{ stepStatusText(step.status) }}
              </span>
            </div>

            <div v-if="safeAnalysisHtml" class="analysis markdown-body llm-analysis-body" v-html="safeAnalysisHtml" />
            <div v-else-if="displayAnalysisText" class="analysis llm-analysis-body">
              <p>{{ displayAnalysisText }}</p>
            </div>
            <p v-else class="muted">{{ hasLlmAnalysis ? 'LLM 分析尚未生成。' : '本地分析尚未生成。' }}</p>
          </section>

          <template v-if="activeWorkspaceTab === 'media'">
          <div class="section-divider">
            <div>
              <p class="eyebrow">News Feed</p>
              <h2>原始报道流</h2>
            </div>
            <button class="ghost-button" @click="showArticles = !showArticles">
              {{ showArticles ? '收起报道' : `展开报道 (${totalArticles})` }}
            </button>
          </div>

          <template v-if="showArticles">
          <div class="mini-chart" aria-label="立场分布">
            <div v-for="group in stanceGroups" :key="group.name" class="bar-row">
              <span>{{ group.name }}</span>
              <div>
                <i :style="{ width: `${Math.max(8, (group.count / Math.max(1, articles.length)) * 100)}%` }" />
              </div>
              <b>{{ group.count }}</b>
            </div>
          </div>

          <div v-if="articleCategoryGroups.length" class="article-tools">
            <label>
              <span>报道分类</span>
              <select v-model="articleCategoryFilter" aria-label="报道功能分类筛选">
                <option v-for="option in articleCategoryOptions" :key="option.key" :value="option.key">
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>

          <p v-if="articleLoading" class="muted">正在加载报道...</p>
          <p v-else-if="!filteredArticles.length" class="muted">没有匹配的报道。</p>

          <details
            v-for="group in visibleArticleGroups"
            :key="group.category"
            class="article-group"
            open
          >
            <summary>
              <strong>{{ group.category }}</strong>
              <span>{{ group.items.length }} 篇报道</span>
            </summary>
            <article v-for="article in group.items" :key="article.id" class="article-row">
              <div class="article-main">
                <div class="article-meta">
                  <span>{{ fmtDate(article.published_at, true) }}</span>
                  <span>{{ article.source || '未知来源' }}</span>
                  <span>{{ article.source_lang || '未知语言' }}</span>
                  <span>{{ article.collector }}</span>
                  <span>{{ article.category || '行动进展' }}</span>
                </div>
                <h3>
                  <a :href="article.url" target="_blank" rel="noreferrer">{{ titleFor(article) }}</a>
                </h3>
                <p>{{ snippetFor(article) }}</p>
              </div>
              <aside>
                <strong>{{ percent(article.relevance) }}</strong>
                <span>{{ article.stance || (article.enriched ? '未标注' : '本地待判定') }}</span>
              </aside>
            </article>
          </details>
          </template>
          </template>
        </section>

        <aside v-if="activeWorkspaceTab === 'media'" class="insight-pane">
          <section>
            <div class="pane-header compact">
              <div>
                <p class="eyebrow">Entity Cloud</p>
                <h2>关键人物/名词</h2>
              </div>
            </div>
            <div v-if="entities.length" class="entity-groups">
              <article v-for="group in entityGroups" :key="group.kind">
                <strong>{{ group.label }}</strong>
                <div class="entity-list">
                  <button
                    v-for="word in group.items"
                    :key="word.term"
                    type="button"
                    class="entity-chip"
                    :style="{ opacity: 0.66 + word.weight * 0.34 }"
                    @click="query = word.term"
                  >
                    <span>{{ word.term }}</span>
                    <small>{{ word.count }}</small>
                  </button>
                </div>
              </article>
            </div>
            <div v-else-if="keywords.length" class="word-cloud">
              <span
                v-for="word in keywords"
                :key="word.term"
                :style="{ fontSize: keywordSize(word), opacity: 0.55 + word.weight * 0.45 }"
              >
                {{ word.term }}
              </span>
            </div>
            <p v-else class="muted">暂无关键实体。采集报道后会自动生成。</p>
          </section>

          <section>
            <div class="pane-header compact">
              <div>
                <p class="eyebrow">Attitude Shift</p>
                <h2>态度随时间变化</h2>
              </div>
            </div>
            <div v-if="stancePeriods.length" class="stance-evolution">
              <article v-for="period in stancePeriods" :key="period.period">
                <time>{{ period.period }}</time>
                <strong>{{ period.dominant_stance }}</strong>
                <div class="stance-pills">
                  <span v-for="(count, label) in period.counts" :key="label">
                    {{ label }} {{ count }}
                  </span>
                </div>
              </article>
            </div>
            <p v-else class="muted">需要更多带时间的报道才能观察态度变化。</p>
          </section>
        </aside>
      </section>
    </template>
  </main>
</template>
