<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  fetchArticlePerspective,
  fetchAutoRefreshStatus,
  fetchCognitionMarks,
  fetchCognitionProfile,
  fetchCountryCompare,
  fetchEventContrast,
  fetchSources,
  createSource,
  importSources,
  runAutoRefreshNow,
  saveCognitionMark,
  updateSource,
} from './api/dossierApi'
import AcademicPanel from './components/AcademicPanel.vue'
import CrossPanel from './components/CrossPanel.vue'
import DiscoveryPanel from './components/DiscoveryPanel.vue'
import LlmPanel from './components/LlmPanel.vue'
import MediaPanel from './components/MediaPanel.vue'
import SentimentPanel from './components/SentimentPanel.vue'
import { useDigQueue, digItemKey } from './composables/useDigQueue'
import { useDiscovery } from './composables/useDiscovery'
import { useEventWorkbench } from './composables/useEventWorkbench'
import { useJobRunner } from './composables/useJobRunner'
import { readableError, useTopicData } from './composables/useTopicData'
import type {
  AcademicFoundationalPaper,
  AcademicPaper,
  Article,
  ArticlePerspective,
  AutoRefreshStatus,
  CognitionLabel,
  CognitionMark,
  CognitionProfileItem,
  CountryCompare,
  CountryCompareCountry,
  DiscoverySeed,
  EventContrastPayload,
  EvidenceArticle,
  Keyword,
  LocalEvent,
  SearchResponse,
  SentimentPost,
  SourceRegistry,
} from './types/dossier'

const countryCompareLoading = ref(false)
const countryCompare = ref<CountryCompare | null>(null)
const countryCompareError = ref('')
const countryCompareEventKey = ref('')
const eventContrastLoading = ref(false)
const eventContrast = ref<EventContrastPayload | null>(null)
const eventContrastError = ref('')
const eventContrastEventKey = ref('')
const articlePerspectives = ref<Record<number, ArticlePerspective>>({})
const articlePerspectiveLoading = ref<Record<number, boolean>>({})
const articlePerspectiveErrors = ref<Record<number, string>>({})
const seedCognitionMarks = ref<Record<string, CognitionMark>>({})
const cognitionProfile = ref<CognitionProfileItem[]>([])
const cognitionMarkError = ref('')

type AppMode = 'workbench' | 'discovery'
const appMode = ref<AppMode>('discovery')
const appModes = [
  { key: 'workbench', label: '事件分析台' },
  { key: 'discovery', label: '今日情报台' },
] as const

const {
  report: discoveryReport,
  loading: discoveryLoading,
  analyzing: discoveryAnalyzing,
  loaded: discoveryLoaded,
  error: discoveryError,
  message: discoveryMessage,
  activeJobId: discoveryJobId,
  steps: discoverySteps,
  reports: discoveryReports,
  selectedRunId: selectedDiscoveryRunId,
  timelineTree: discoveryTimelineTree,
  safeReportHtml: discoverySafeHtml,
  hasReport: discoveryHasReport,
  seeds: discoverySeeds,
  loadLatest: loadLatestDiscovery,
  loadReport: loadDiscoveryReport,
  runDiscovery,
  distill: distillSeedTopic,
  stepStatusText: discoveryStepStatusText,
} = useDiscovery()

const workspaceTabs = [
  { key: 'media', label: '媒体' },
  { key: 'academic', label: '学界' },
  { key: 'sentiment', label: '民间情绪' },
  { key: 'cross', label: '三方对照' },
  { key: 'llm', label: 'LLM 深度分析' },
] as const

const {
  projects,
  topics,
  selectedTopicId,
  detail,
  localData,
  eventGraph,
  articles,
  totalArticles,
  loading,
  articleLoading,
  localLoading,
  error,
  selectedTopic,
  loadTopics,
  loadTopic,
  loadArticles,
  loadLocalEvents,
  loadEventGraph,
  saveProject,
  archiveProject,
  removeProject,
  saveTopic,
  archiveTopic,
  removeTopic,
} = useTopicData()

const showProjectManager = ref(false)
const activeManagerForm = ref<'project' | 'topic'>('topic')
const projectDraft = ref({
  id: 0,
  name: '',
  description: '',
})
const topicDraft = ref({
  id: 0,
  project_id: 0,
  name: '',
  description: '',
  queries: '',
})
const savingProject = ref(false)
const creatingTopic = ref(false)
const projectManagerError = ref('')
const sources = ref<SourceRegistry[]>([])
const sourceManagerLoading = ref(false)
const sourceManagerError = ref('')
const sourceBusy = ref<Record<number, boolean>>({})
const creatingSource = ref(false)
const importingSources = ref(false)
const sourceImportMessage = ref('')
const sourceDraft = ref({
  name: '',
  url: '',
  country: '',
  language: 'en',
  source_type: 'rss',
  quality_tier: 'user',
})
const sourceImportDraft = ref({
  text: '',
  country: '',
  language: 'en',
  source_type: 'rss',
  quality_tier: 'user',
})
const autoRefreshStatus = ref<AutoRefreshStatus | null>(null)
const autoRefreshLoading = ref(false)
const autoRefreshRunning = ref(false)
const autoRefreshError = ref('')
const staleTopicDays = 7
const sourceManagerStats = computed(() => {
  const enabled = sources.value.filter((source) => source.enabled).length
  const failedSources = sources.value.filter((source) => source.last_status === 'failed')
  const limitedSources = sources.value.filter((source) => isLimitedSource(source))
  const latestSuccess = sources.value
    .filter((source) => source.last_status === 'ok' && source.last_fetched_at)
    .sort((left, right) => {
      const leftTime = new Date(left.last_fetched_at || '').getTime()
      const rightTime = new Date(right.last_fetched_at || '').getTime()
      return rightTime - leftTime
    })[0]

  return {
    total: sources.value.length,
    enabled,
    failed: failedSources.length,
    limited: limitedSources.length,
    latestSuccessAt: latestSuccess?.last_fetched_at || null,
    failedNotes: failedSources
      .slice(0, 3)
      .map((source) => `${source.name}：${source.last_error || '最近采集失败，暂无详细原因'}`),
  }
})
const sourceCoverageMix = computed(() => ({
  tiers: countByLabel(
    sources.value.map((source) => source.quality_tier || 'unknown'),
    ['wire', 'professional', 'mainstream', 'newsletter', 'research', 'user'],
  ),
  types: countByLabel(sources.value.map((source) => source.source_type || 'unknown')),
}))
const topicFreshnessWarning = computed(() => {
  const latest = selectedTopic.value?.latest_published_at
  if (!latest) return ''
  const latestDate = new Date(latest)
  if (Number.isNaN(latestDate.getTime())) return ''
  const ageDays = Math.floor((Date.now() - latestDate.getTime()) / 86_400_000)
  if (ageDays < staleTopicDays) return ''
  return `最后采集时间是 ${fmtDate(latest)}，这只说明本地档案停在这里，不代表世界没有新报道。需要最新报道时请刷新采集。`
})
const autoRefreshSummary = computed(() => {
  const status = autoRefreshStatus.value
  if (!status) return ''
  const parts = [`自动刷新：${status.enabled ? '已开启' : '未开启'}`]
  if (status.running) parts.push('正在运行')
  if (status.last_finished_at) parts.push(`上次完成 ${fmtDate(status.last_finished_at, true)}`)
  else if (status.last_started_at) parts.push(`上次开始 ${fmtDate(status.last_started_at, true)}`)
  parts.push(`新闻刷新 ${status.news_refreshed} 个`)
  if (status.frontier_refreshed) parts.push('前沿日报已更新')
  if (status.skipped_active) parts.push(`跳过 ${status.skipped_active} 个活跃任务`)
  return parts.join(' · ')
})
const autoRefreshErrors = computed(() => {
  const status = autoRefreshStatus.value
  if (!status) return []
  return [status.last_error, ...(status.news_errors || [])].filter(Boolean)
})

