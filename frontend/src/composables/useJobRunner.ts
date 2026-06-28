import type { Ref } from 'vue'
import { computed, ref } from 'vue'
import {
  createAcademicJob,
  createCrossSynthesisJob,
  createDeepAnalysisJob,
  createSearchJob,
  createSentimentJob,
  fetchAcademic,
  fetchCrossSynthesis,
  fetchSentiment,
  rerunSearchJob,
} from '../api/dossierApi'
import { renderMarkdown } from '../utils/markdown'
import { stepStatusText, waitForJob, type StepState } from './jobPolling'
import type {
  AcademicLayer,
  CrossSynthesis,
  DeepAnalysisResult,
  LocalEventsPayload,
  SearchJob,
  SearchResponse,
  SentimentLayer,
  SentimentPost,
} from '../types/dossier'
import { readableError } from './useTopicData'

type UseJobRunnerOptions = {
  selectedTopicId: Ref<number | null>
  localData: Ref<LocalEventsPayload | null>
  selectedEventIndex: Ref<number>
  error: Ref<string>
  loadTopics: (preferTopicId?: number) => Promise<void>
  loadTopic: (id: number) => Promise<void>
  loadArticles: (id: number) => Promise<void>
  loadLocalEvents: (id: number) => Promise<void>
}

const deepEnrichLimit = 30
const academicTopN = 30
const sentimentLimit = 25

export function useJobRunner(options: UseJobRunnerOptions) {
  const {
    selectedTopicId,
    localData,
    selectedEventIndex,
    error,
    loadTopics,
    loadTopic,
    loadArticles,
    loadLocalEvents,
  } = options

  const searching = ref(false)
  const deepAnalyzing = ref(false)
  const crossSynthesisAnalyzing = ref(false)
  const academicAnalyzing = ref(false)
  const sentimentAnalyzing = ref(false)
  const crossSynthesisLoading = ref(false)
  const academicLoading = ref(false)
  const sentimentLoading = ref(false)
  const eventSearch = ref('美伊战争')
  const searchMessage = ref('')
  const searchSteps = ref<StepState[]>([])
  const searchWarnings = ref<string[]>([])
  const subtopics = ref<string[]>([])   // 下钻: 当前主题的更细切面 (可点击开新搜索)
  const analogues = ref<string[]>([])   // 历史: 相似先例事件 (可点击开新搜索)
  const activeJobId = ref('')
  const activeDeepJobId = ref('')
  const activeCrossSynthesisJobId = ref('')
  const activeAcademicJobId = ref('')
  const activeSentimentJobId = ref('')
  const terminalJob = ref<SearchJob | null>(null)
  const deepJob = ref<SearchJob | null>(null)
  const deepMessage = ref('')
  const deepSteps = ref<StepState[]>([])
  const crossSynthesisLayer = ref<CrossSynthesis | null>(null)
  const crossSynthesisJob = ref<SearchJob | null>(null)
  const crossSynthesisMessage = ref('')
  const crossSynthesisError = ref('')
  const crossSynthesisSteps = ref<StepState[]>([])
  const academicLayer = ref<AcademicLayer | null>(null)
  const academicJob = ref<SearchJob | null>(null)
  const academicMessage = ref('')
  const academicError = ref('')
  const academicSteps = ref<StepState[]>([])
  const sentimentLayer = ref<SentimentLayer | null>(null)
  const sentimentJob = ref<SearchJob | null>(null)
  const sentimentMessage = ref('')
  const sentimentError = ref('')
  const sentimentSteps = ref<StepState[]>([])
  const collectDiagnostics = ref<SearchResponse['collect'] | null>(null)

  const safeAcademicSummaryHtml = computed(() => {
    const text = academicLayer.value?.summary_md?.trim()
    return renderMarkdown(text)
  })
  const safeSentimentSummaryHtml = computed(() => {
    const text = sentimentLayer.value?.summary_md?.trim()
    return renderMarkdown(text)
  })
  const safeCrossSynthesisHtml = computed(() => {
    const text = crossSynthesisLayer.value?.content_md?.trim()
    return renderMarkdown(text)
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

  async function runEventSearch() {
    const term = eventSearch.value.trim()
    if (!term) return
    searching.value = true
    error.value = ''
    searchMessage.value = ''
    searchWarnings.value = []
    subtopics.value = []
    analogues.value = []
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
    if (!isSearchResponse(job.result)) {
      throw new Error('搜索任务返回了未知结果')
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
    subtopics.value = result.subtopics || []
    analogues.value = result.analogues || []
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
    return waitForJob(jobId, searchSteps, searchMessage, 1200, '任务')
  }

  async function waitForDeepAnalysisJob(jobId: string) {
    return waitForJob(jobId, deepSteps, deepMessage, 1500, '深度分析')
  }

  async function waitForAcademicJob(jobId: string) {
    return waitForJob(jobId, academicSteps, academicMessage, 1800, '学界任务')
  }

  async function waitForSentimentJob(jobId: string) {
    return waitForJob(jobId, sentimentSteps, sentimentMessage, 1800, '民间情绪任务')
  }

  async function waitForCrossSynthesisJob(jobId: string) {
    return waitForJob(jobId, crossSynthesisSteps, crossSynthesisMessage, 1800, '三方对照任务')
  }

  // 点下钻/历史 chip: 把该线索填进搜索框并立刻跑一次新搜索 (各开各的档案)。
  async function searchRelated(term: string) {
    const next = (term || '').trim()
    if (!next || searching.value) return
    eventSearch.value = next
    await runEventSearch()
  }

  return {
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
    deepJob,
    deepMessage,
    deepSteps,
    crossSynthesisLayer,
    crossSynthesisJob,
    crossSynthesisMessage,
    crossSynthesisError,
    crossSynthesisSteps,
    academicLayer,
    academicJob,
    academicMessage,
    academicError,
    academicSteps,
    sentimentLayer,
    sentimentJob,
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
  }
}

function canRerunJob(job: SearchJob | null) {
  return job?.status === 'interrupted' || job?.status === 'failed'
}

function isSearchResponse(result: SearchJob['result']): result is SearchResponse {
  return Boolean(result && 'topic' in result && 'events' in result && 'collect' in result && 'steps' in result)
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

function sentimentPlatformLabel(platform: string) {
  const labels: Record<string, string> = {
    reddit: 'Reddit',
    hackernews: 'Hacker News',
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
    hackernews: 2,
    bilibili: 3,
    xiaohongshu: 4,
    xueqiu: 5,
  }
  return ranks[platform] || 99
}

function voiceLabel(voice: string) {
  const labels: Record<string, string> = {
    media: '媒体',
    academic: '学界',
    sentiment: '民间',
  }
  return labels[voice] || voice
}