function countByLabel(labels: string[], priority: string[] = []) {
  const counts = new Map<string, number>()
  for (const label of labels) {
    counts.set(label, (counts.get(label) || 0) + 1)
  }
  return [...counts.entries()]
    .sort((left, right) => {
      const leftPriority = priority.indexOf(left[0])
      const rightPriority = priority.indexOf(right[0])
      if (leftPriority >= 0 || rightPriority >= 0) {
        return (leftPriority >= 0 ? leftPriority : 999) - (rightPriority >= 0 ? rightPriority : 999)
      }
      return right[1] - left[1] || left[0].localeCompare(right[0], 'zh-CN')
    })
    .map(([label, count]) => `${label} ${count}`)
    .join('、')
}

function openNewTopic(projectId: number | null = null) {
  activeManagerForm.value = 'topic'
  topicDraft.value = {
    id: 0,
    project_id: projectId || projects.value[0]?.id || selectedTopic.value?.project_id || 0,
    name: '',
    description: '',
    queries: '',
  }
  projectDraft.value = { id: 0, name: '', description: '' }
  projectManagerError.value = ''
}

function openNewProject() {
  activeManagerForm.value = 'project'
  projectDraft.value = { id: 0, name: '', description: '' }
  topicDraft.value = { id: 0, project_id: 0, name: '', description: '', queries: '' }
  projectManagerError.value = ''
}

function editProjectDraft(project: { id: number; name: string; description: string }) {
  activeManagerForm.value = 'project'
  projectDraft.value = {
    id: project.id,
    name: project.name,
    description: project.description || '',
  }
  topicDraft.value = { id: 0, project_id: 0, name: '', description: '', queries: '' }
  projectManagerError.value = ''
}

function editTopicDraft(topic: {
  id: number
  project_id?: number | null
  name: string
  description: string
  queries: string[]
}) {
  activeManagerForm.value = 'topic'
  topicDraft.value = {
    id: topic.id,
    project_id: topic.project_id || projects.value[0]?.id || 0,
    name: topic.name,
    description: topic.description || '',
    queries: topic.queries.join('\n'),
  }
  projectDraft.value = { id: 0, name: '', description: '' }
  projectManagerError.value = ''
}

async function saveProjectDraft() {
  if (!projectDraft.value.name.trim() || savingProject.value) return
  savingProject.value = true
  projectManagerError.value = ''
  try {
    await saveProject({
      id: projectDraft.value.id || undefined,
      name: projectDraft.value.name.trim(),
      description: projectDraft.value.description.trim(),
    })
    projectDraft.value = { id: 0, name: '', description: '' }
    activeManagerForm.value = 'topic'
  } catch (err) {
    projectManagerError.value = readableError(err)
  } finally {
    savingProject.value = false
  }
}

async function saveTopicDraft() {
  if (!topicDraft.value.name.trim() || creatingTopic.value) return
  creatingTopic.value = true
  projectManagerError.value = ''
  try {
    const topic = await saveTopic({
      id: topicDraft.value.id || undefined,
      project_id: topicDraft.value.project_id || null,
      name: topicDraft.value.name.trim(),
      description: topicDraft.value.description.trim(),
      queries: topicDraft.value.queries
        .split(/\r?\n|,/)
        .map((item) => item.trim())
        .filter(Boolean),
    })
    selectedTopicId.value = topic.id
    topicDraft.value = { id: 0, project_id: topic.project_id || 0, name: '', description: '', queries: '' }
  } catch (err) {
    projectManagerError.value = readableError(err)
  } finally {
    creatingTopic.value = false
  }
}

async function archiveExistingProject(projectId: number) {
  projectManagerError.value = ''
  try {
    await archiveProject(projectId)
  } catch (err) {
    projectManagerError.value = readableError(err)
  }
}

async function deleteExistingProject(projectId: number) {
  if (!window.confirm('删除项目只允许在项目下没有专题时执行，确认删除？')) return
  projectManagerError.value = ''
  try {
    await removeProject(projectId)
  } catch (err) {
    projectManagerError.value = readableError(err)
  }
}

async function archiveExistingTopic(topicId: number) {
  projectManagerError.value = ''
  try {
    await archiveTopic(topicId)
  } catch (err) {
    projectManagerError.value = readableError(err)
  }
}

async function deleteExistingTopic(topicId: number) {
  if (!window.confirm('删除专题会移除该专题下的分析结果和独占文章，确认删除？')) return
  projectManagerError.value = ''
  try {
    await removeTopic(topicId)
  } catch (err) {
    projectManagerError.value = readableError(err)
  }
}

async function loadSourceRegistry() {
  sourceManagerLoading.value = true
  sourceManagerError.value = ''
  try {
    sources.value = await fetchSources()
  } catch (err) {
    sourceManagerError.value = readableError(err)
  } finally {
    sourceManagerLoading.value = false
  }
}

async function toggleSource(source: SourceRegistry) {
  sourceBusy.value = { ...sourceBusy.value, [source.id]: true }
  sourceManagerError.value = ''
  try {
    const updated = await updateSource(source.id, { enabled: !source.enabled })
    sources.value = sources.value.map((item) => (item.id === updated.id ? updated : item))
  } catch (err) {
    sourceManagerError.value = readableError(err)
  } finally {
    sourceBusy.value = { ...sourceBusy.value, [source.id]: false }
  }
}

async function saveSourceDraft() {
  if (!sourceDraft.value.name.trim() || !sourceDraft.value.url.trim() || creatingSource.value) return
  creatingSource.value = true
  sourceManagerError.value = ''
  try {
    const created = await createSource({
      name: sourceDraft.value.name.trim(),
      url: sourceDraft.value.url.trim(),
      country: sourceDraft.value.country.trim(),
      language: sourceDraft.value.language.trim(),
      source_type: sourceDraft.value.source_type,
      quality_tier: sourceDraft.value.quality_tier,
      notes: 'user-added source',
    })
    sources.value = [created, ...sources.value.filter((item) => item.id !== created.id)]
    sourceDraft.value = {
      name: '',
      url: '',
      country: '',
      language: 'en',
      source_type: 'rss',
      quality_tier: 'user',
    }
  } catch (err) {
    sourceManagerError.value = readableError(err)
  } finally {
    creatingSource.value = false
  }
}

async function importSourceDraft() {
  if (!sourceImportDraft.value.text.trim() || importingSources.value) return
  importingSources.value = true
  sourceManagerError.value = ''
  sourceImportMessage.value = ''
  try {
    const result = await importSources({
      text: sourceImportDraft.value.text,
      country: sourceImportDraft.value.country.trim(),
      language: sourceImportDraft.value.language.trim(),
      source_type: sourceImportDraft.value.source_type,
      quality_tier: sourceImportDraft.value.quality_tier,
      notes: 'bulk-imported source',
    })
    sources.value = [
      ...result.created,
      ...sources.value.filter((item) => !result.created.some((created) => created.id === item.id)),
    ]
    sourceImportMessage.value =
      `导入 ${result.created_count} 个，重复 ${result.duplicate_count} 个，无效 ${result.invalid_count} 个。`
    if (result.created_count > 0) {
      sourceImportDraft.value.text = ''
    }
  } catch (err) {
    sourceManagerError.value = readableError(err)
  } finally {
    importingSources.value = false
  }
}

async function loadAutoRefreshStatus() {
  autoRefreshLoading.value = true
  autoRefreshError.value = ''
  try {
    autoRefreshStatus.value = await fetchAutoRefreshStatus()
  } catch (err) {
    autoRefreshError.value = readableError(err)
  } finally {
    autoRefreshLoading.value = false
  }
}

const {
  query,
  selectedEventIndex,
  activeWorkspaceTab,
  expandedTimelineIndex,
  sourceTierFilter,
  sourceMatrixSort,
  articleCategoryFilter,
  hasLlmAnalysis,
  analysisModeLabel,
  majorEvents,
  selectedEvent,
  selectedEventKey,
  visibleCountryCompare,
  countryCards,
  firstReporterTimeline,
  hasCountryCompare,
  framing,
  displayAnalysisText,
  safeAnalysisHtml,
  stancePeriods,
  criteria,
  keywords,
  entities,
  entityGroups,
  sourceTierOptions,
  visibleSourceMatrix,
  articleCategoryGroups,
  visibleArticleGroups,
  articleCategoryOptions,
  filteredArticles,
  stanceGroups,
  toggleTimelineEvent,
  resetSelectedEvent,
  showAuthoritySources,
  showEarliestSources,
  showMostCoveredSources,
} = useEventWorkbench({
  detail,
  localData,
  articles,
  selectedTopicId,
  countryCompare,
  countryCompareEventKey,
  resetCountryCompare,
})

const {
  searching,
  deepAnalyzing,
  crossSynthesisAnalyzing,
  academicAnalyzing,
  sentimentAnalyzing,
  crossSynthesisLoading,
  academicLoading,
  sentimentLoading,
  eventSearch,
  searchMessage,
  searchSteps,
  searchWarnings,
  subtopics,
  analogues,
  activeJobId,
  activeDeepJobId,
  activeCrossSynthesisJobId,
  activeAcademicJobId,
  activeSentimentJobId,
  terminalJob,
  deepMessage,
  deepSteps,
  crossSynthesisMessage,
  crossSynthesisError,
  crossSynthesisSteps,
  academicMessage,
  academicError,
  academicSteps,
  academicLayer,
  sentimentLayer,
  openCliDiagnostics,
  sentimentMessage,
  sentimentError,
  sentimentSteps,
  collectDiagnostics,
  safeAcademicSummaryHtml,
  safeSentimentSummaryHtml,
  safeCrossSynthesisHtml,
  crossVoicesUsed,
  crossChainItems,
  hasCrossSynthesis,
  academicPapers,
  academicSchools,
  academicFoundationalPapers,
  academicCitationEdges,
  hasAcademicLayer,
  sentimentPosts,
  hasSentimentLayer,
  sentimentPostItems,
  sentimentCommentItems,
  sentimentCommentsByParent,
  sentimentPlatformGroups,
  sentimentPlatformLabels,
  loadAcademicLayer,
  loadSentimentLayer,
  loadCrossSynthesisLayer,
  resetCrossSynthesisState,
  resetAcademicState,
  resetSentimentState,
  runEventSearch,
  searchRelated,
  rerunTerminalJob,
  runDeepAnalysis,
  runAcademicAnalysis,
  runSentimentAnalysis,
  runCrossSynthesis,
  canRerunJob,
  stepStatusText,
  sentimentPlatformLabel,
  voiceLabel,
} = useJobRunner({
  selectedTopicId,
  selectedTopic,
  localData,
  selectedEventIndex,
  error,
  loadTopics,
  loadTopic,
  loadArticles,
  loadLocalEvents,
})

onMounted(async () => {
  await Promise.all([
    loadTopics(),
    loadAutoRefreshStatus(),
    loadLatestDiscovery(),
    loadSeedCognitionState(),
  ])
  // 邮件深链（省力早报 → 硬核台的桥）：?topic=&event=&view=contrast。
  // 无 router，纯读 URLSearchParams；topic 必需，event 可选，view 默认对照。
  parseDeepLink()
})

// 解析地址栏 deep-link 参数，命中则进入深挖（复用 digestDigTarget 的定位机）。
function parseDeepLink() {
  const params = new URLSearchParams(window.location.search)
  const rawTopic = params.get('topic')
  if (!rawTopic) return
  const topicId = Number(rawTopic)
  if (!Number.isInteger(topicId) || topicId <= 0) return
  const rawEvent = params.get('event')
  const eventId = rawEvent && /^\d+$/.test(rawEvent) ? Number(rawEvent) : null
  const view = params.get('view') || 'contrast'
  digestDigTarget(topicId, eventId, view)
}

watch(appMode, (mode) => {
  if (mode === 'discovery' && !discoveryLoaded.value) {
    loadLatestDiscovery()
  }
  if (mode === 'discovery') {
    loadSeedCognitionState()
  }
})

watch(showProjectManager, (visible) => {
  if (visible && !sources.value.length) {
    loadSourceRegistry()
  }
})

// 发现 -> 分析闭环: 点种子 -> LLM 提炼成话题词 -> 切到事件分析台 -> 自动搜索。
const seedBusy = ref(false)
const activeSeedUrl = ref('')
const seedNote = ref('')

async function analyzeSeed(seed: DiscoverySeed) {
  if (seedBusy.value) return
  seedBusy.value = true
  activeSeedUrl.value = seed.url
  seedNote.value = ''
  try {
    const { query, llm } = await distillSeedTopic(seed)
    const term = (query || seed.title).trim()
    eventSearch.value = term
    appMode.value = 'workbench'
    if (llm && query) {
      // LLM 提炼成功 -> 直接跑搜索
      await runEventSearch()
    } else {
      // 降级 (无 LLM / 提炼失败): 已带入话题词，但不自动搜，提示用户精简后手动点。
      searchMessage.value = `已从认知前沿带入「${term}」。未用 LLM 提炼，建议精简关键词后点击搜索。`
    }
  } catch (err) {
    // distill 调用本身失败 (网络等) -> 停在发现页给出提示，不切走。
    seedNote.value = readableError(err)
  } finally {
    seedBusy.value = false
    activeSeedUrl.value = ''
  }
}

async function refreshSelectedTopicCollection() {
  const term = selectedTopic.value?.queries?.[0] || selectedTopic.value?.name || ''
  if (!term.trim()) return
  eventSearch.value = term.trim()
  await runEventSearch()
}

async function triggerAutoRefreshNow() {
  if (autoRefreshRunning.value) return
  autoRefreshRunning.value = true
  autoRefreshError.value = ''
  try {
    autoRefreshStatus.value = await runAutoRefreshNow()
  } catch (err) {
    autoRefreshError.value = readableError(err)
  } finally {
    autoRefreshRunning.value = false
  }
}

// 情报台「正在追踪」: 点已建专题 -> 切到事件分析台并选中它 (watch(selectedTopicId) 自动加载档案)。
function trackTopic(topicId: number) {
  selectedTopicId.value = topicId
  appMode.value = 'workbench'
}

watch(selectedTopicId, async (id) => {
  if (id) {
    localData.value = null
    eventGraph.value = null
    resetCountryCompare()
    resetEventContrast()
    resetCrossSynthesisState()
    resetAcademicState()
    resetSentimentState()
    resetSelectedEvent()
    articlePerspectives.value = {}
    articlePerspectiveLoading.value = {}
    articlePerspectiveErrors.value = {}
    cognitionMarkError.value = ''
    await Promise.all([
      loadTopic(id),
      loadArticles(id),
      loadLocalEvents(id),
      loadEventGraph(id),
      loadCrossSynthesisLayer(id),
      loadAcademicLayer(id),
      loadSentimentLayer(id),
    ])
    // 事件图已到位：若有待消化目标（来自队列/头版深挖/邮件深链），此刻按 eventId 定位。
    if (pendingDigest.value) await resolvePendingDigest()
  }
})

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

// 对照台按 event_id 取数（GPT 契约）。选中 index → 后端事件图同序节点的稳定 Event.id。
// 后端图缺席（本地兜底）时无稳定 id → null，按钮据此禁用并诚实提示，不伪造 id。
const selectedEventId = computed<number | null>(() => {
  const nodes = eventGraph.value?.nodes
  if (!nodes || !nodes.length) return null
  const node = nodes[selectedEventIndex.value]
  return node ? node.id : null
})

async function loadContrastForSelectedEvent() {
  const topicId = selectedTopicId.value
  const eventId = selectedEventId.value
  // 请求发起时的事件身份，await 期间用户若切走，结果不得贴到新事件上（证据归属红线）。
  const requestedKey = selectedEventKey.value
  if (!topicId || eventId === null || eventContrastLoading.value) return
  eventContrastLoading.value = true
  eventContrastError.value = ''
  try {
    const payload = await fetchEventContrast(topicId, eventId)
    // 迟到的响应：已切到别的事件则丢弃，不污染当前事件的证据。
    if (selectedEventKey.value !== requestedKey) return
    eventContrast.value = payload
    eventContrastEventKey.value = requestedKey
  } catch (err) {
    eventContrastError.value = readableError(err)
  } finally {
    eventContrastLoading.value = false
  }
}

function resetEventContrast() {
  eventContrast.value = null
  eventContrastError.value = ''
  eventContrastEventKey.value = ''
}

// 只在对照数据属于当前选中事件时才显示，切换事件后旧对照不串台。
const visibleEventContrast = computed<EventContrastPayload | null>(() =>
  eventContrast.value && eventContrastEventKey.value === selectedEventKey.value
    ? eventContrast.value
    : null,
)

// ── 深挖队列消化 + deep-link(双模式桥梁 V1a）──
// 队列条目、头版深挖入口(A)、邮件深链共用同一台「按 eventId 定位并展开对照」解析机。
// 切 topic 会触发 watch(selectedTopicId) 异步加载事件图；图到位前先把目标记进 pendingDigest，
// 图加载完在 watch 尾解析，避免竞态。
const { digItems, digCount, addToDigQueue, removeFromDigQueue } = useDigQueue()

// topicId 必存：审计 #3——只凭 eventId 会被任意话题加载抢先消费。解析前校验目标话题==当前话题。
type PendingDigest = { topicId: number; eventId: number | null; view: string }
const pendingDigest = ref<PendingDigest | null>(null)
// 深链/队列消化落空时的诚实提示（审计 #8：不再静默丢意图）。
const digestNotice = ref('')

// 解析待消化目标：切到 workbench+media，按 eventId 找同序节点 → 选中+展开；view=contrast 则拉对照。
// eventId=null(话题级标记）只停在默认选中事件不定位。
async function resolvePendingDigest() {
  const target = pendingDigest.value
  if (!target) return
  // 审计 #3：目标话题 ≠ 当前话题（旧话题的 watch 抢跑）→ 不消费，留给正确话题的加载解析。
  if (selectedTopicId.value !== target.topicId) return
  // 到这里已确认在正确话题、事件图已加载完（watch 尾调用）→ 可以安全清空并解析。
  pendingDigest.value = null
  appMode.value = 'workbench'
  activeWorkspaceTab.value = 'media'
  if (target.eventId !== null) {
    const nodes = eventGraph.value?.nodes || []
    const index = nodes.findIndex((node) => node.id === target.eventId)
    if (index >= 0) {
      toggleTimelineEvent(index)
    } else {
      // 审计 #8：事件不在当前图里（本地兜底/已归档）→ 明确告知，不假装成功也不静默丢。
      digestNotice.value = '该深挖目标事件不在当前事件图中，已切到话题但未能定位到具体事件。'
    }
  }
  if (target.view === 'contrast' && selectedEventId.value !== null) {
    await loadContrastForSelectedEvent()
  }
}

// 进入深挖：同 topic 直接解析；跨 topic 先切（触发 watch 加载图），watch 尾会解析。
function digestDigTarget(topicId: number, eventId: number | null, view = 'contrast') {
  digestNotice.value = ''
  pendingDigest.value = { topicId, eventId, view }
  if (selectedTopicId.value === topicId) {
    void resolvePendingDigest()
  } else {
    selectedTopicId.value = topicId
    appMode.value = 'workbench'
  }
}

// 头版「回头深挖」标记 → 入队（话题级，手机低意图场景，缓冲到电脑消化）。
function markTopicForDig(topic: { id: number; name: string }) {
  addToDigQueue({
    id: digItemKey(topic.id, null),
    topicId: topic.id,
    topicName: topic.name,
    eventId: null,
    eventTitle: topic.name,
    view: 'contrast',
  })
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

function isLimitedSource(source: SourceRegistry) {
  return !source.enabled && Boolean(source.coverage || source.access || source.coverage_reason)
}

function sourceCoverageLabel(value?: string) {
  const labels: Record<string, string> = {
    fresh_rss: '新鲜 RSS',
    summary_only: '摘要源',
    zombie: '已失活',
    proxy_only: '代理限定',
    paywalled: '付费墙',
    api_license: '授权/API',
    anti_bot: '反爬限制',
    scrapling: '需抓取器',
  }
  return value ? labels[value] || value : ''
}

function sourceAccessLabel(value?: string) {
  const labels: Record<string, string> = {
    public: '公开访问',
    paywalled: '付费墙',
    api_license: '授权/API',
    anti_bot: '反爬限制',
    proxy_only: '代理限定',
  }
  return value ? labels[value] || value : ''
}

function titleFor(article: Article) {
  return article.title_zh || article.title || '未命名报道'
}

function snippetFor(article: Article) {
  return article.snippet_zh || article.snippet || article.stance_summary || '暂无摘要'
}

async function loadArticlePerspective(article: Article) {
  if (!selectedTopicId.value || articlePerspectiveLoading.value[article.id]) return
  articlePerspectiveLoading.value = { ...articlePerspectiveLoading.value, [article.id]: true }
  articlePerspectiveErrors.value = { ...articlePerspectiveErrors.value, [article.id]: '' }
  try {
    const result = await fetchArticlePerspective(selectedTopicId.value, article.id)
    articlePerspectives.value = { ...articlePerspectives.value, [article.id]: result }
  } catch (err) {
    articlePerspectiveErrors.value = { ...articlePerspectiveErrors.value, [article.id]: readableError(err) }
  } finally {
    articlePerspectiveLoading.value = { ...articlePerspectiveLoading.value, [article.id]: false }
  }
}

async function markSeedCognition(seed: DiscoverySeed, label: CognitionLabel, note = '') {
  try {
    const mark = await saveCognitionMark({
      target_type: 'seed',
      target_id: 0,
      target_key: seed.url,
      label,
      note,
      domain: seed.domain,
    })
    seedCognitionMarks.value = { ...seedCognitionMarks.value, [seed.url]: mark }
    cognitionMarkError.value = ''
    // 闭环: 标记后后端会按 domain 回写 profile confidence, refetch 让画像证据即时反映, 不整页重载。
    try {
      cognitionProfile.value = await fetchCognitionProfile()
    } catch {
      // 回写刷新失败不影响标记本身, 画像下次加载时会补上。
    }
  } catch (err) {
    cognitionMarkError.value = readableError(err)
  }
}

async function runLlmAnalysisBundle() {
  // 三级「深度分析」= 先并发跑三个一级声部(媒体/学界/民间), 全部落库后
  // 再跑二级「三方对照」——用 refreshVoices=false 走轻量路径, 只复用刚落库的声部,
  // 不重跑三声部(否则各跑两遍)。缺声部由后端 gather_voices 兜底照常合成。
  await Promise.allSettled([
    runDeepAnalysis(),
    runAcademicAnalysis(),
    runSentimentAnalysis(),
  ])
  await runCrossSynthesis(false)
}

async function loadSeedCognitionState() {
  try {
    const [marks, profile] = await Promise.all([
      fetchCognitionMarks(null, 'seed'),
      fetchCognitionProfile(),
    ])
    const bySeed: Record<string, CognitionMark> = {}
    for (const mark of marks) {
      if (mark.target_type === 'seed' && mark.target_key) bySeed[mark.target_key] = mark
    }
    seedCognitionMarks.value = { ...bySeed, ...seedCognitionMarks.value }
    cognitionProfile.value = profile
    cognitionMarkError.value = ''
  } catch (err) {
    cognitionMarkError.value = readableError(err)
  }
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
  if ('doi' in paper && paper.doi) return paper.doi
  if ('openalex_url' in paper && paper.openalex_url) return paper.openalex_url
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

function sentimentCommunityLabel(post: SentimentPost) {
  if (post.platform === 'reddit') return `r/${post.subreddit || 'unknown'}`
  return post.subreddit || sentimentPlatformLabel(post.platform)
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

</script>

<template>
  <main class="shell">
    <section class="topbar">
      <div>
        <p class="eyebrow">Dossier Intelligence</p>
        <h1>{{ appMode === 'discovery' ? '今日情报台' : '事件搜索与发展时间轴' }}</h1>
      </div>
      <div class="topbar-controls">
        <nav class="mode-switch" aria-label="顶层视图切换">
          <button
            v-for="mode in appModes"
            :key="mode.key"
            type="button"
            :class="{ active: appMode === mode.key }"
            @click="appMode = mode.key"
          >
            {{ mode.label }}
          </button>
        </nav>
        <button
          v-if="appMode === 'workbench'"
          type="button"
          class="ghost-button"
          @click="showProjectManager = !showProjectManager"
        >
          管理项目
        </button>
        <select v-if="appMode === 'workbench'" v-model="selectedTopicId" class="topic-select" aria-label="选择专题">
          <option :value="null" disabled>选择已有专题…</option>
          <option v-for="topic in topics" :key="topic.id" :value="topic.id">
            #{{ topic.id }} {{ topic.name }}
          </option>
        </select>
      </div>
    </section>

    <section v-if="appMode === 'workbench' && showProjectManager" class="project-manager">
      <div class="project-manager-head">
        <div>
          <p class="eyebrow">Projects</p>
          <h2>项目与专题</h2>
        </div>
        <div class="project-manager-actions">
          <button type="button" class="ghost-button" @click="openNewProject">
            新建项目
          </button>
          <button type="button" class="cross-primary-button" @click="openNewTopic(null)">
            新建专题
          </button>
        </div>
      </div>
      <p v-if="projectManagerError" class="search-message error">{{ projectManagerError }}</p>
      <div class="project-grid">
        <article v-for="project in projects" :key="project.id" class="project-row">
          <div class="project-row-head">
            <div>
              <strong>{{ project.name }}</strong>
              <span v-if="project.status === 'archived'" class="status-pill">已归档</span>
            </div>
            <p>{{ project.description || '暂无描述' }}</p>
            <span>{{ project.topic_count }} 个专题</span>
          </div>
          <ul>
            <li v-for="topic in project.topics" :key="topic.id">
              <div class="topic-row-main">
                <button type="button" @click="selectedTopicId = topic.id">
                  {{ topic.name }}
                </button>
                <span>
                  {{ topic.article_count }} 篇 · {{ topic.source_count }} 源
                  <template v-if="topic.status === 'archived'"> · 已归档</template>
                </span>
              </div>
              <div class="topic-row-actions">
                <button type="button" class="text-button" @click="editTopicDraft(topic)">
                  编辑专题
                </button>
                <button type="button" class="text-button" @click="archiveExistingTopic(topic.id)">
                  归档专题
                </button>
                <button type="button" class="text-button danger" @click="deleteExistingTopic(topic.id)">
                  删除专题
                </button>
              </div>
            </li>
          </ul>
          <div class="project-row-actions">
            <button type="button" class="ghost-button" @click="openNewTopic(project.id)">
              新建专题
            </button>
            <button type="button" class="ghost-button" @click="editProjectDraft(project)">
              编辑项目
            </button>
            <button type="button" class="ghost-button" @click="archiveExistingProject(project.id)">
              归档项目
            </button>
            <button type="button" class="ghost-button danger" @click="deleteExistingProject(project.id)">
              删除项目
            </button>
          </div>
        </article>
      </div>
      <form v-if="activeManagerForm === 'project'" class="project-editor" @submit.prevent="saveProjectDraft">
        <label>
          项目名称
          <input v-model="projectDraft.name" aria-label="项目名称" placeholder="俄乌战争研究" />
        </label>
        <label>
          项目描述
          <textarea v-model="projectDraft.description" aria-label="项目描述" placeholder="长期项目的范围与备注" />
        </label>
        <button type="submit" :disabled="savingProject || !projectDraft.name.trim()">
          {{ savingProject ? '保存中...' : '保存项目' }}
        </button>
      </form>
      <form v-else class="topic-editor" @submit.prevent="saveTopicDraft">
        <label>
          所属项目
          <select v-model.number="topicDraft.project_id" aria-label="所属项目">
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </option>
          </select>
        </label>
        <label>
          专题名称
          <input v-model="topicDraft.name" aria-label="专题名称" placeholder="前线态势" />
        </label>
        <label>
          检索词
          <textarea v-model="topicDraft.queries" aria-label="检索词" placeholder="俄乌战争 前线态势" />
        </label>
        <label>
          专题描述
          <textarea v-model="topicDraft.description" aria-label="专题描述" placeholder="保留父专题语境的追踪说明" />
        </label>
        <button type="submit" :disabled="creatingTopic || !topicDraft.name.trim()">
          {{ creatingTopic ? '保存中...' : topicDraft.id ? '保存专题' : '保存专题' }}
        </button>
      </form>
      <div class="source-manager">
        <div class="source-manager-head">
          <div>
            <p class="eyebrow">Sources</p>
            <h2>情报源</h2>
          </div>
          <button type="button" class="ghost-button" :disabled="sourceManagerLoading" @click="loadSourceRegistry">
            {{ sourceManagerLoading ? '刷新中...' : '刷新' }}
          </button>
        </div>
        <p v-if="sourceManagerError" class="search-message error">{{ sourceManagerError }}</p>
        <div v-if="sources.length" class="source-status-summary" aria-label="情报源状态摘要">
          <span>共 {{ sourceManagerStats.total }} 个源</span>
          <span>启用 {{ sourceManagerStats.enabled }} 个</span>
          <span v-if="sourceManagerStats.limited" class="warning">受限 {{ sourceManagerStats.limited }} 个</span>
          <span :class="{ warning: sourceManagerStats.failed > 0 }">失败 {{ sourceManagerStats.failed }} 个</span>
          <span>最近成功 {{ fmtDate(sourceManagerStats.latestSuccessAt, true) }}</span>
          <small v-for="note in sourceManagerStats.failedNotes" :key="note">{{ note }}</small>
        </div>
        <div v-if="sources.length" class="source-coverage-mix" aria-label="来源构成">
          <strong>来源构成</strong>
          <span>层级：{{ sourceCoverageMix.tiers || '暂无' }}</span>
          <span>类型：{{ sourceCoverageMix.types || '暂无' }}</span>
        </div>
        <div class="source-ingestion-guide" aria-label="情报源导入路径">
          <strong>情报源导入路径</strong>
          <span>RSS / Newsletter / Google Alerts：粘贴 feed URL 后进入采集与本地预分析。</span>
          <span>B站视频 / 网页线索：先作为待核实来源备注或对应平台样本处理，V1 不做视频转录。</span>
          <span>失败原因会显示在源状态表里；付费墙、登录态和反爬限制不静默吞掉。</span>
        </div>
        <form class="source-editor" @submit.prevent="saveSourceDraft">
          <label>
            源名
            <input v-model="sourceDraft.name" aria-label="源名" placeholder="Google Alert - Ukraine frontline" />
          </label>
          <label>
            Feed URL
            <input v-model="sourceDraft.url" aria-label="Feed URL" placeholder="https://example.com/feed.xml" />
          </label>
          <label>
            国家/地区
            <input v-model="sourceDraft.country" aria-label="国家/地区" placeholder="United States" />
          </label>
          <label>
            层级
            <select v-model="sourceDraft.quality_tier" aria-label="来源层级">
              <option value="user">user</option>
              <option value="newsletter">newsletter</option>
              <option value="mainstream">mainstream</option>
              <option value="professional">professional</option>
              <option value="wire">wire</option>
            </select>
          </label>
          <button type="submit" :disabled="creatingSource || !sourceDraft.name.trim() || !sourceDraft.url.trim()">
            {{ creatingSource ? '添加中...' : '添加源' }}
          </button>
        </form>
        <form class="source-importer" @submit.prevent="importSourceDraft">
          <label>
            批量导入情报源
            <textarea
              v-model="sourceImportDraft.text"
              aria-label="批量导入情报源"
              placeholder="Ukraine Alert https://example.com/feed.xml&#10;Morning Brew https://www.morningbrew.com/daily/rss"
            />
          </label>
          <label>
            批量导入层级
            <select v-model="sourceImportDraft.quality_tier" aria-label="批量导入层级">
              <option value="user">user</option>
              <option value="newsletter">newsletter</option>
              <option value="mainstream">mainstream</option>
              <option value="professional">professional</option>
              <option value="wire">wire</option>
            </select>
          </label>
          <label>
            国家/地区
            <input v-model="sourceImportDraft.country" aria-label="批量导入国家/地区" placeholder="United States" />
          </label>
          <button type="submit" :disabled="importingSources || !sourceImportDraft.text.trim()">
            {{ importingSources ? '导入中...' : '批量导入' }}
          </button>
        </form>
        <p v-if="sourceImportMessage" class="source-import-message">{{ sourceImportMessage }}</p>
        <div class="source-table">
          <article v-for="source in sources" :key="source.id" :class="{ disabled: !source.enabled }">
            <div>
              <strong>{{ source.name }}</strong>
              <small>{{ source.url }}</small>
            </div>
            <span>{{ source.source_type }}</span>
            <span>{{ source.quality_tier }}</span>
            <span>{{ source.country || '未知' }}</span>
            <span :class="`source-status status-${source.last_status}`">{{ source.last_status }}</span>
            <span>{{ source.article_count }} 篇</span>
            <button type="button" :disabled="sourceBusy[source.id]" @click="toggleSource(source)">
              {{ source.enabled ? '暂停' : '恢复' }}
            </button>
            <small v-if="source.last_error">{{ source.last_error }}</small>
            <div
              v-if="source.coverage || source.access || source.last_tested || source.coverage_reason || source.state_media"
              class="source-limit-details"
            >
              <span v-if="source.coverage">{{ sourceCoverageLabel(source.coverage) }}</span>
              <span v-if="source.access">{{ sourceAccessLabel(source.access) }}</span>
              <span v-if="source.last_tested">实测 {{ fmtDate(source.last_tested) }}</span>
              <span v-if="source.state_media">国家媒体/官方叙事样本</span>
              <small v-if="source.coverage_reason">{{ source.coverage_reason }}</small>
            </div>
          </article>
          <p v-if="!sourceManagerLoading && !sources.length" class="source-empty">暂无情报源。</p>
        </div>
      </div>
    </section>

    <DiscoveryPanel
      v-if="appMode === 'discovery'"
      :report="discoveryReport"
      :loading="discoveryLoading"
      :analyzing="discoveryAnalyzing"
      :loaded="discoveryLoaded"
      :error="discoveryError"
      :message="discoveryMessage"
      :active-job-id="discoveryJobId"
      :steps="discoverySteps"
      :discovery-reports="discoveryReports"
      :selected-discovery-run-id="selectedDiscoveryRunId"
      :discovery-timeline-tree="discoveryTimelineTree"
      :safe-report-html="discoverySafeHtml"
      :has-report="discoveryHasReport"
      :seeds="discoverySeeds"
      :seed-busy="seedBusy"
      :active-seed-url="activeSeedUrl"
      :seed-note="seedNote"
      :tracked-topics="topics"
      :seed-cognition-marks="seedCognitionMarks"
      :cognition-profile="cognitionProfile"
      :cognition-mark-error="cognitionMarkError"
      :step-status-text="discoveryStepStatusText"
      @run-discovery="runDiscovery"
      @select-discovery-report="loadDiscoveryReport"
      @analyze-seed="analyzeSeed"
      @track-topic="trackTopic"
      @mark-topic-for-dig="markTopicForDig"
      @mark-seed-cognition="markSeedCognition"
    />

    <template v-else>

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

      <div v-if="subtopics.length || analogues.length" class="related-threads">
        <div v-if="subtopics.length" class="thread-row">
          <span class="thread-label">↘ 继续下钻</span>
          <button
            v-for="topic in subtopics"
            :key="`sub-${topic}`"
            type="button"
            class="thread-chip thread-drill"
            :disabled="searching"
            @click="searchRelated(topic, 'subtopic')"
          >
            {{ topic }}
          </button>
        </div>
        <div v-if="analogues.length" class="thread-row">
          <span class="thread-label">🕰 历史相似</span>
          <button
            v-for="ana in analogues"
            :key="`ana-${ana}`"
            type="button"
            class="thread-chip thread-history"
            :disabled="searching"
            @click="searchRelated(ana, 'analogue')"
          >
            {{ ana }}
          </button>
        </div>
      </div>

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
            <button type="button" class="cross-primary-button" :disabled="crossSynthesisAnalyzing" @click="runCrossSynthesis()">
              {{ crossSynthesisAnalyzing ? '三方对照生成中...' : hasCrossSynthesis ? '刷新三方对照' : '三方对照' }}
            </button>
            <button type="button" class="ghost-button" :disabled="academicAnalyzing" @click="runAcademicAnalysis">
              {{ academicAnalyzing ? '学界分析中...' : '学界视角' }}
            </button>
            <button type="button" class="ghost-button" :disabled="sentimentAnalyzing" @click="runSentimentAnalysis">
              {{ sentimentAnalyzing ? '民间情绪分析中...' : '民间情绪' }}
            </button>
            <button type="button" :disabled="deepAnalyzing || academicAnalyzing || sentimentAnalyzing || crossSynthesisAnalyzing" @click="runLlmAnalysisBundle">
              {{ deepAnalyzing || academicAnalyzing || sentimentAnalyzing || crossSynthesisAnalyzing ? 'LLM 分析中...' : '深度分析（LLM · 媒体+学界+民间+三方对照）' }}
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
          <div v-if="subtopics.length || analogues.length" class="related-threads context-drilldown">
            <div v-if="subtopics.length" class="thread-row">
              <span class="thread-label">继续下钻</span>
              <button
                v-for="topic in subtopics"
                :key="`summary-sub-${topic}`"
                type="button"
                class="thread-chip thread-drill"
                :disabled="searching"
                @click="searchRelated(topic, 'subtopic')"
              >
                {{ topic }}
              </button>
            </div>
            <div v-if="analogues.length" class="thread-row">
              <span class="thread-label">历史相似</span>
              <button
                v-for="ana in analogues"
                :key="`summary-ana-${ana}`"
                type="button"
                class="thread-chip thread-history"
                :disabled="searching"
                @click="searchRelated(ana, 'analogue')"
              >
                {{ ana }}
              </button>
            </div>
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
        <div v-if="topicFreshnessWarning" class="freshness-warning">
          <span>{{ topicFreshnessWarning }}</span>
          <button type="button" class="ghost-button" :disabled="searching" @click="refreshSelectedTopicCollection">
            {{ searching ? '刷新中...' : '刷新采集' }}
          </button>
        </div>
        <div class="auto-refresh-status">
          <span v-if="autoRefreshSummary">{{ autoRefreshSummary }}</span>
          <span v-else-if="autoRefreshLoading">正在读取自动刷新状态...</span>
          <span v-else>自动刷新状态暂不可用。</span>
          <button
            type="button"
            class="ghost-button"
            :disabled="autoRefreshRunning || autoRefreshLoading"
            @click="triggerAutoRefreshNow"
          >
            {{ autoRefreshRunning ? '运行中...' : '立即运行' }}
          </button>
          <small v-if="autoRefreshError">{{ autoRefreshError }}</small>
          <small v-for="item in autoRefreshErrors" :key="item">{{ item }}</small>
        </div>
      </section>

      <!-- 深链/队列消化落空时的诚实提示（审计 #8：意图不静默丢） -->
      <p v-if="digestNotice" class="dig-queue-notice" role="status">{{ digestNotice }}</p>

      <!-- 深挖队列消化卡带（双模式桥梁 V1a）：手机标记的好奇心在电脑上排队等消化 -->
      <section v-if="digCount" class="dig-queue-band" aria-label="待深挖队列">
        <header class="dig-queue-head">
          <strong>待深挖 {{ digCount }} 件</strong>
          <span class="dig-queue-hint">手机标记的好奇心，在这里逐条消化</span>
        </header>
        <ul class="dig-queue-list">
          <li v-for="item in digItems" :key="item.id" class="dig-queue-item">
            <button
              type="button"
              class="dig-queue-open"
              @click="digestDigTarget(item.topicId, item.eventId, item.view)"
            >
              <span class="dig-queue-topic">{{ item.topicName }}</span>
              <span v-if="item.eventId !== null" class="dig-queue-event">{{ item.eventTitle }}</span>
            </button>
            <button
              type="button"
              class="dig-queue-remove"
              aria-label="移出队列"
              @click="removeFromDigQueue(item.id)"
            >
              ×
            </button>
          </li>
        </ul>
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
        <MediaPanel
          v-if="activeWorkspaceTab === 'media'"
          v-model:query="query"
          v-model:source-tier-filter="sourceTierFilter"
          v-model:source-matrix-sort="sourceMatrixSort"
          v-model:article-category-filter="articleCategoryFilter"
          :local-loading="localLoading"
          :major-events="majorEvents"
          :event-graph="eventGraph"
          :selected-event-index="selectedEventIndex"
          :expanded-timeline-index="expandedTimelineIndex"
          :has-llm-analysis="hasLlmAnalysis"
          :selected-event="selectedEvent"
          :country-compare-loading="countryCompareLoading"
          :country-compare-error="countryCompareError"
          :visible-source-matrix="visibleSourceMatrix"
          :source-tier-options="sourceTierOptions"
          :has-country-compare="hasCountryCompare"
          :visible-country-compare="visibleCountryCompare"
          :first-reporter-timeline="firstReporterTimeline"
          :country-cards="countryCards"
          :criteria="criteria"
          :framing="framing"
          :total-articles="totalArticles"
          :stance-groups="stanceGroups"
          :articles="articles"
          :article-category-groups="articleCategoryGroups"
          :article-category-options="articleCategoryOptions"
          :article-loading="articleLoading"
          :filtered-articles="filteredArticles"
          :visible-article-groups="visibleArticleGroups"
          :entities="entities"
          :keywords="keywords"
          :entity-groups="entityGroups"
          :stance-periods="stancePeriods"
          :narrative-signals="localData?.narrative_signals || []"
          :fmt-date="fmtDate"
          :importance-text="importanceText"
          :coverage-text="coverageText"
          :percent="percent"
          :evidence-snippet="evidenceSnippet"
          :country-flag="countryFlag"
          :top-stance-entries="topStanceEntries"
          :outlet-summary="outletSummary"
          :country-coverage-note="countryCoverageNote"
          :title-for="titleFor"
          :snippet-for="snippetFor"
          :article-perspectives="articlePerspectives"
          :article-perspective-loading="articlePerspectiveLoading"
          :article-perspective-errors="articlePerspectiveErrors"
          :subtopics="subtopics"
          :analogues="analogues"
          :searching="searching"
          :keyword-size="keywordSize"
          :toggle-timeline-event="toggleTimelineEvent"
          :search-related="searchRelated"
          :load-country-compare-for-selected-event="loadCountryCompareForSelectedEvent"
          :selected-event-id="selectedEventId"
          :event-contrast-loading="eventContrastLoading"
          :event-contrast-error="eventContrastError"
          :visible-event-contrast="visibleEventContrast"
          :load-event-contrast-for-selected-event="loadContrastForSelectedEvent"
          :show-authority-sources="showAuthoritySources"
          :show-earliest-sources="showEarliestSources"
          :show-most-covered-sources="showMostCoveredSources"
          :load-article-perspective="loadArticlePerspective"
        />
        <CrossPanel
          v-else-if="activeWorkspaceTab === 'cross'"
          :cross-synthesis-analyzing="crossSynthesisAnalyzing"
          :has-cross-synthesis="hasCrossSynthesis"
          :active-cross-synthesis-job-id="activeCrossSynthesisJobId"
          :cross-synthesis-message="crossSynthesisMessage"
          :cross-synthesis-steps="crossSynthesisSteps"
          :cross-chain-items="crossChainItems"
          :cross-synthesis-loading="crossSynthesisLoading"
          :cross-synthesis-error="crossSynthesisError"
          :cross-voices-used="crossVoicesUsed"
          :safe-cross-synthesis-html="safeCrossSynthesisHtml"
          :step-status-text="stepStatusText"
          :voice-label="voiceLabel"
          @run-cross-synthesis="runCrossSynthesis"
        />
        <AcademicPanel
          v-else-if="activeWorkspaceTab === 'academic'"
          :academic-analyzing="academicAnalyzing"
          :has-academic-layer="hasAcademicLayer"
          :active-academic-job-id="activeAcademicJobId"
          :academic-message="academicMessage"
          :academic-steps="academicSteps"
          :academic-loading="academicLoading"
          :academic-error="academicError"
          :academic-layer="academicLayer"
          :academic-papers="academicPapers"
          :academic-citation-edges="academicCitationEdges"
          :academic-schools="academicSchools"
          :academic-foundational-papers="academicFoundationalPapers"
          :safe-academic-summary-html="safeAcademicSummaryHtml"
          :step-status-text="stepStatusText"
          :academic-paper-url="academicPaperUrl"
          :is-foundational-paper="isFoundationalPaper"
          :foundational-stats="foundationalStats"
          :academic-venue="academicVenue"
          :academic-authors="academicAuthors"
          @run-academic-analysis="runAcademicAnalysis"
        />
        <SentimentPanel
          v-else-if="activeWorkspaceTab === 'sentiment'"
          :sentiment-analyzing="sentimentAnalyzing"
          :has-sentiment-layer="hasSentimentLayer"
          :active-sentiment-job-id="activeSentimentJobId"
          :sentiment-message="sentimentMessage"
          :sentiment-steps="sentimentSteps"
          :sentiment-loading="sentimentLoading"
          :sentiment-error="sentimentError"
          :sentiment-post-items="sentimentPostItems"
          :sentiment-comment-items="sentimentCommentItems"
          :sentiment-platform-labels="sentimentPlatformLabels"
          :sentiment-layer="sentimentLayer"
          :open-cli-diagnostics="openCliDiagnostics"
          :selected-topic="selectedTopic"
          :sentiment-posts="sentimentPosts"
          :safe-sentiment-summary-html="safeSentimentSummaryHtml"
          :sentiment-platform-groups="sentimentPlatformGroups"
          :step-status-text="stepStatusText"
          :sentiment-platform-label="sentimentPlatformLabel"
          :sentiment-community-label="sentimentCommunityLabel"
          :sentiment-post-date="sentimentPostDate"
          :sentiment-snippet="sentimentSnippet"
          :sentiment-comments-for-post="sentimentCommentsForPost"
          @run-sentiment-analysis="runSentimentAnalysis"
        />
        <LlmPanel
          v-else-if="activeWorkspaceTab === 'llm'"
          :has-llm-analysis="hasLlmAnalysis"
          :deep-analyzing="deepAnalyzing"
          :academic-analyzing="academicAnalyzing"
          :sentiment-analyzing="sentimentAnalyzing"
          :active-deep-job-id="activeDeepJobId"
          :deep-message="deepMessage"
          :deep-steps="deepSteps"
          :safe-analysis-html="safeAnalysisHtml"
          :display-analysis-text="displayAnalysisText"
          :step-status-text="stepStatusText"
          @run-deep-analysis="runLlmAnalysisBundle"
        />
      </section>
    </template>
    </template>
  </main>
</template>
