import type { Ref } from 'vue'
import { computed, nextTick, ref } from 'vue'
import {
  createAcademicJob,
  createCrossSynthesisJob,
  createDeepAnalysisJob,
  createSearchJob,
  createSentimentJob,
  fetchAcademic,
  fetchCrossSynthesis,
  fetchOpenCliDiagnostics,
  fetchSentiment,
  rerunSearchJob,
} from '../api/dossierApi'
import { renderMarkdown } from '../utils/markdown'
import { isJobSuperseded, stepStatusText, waitForJob, type StepState } from './jobPolling'
import type {
  AcademicLayer,
  CrossSynthesis,
  DeepAnalysisResult,
  LocalEventsPayload,
  OpenCliDiagnostics,
  SearchJob,
  SearchResponse,
  SentimentLayer,
  SentimentPost,
  TopicSummary,
} from '../types/dossier'
import { readableError } from './useTopicData'

type UseJobRunnerOptions = {
  selectedTopicId: Ref<number | null>
  selectedTopic: Ref<TopicSummary | null>
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
    selectedTopic,
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
  const openCliDiagnostics = ref<OpenCliDiagnostics | null>(null)
  const sentimentJob = ref<SearchJob | null>(null)
  const sentimentMessage = ref('')
  const sentimentError = ref('')
  const sentimentSteps = ref<StepState[]>([])
  const collectDiagnostics = ref<SearchResponse['collect'] | null>(null)

  // 话题级层加载的 request-token：切话题时旧请求的迟到响应必须丢弃（与 useTopicData 同构）。
  // job 归属改由下方单调 generation 统一裁决；GET 层加载仍用各自 request-token。
  let academicLayerRequestId = 0
  let sentimentLayerRequestId = 0
  let crossSynthesisLayerRequestId = 0

  // 单调 job generation：唯一的作业归属判据（取代脆弱的 topic-id 相等）。
  // 每次切题（cancelRunningJobs）递增一次；作业发起时捕获当代，全生命周期
  // create→poll→finish→catch→finally 每个写入点只在「仍是当代」时提交。
  // 这从根上解决两个缺陷：① A→B→A 时 topic-id 又相等、旧 A 被误放行（ABA）；
  // ② 守卫只覆盖 finish、poll/catch/finally 仍写共享态。切题即作废在途作业，
  // 让 B 能立刻发起同族任务（旧全局 busy flag 不再阻塞）。
  let jobGeneration = 0

  function currentGeneration() {
    return jobGeneration
  }

  // search 自导航专用 owner token：搜索完成态的提交判据。search 导航到结果专题会
  // 触发 watch→cancelRunningJobs，但那次导航若是搜索自己预期的落点则不 bump 本 token
  // （放行完成态写入）；任何手动切题（含 A→B→A 的中途、A→null）都 bump，作废旧提交。
  // 这取代脆弱的「导航后比 topic-id」判据——A→B→A 落回 A 时 id 又相等、旧提交会被误放行。
  function currentSearchOwnerToken() {
    return searchOwnerToken
  }

  // finishSearchJob 在 await loadTopics 前登记预期落点，让那一次 watch 导航豁免 bump。
  function markPendingSearchNav(topicId: number) {
    pendingSearchNavTopicId = topicId
  }

  // 搜索自导航专用 owner token：解决 finishSearchJob 导航后归属判据的两难——
  // generation 会被搜索自己的导航（loadTopics→watch→cancelRunningJobs）bump 掉，
  // 而退回 topic-id 相等又有 A→B→A 的 ABA 漏洞。做法：搜索发起时捕获此 token，
  // 只有「非本次搜索预期导航」的切题才 bump 它。搜索把预期落点记进 pendingSearchNavTopicId，
  // cancelRunningJobs 收到匹配的落点则不 bump（放行本次结果）；任何其它切题都 bump（作废）。
  let searchOwnerToken = 0
  let pendingSearchNavTopicId: number | null = null

  // 切题/重置时调用：作废所有在途作业并释放同族 busy flag 与 active-id。
  // 在途作业的 poll 会因 generation 变更抛 JobSupersededError 而静默短路；
  // 其 finally 里的 busy/active-id 清理也用 generation 守卫，不误清 B 的新作业。
  // navigatedTopicId：本次切题的落点（watch 传入，A→null 传 null）。
  // 若它等于搜索预期落点，则这是搜索自己的导航，不 bump searchOwnerToken（放行结果）；
  // 其它任何切题（含手动、A→null）都 bump，作废在途搜索的完成态提交。
  function cancelRunningJobs(navigatedTopicId: number | null = null) {
    jobGeneration += 1
    if (pendingSearchNavTopicId === null || navigatedTopicId !== pendingSearchNavTopicId) {
      searchOwnerToken += 1
    }
    pendingSearchNavTopicId = null  // 一次性消费：无论是否匹配都清，避免陈旧放行。
    searching.value = false
    deepAnalyzing.value = false
    academicAnalyzing.value = false
    sentimentAnalyzing.value = false
    crossSynthesisAnalyzing.value = false
    activeJobId.value = ''
    activeDeepJobId.value = ''
    activeAcademicJobId.value = ''
    activeSentimentJobId.value = ''
    activeCrossSynthesisJobId.value = ''
    // search/deep 的终态展示（含可重跑的 terminalJob）属于旧专题，切题后必须清，
    // 否则 A 的搜索结果/深度步骤/可重跑任务会残留并可运行在 B（UI 归属泄漏）。
    // 注意：finishSearchJob 在导航（loadTopics）之后才写这些，故此清理不会吞掉新搜索结果。
    terminalJob.value = null
    searchMessage.value = ''
    searchSteps.value = []
    searchWarnings.value = []
    subtopics.value = []
    analogues.value = []
    collectDiagnostics.value = null  // 空选题/切题：旧采集诊断不得残留（审计补项）。
    error.value = ''                 // 顶层错误同属旧专题，一并清（审计补项）。
    deepJob.value = null
    deepMessage.value = ''
    deepSteps.value = []
  }

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
    const requestId = ++academicLayerRequestId
    academicLoading.value = true
    academicError.value = ''
    try {
      const layer = await fetchAcademic(id)
      if (requestId !== academicLayerRequestId || selectedTopicId.value !== id) return
      academicLayer.value = layer
    } catch (err) {
      if (requestId !== academicLayerRequestId || selectedTopicId.value !== id) return
      academicError.value = readableError(err)
      academicLayer.value = null
    } finally {
      if (requestId === academicLayerRequestId) academicLoading.value = false
    }
  }

  async function loadSentimentLayer(id: number) {
    const requestId = ++sentimentLayerRequestId
    sentimentLoading.value = true
    sentimentError.value = ''
    try {
      const [layer, diagnostics] = await Promise.all([
        fetchSentiment(id),
        loadOpenCliDiagnostics(),
      ])
      if (requestId !== sentimentLayerRequestId || selectedTopicId.value !== id) return
      sentimentLayer.value = layer
      openCliDiagnostics.value = diagnostics
    } catch (err) {
      if (requestId !== sentimentLayerRequestId || selectedTopicId.value !== id) return
      sentimentError.value = readableError(err)
      sentimentLayer.value = null
    } finally {
      if (requestId === sentimentLayerRequestId) sentimentLoading.value = false
    }
  }

  async function loadOpenCliDiagnostics() {
    try {
      return await fetchOpenCliDiagnostics()
    } catch {
      return null
    }
  }

  async function loadCrossSynthesisLayer(id: number) {
    const requestId = ++crossSynthesisLayerRequestId
    crossSynthesisLoading.value = true
    crossSynthesisError.value = ''
    try {
      const layer = await fetchCrossSynthesis(id)
      if (requestId !== crossSynthesisLayerRequestId || selectedTopicId.value !== id) return
      crossSynthesisLayer.value = layer
    } catch (err) {
      if (requestId !== crossSynthesisLayerRequestId || selectedTopicId.value !== id) return
      crossSynthesisError.value = readableError(err)
      crossSynthesisLayer.value = null
    } finally {
      if (requestId === crossSynthesisLayerRequestId) crossSynthesisLoading.value = false
    }
  }

  function resetCrossSynthesisState() {
    crossSynthesisLayerRequestId += 1  // 作废在途请求，其迟到响应不再写入
    crossSynthesisLoading.value = false
    crossSynthesisLayer.value = null
    crossSynthesisJob.value = null
    crossSynthesisMessage.value = ''
    crossSynthesisError.value = ''
    crossSynthesisSteps.value = []
    activeCrossSynthesisJobId.value = ''
  }

  function resetAcademicState() {
    academicLayerRequestId += 1
    academicLoading.value = false
    academicLayer.value = null
    academicJob.value = null
    academicMessage.value = ''
    academicError.value = ''
    academicSteps.value = []
    activeAcademicJobId.value = ''
  }

  function resetSentimentState() {
    sentimentLayerRequestId += 1
    sentimentLoading.value = false
    sentimentLayer.value = null
    openCliDiagnostics.value = null
    sentimentJob.value = null
    sentimentMessage.value = ''
    sentimentError.value = ''
    sentimentSteps.value = []
    activeSentimentJobId.value = ''
  }

  async function runEventSearch() {
    const term = eventSearch.value.trim()
    if (!term || searching.value) return
    const generation = currentGeneration()
    const originTopicId = selectedTopicId.value
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
      if (generation !== currentGeneration()) return  // 创建返回时已切题：不写 active-id/steps。
      activeJobId.value = job.id
      searchSteps.value = job.steps || searchSteps.value
      searchMessage.value = `任务已提交：${job.id.slice(0, 8)}`
      const res = await waitForSearchJob(job.id, () => generation === currentGeneration())
      await finishSearchJob(res, originTopicId, generation)
    } catch (err) {
      // generation 守卫：作废（切题）或已非当代则静默短路，不写 B 的面板。
      if (isJobSuperseded(err) || generation !== currentGeneration()) return
      error.value = readableError(err)
      searchSteps.value = searchSteps.value.map((step) =>
        step.status === 'running' ? { ...step, status: 'failed' } : step,
      )
    } finally {
      // 只有仍是当代才清 busy/active-id；切题后 cancelRunningJobs 已清，勿覆盖 B。
      if (generation === currentGeneration()) {
        searching.value = false
        activeJobId.value = ''
      }
    }
  }

  async function rerunTerminalJob() {
    const job = terminalJob.value
    if (!job || !canRerunJob(job) || searching.value) return
    const generation = currentGeneration()
    const originTopicId = selectedTopicId.value
    searching.value = true
    error.value = ''
    searchMessage.value = `正在重新提交任务 ${job.id.slice(0, 8)}...`
    searchWarnings.value = []
    collectDiagnostics.value = null
    try {
      const newJob = await rerunSearchJob(job.id)
      if (generation !== currentGeneration()) return
      activeJobId.value = newJob.id
      terminalJob.value = null
      searchSteps.value = newJob.steps || []
      searchMessage.value = `已重新提交：${newJob.id.slice(0, 8)}`
      const res = await waitForSearchJob(newJob.id, () => generation === currentGeneration())
      await finishSearchJob(res, originTopicId, generation)
    } catch (err) {
      if (isJobSuperseded(err) || generation !== currentGeneration()) return
      error.value = readableError(err)
      searchSteps.value = searchSteps.value.map((step) =>
        step.status === 'running' ? { ...step, status: 'failed' } : step,
      )
    } finally {
      if (generation === currentGeneration()) {
        searching.value = false
        activeJobId.value = ''
      }
    }
  }

  async function runDeepAnalysis() {
    const topicId = selectedTopicId.value
    if (!topicId || deepAnalyzing.value) return
    const generation = currentGeneration()
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
      if (generation !== currentGeneration()) return
      activeDeepJobId.value = job.id
      deepSteps.value = job.steps || deepSteps.value
      deepMessage.value = `深度分析任务已提交：${job.id.slice(0, 8)}`
      const resultJob = await waitForDeepAnalysisJob(job.id, () => generation === currentGeneration())
      await finishDeepAnalysisJob(resultJob, generation)
    } catch (err) {
      if (isJobSuperseded(err) || generation !== currentGeneration()) return
      error.value = readableError(err)
      deepSteps.value = deepSteps.value.map((step) =>
        step.status === 'running' ? { ...step, status: 'failed' } : step,
      )
    } finally {
      if (generation === currentGeneration()) {
        deepAnalyzing.value = false
        activeDeepJobId.value = ''
      }
    }
  }

  async function runAcademicAnalysis() {
    const topicId = selectedTopicId.value
    if (!topicId || academicAnalyzing.value) return
    const generation = currentGeneration()
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
      if (generation !== currentGeneration()) return
      activeAcademicJobId.value = job.id
      academicSteps.value = job.steps || academicSteps.value
      academicMessage.value = `学界任务已提交：${job.id.slice(0, 8)}`
      const resultJob = await waitForAcademicJob(job.id, () => generation === currentGeneration())
      await finishAcademicJob(resultJob, generation)
    } catch (err) {
      // 切走后 A 的错误不得写进 B 的面板（generation 守卫，取代脆弱的 topic-id 相等）。
      if (isJobSuperseded(err) || generation !== currentGeneration()) return
      academicError.value = readableError(err)
      academicSteps.value = academicSteps.value.map((step) =>
        step.status === 'running' ? { ...step, status: 'failed' } : step,
      )
    } finally {
      if (generation === currentGeneration()) {
        academicAnalyzing.value = false
        activeAcademicJobId.value = ''
      }
    }
  }

  async function runSentimentAnalysis() {
    const topicId = selectedTopicId.value
    if (!topicId || sentimentAnalyzing.value) return
    const generation = currentGeneration()
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
      if (generation !== currentGeneration()) return
      activeSentimentJobId.value = job.id
      sentimentSteps.value = job.steps || sentimentSteps.value
      sentimentMessage.value = `民间情绪任务已提交：${job.id.slice(0, 8)}`
      const resultJob = await waitForSentimentJob(job.id, () => generation === currentGeneration())
      await finishSentimentJob(resultJob, generation)
    } catch (err) {
      if (isJobSuperseded(err) || generation !== currentGeneration()) return
      sentimentError.value = readableError(err)
      sentimentSteps.value = sentimentSteps.value.map((step) =>
        step.status === 'running' ? { ...step, status: 'failed' } : step,
      )
    } finally {
      if (generation === currentGeneration()) {
        sentimentAnalyzing.value = false
        activeSentimentJobId.value = ''
      }
    }
  }

  async function runCrossSynthesis(refreshVoices = false, generationOverride?: number) {
    const topicId = selectedTopicId.value
    if (!topicId || crossSynthesisAnalyzing.value) return
    // bundle 续体传入发起时的 generation：切题后 override 已非当代，直接短路，
    // 不在 B 上起 cross（关闭 runLlmAnalysisBundle 的续体泄漏）。
    const generation = generationOverride ?? currentGeneration()
    if (generation !== currentGeneration()) return
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
      const job = await createCrossSynthesisJob(topicId, refreshVoices)
      if (generation !== currentGeneration()) return
      activeCrossSynthesisJobId.value = job.id
      crossSynthesisSteps.value = job.steps || crossSynthesisSteps.value
      crossSynthesisMessage.value = `三方对照任务已提交：${job.id.slice(0, 8)}`
      const resultJob = await waitForCrossSynthesisJob(job.id, () => generation === currentGeneration())
      await finishCrossSynthesisJob(resultJob, generation)
    } catch (err) {
      if (isJobSuperseded(err) || generation !== currentGeneration()) return
      crossSynthesisError.value = readableError(err)
      crossSynthesisSteps.value = crossSynthesisSteps.value.map((step) =>
        step.status === 'running' ? { ...step, status: 'failed' } : step,
      )
    } finally {
      if (generation === currentGeneration()) {
        crossSynthesisAnalyzing.value = false
        activeCrossSynthesisJobId.value = ''
      }
    }
  }

  async function finishSearchJob(job: SearchJob, originTopicId: number | null, generation: number) {
    // 入口守卫：① generation（切题/reset 后彻底丢弃，取代脆弱的 topic-id 相等）；
    // ② originTopicId（搜索会导航，若等待期间手动切到别的专题则不劫持当前面板）。
    // 空状态搜索时 originTopicId 为 null 且期间保持 null，守卫放行、正常建题导航。
    if (generation !== currentGeneration()) return
    if (selectedTopicId.value !== originTopicId) return
    if (!job.result) {
      throw new Error(job.error || '搜索任务未返回结果')
    }
    if (!isSearchResponse(job.result)) {
      throw new Error('搜索任务返回了未知结果')
    }
    const result = job.result
    const topicId = result.topic.id
    const isNavigation = topicId !== selectedTopicId.value
    // 顺序修复（批 5）：先导航，再写完成态。
    // 若导航到新专题，loadTopics 改 selectedTopicId → 触发 watch(selectedTopicId) →
    // 同步跑 cancelRunningJobs（清 terminalJob/searchMessage/steps）+ 整包加载。
    // 之前「先写完成态再 loadTopics」会被这次 cancel 吞掉自己的结果（审计 finding #3）。
    //
    // 归属再校验（批 6，审计 finding #1）：用 search-owner token 取代脆弱的「导航后比 topic-id」。
    // 捕获发起时的 owner token；登记本次预期落点，使 loadTopics 触发的那一次 watch 导航
    // 豁免 bump（放行本结果）。但 A→B→A（同题搜索、await 期间手动切走再切回）会经历两次
    // 非预期切题、bump token 两次，落回 A 时 id 又相等、旧「比 topic-id」判据会误放行——
    // 改比 token 即可正确丢弃：token 已变。
    const ownerToken = currentSearchOwnerToken()
    markPendingSearchNav(topicId)
    await loadTopics(topicId)
    if (isNavigation) await nextTick()
    // owner token 变了 = 期间发生过非预期切题（含 A→B→A、A→null）：丢弃完成态。
    // 同时校验选中专题仍为 topicId（同题搜索 watch 不触发、token 不变，靠此兜底）。
    if (ownerToken !== currentSearchOwnerToken() || selectedTopicId.value !== topicId) return
    terminalJob.value = job
    selectedEventIndex.value = 0
    searchSteps.value = result.steps || []
    searchWarnings.value = result.collect.errors || []
    subtopics.value = result.subtopics || []
    analogues.value = result.analogues || []
    collectDiagnostics.value = result.collect
    searchMessage.value = `采集 ${result.collect.raw} 条，保留 ${result.collect.kept} 条，新增 ${result.collect.new_articles} 篇。`
    // 本地事件：导航时 watch 的 loadLocalEvents 已按新专题加载（单一所有者），不重复写；
    // 同专题搜索（watch 不触发）才用搜索结果内联的本地分析并显式补加载 topic/articles。
    if (!isNavigation) {
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
      await Promise.all([loadTopic(topicId), loadArticles(topicId)])
    }
  }

  async function finishDeepAnalysisJob(job: SearchJob, generation: number) {
    // generation 守卫：深度分析在当前专题上原地运行。等待期间切走则彻底丢弃——
    // 结果已持久化到后端，切回时由 watch(selectedTopicId) 重新加载，不劫持 B 面板。
    if (generation !== currentGeneration()) return
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
    // 深度分析原地刷新当前专题（topic_id 即当前选题），watch 不会触发，显式补加载。
    // await 后再校验 generation（审计 finding #2）：等待期间手动切到 B 会触发 watch →
    // cancelRunningJobs bump generation，此处短路，不再对 B 续发加载。useTopicData 的
    // token 已能丢弃迟到写入，此再校验进一步避免无谓请求并与 search 路径对称。
    await loadTopics(result.topic_id)
    if (generation !== currentGeneration()) return
    await Promise.all([loadTopic(result.topic_id), loadArticles(result.topic_id), loadLocalEvents(result.topic_id)])
  }

  async function finishAcademicJob(job: SearchJob, generation: number) {
    // 唯一所有者守卫（generation）：等待期间切走则彻底丢弃——不写 job/steps/message，不再加载。
    // 该资源已由目标专题的 watch(selectedTopicId) 独立加载，避免双路径与 UI 归属泄漏。
    if (generation !== currentGeneration()) return
    if (job.status !== 'done') {
      throw new Error(job.error || `学界任务${stepStatusText(job.status)}`)
    }
    if (job.result && !isAcademicLayer(job.result)) {
      throw new Error('学界任务返回了未知结果')
    }
    // 守卫通过后仅同步写入：直接应用任务结果，不二次 loadAcademicLayer（每资源最多一次有效加载）。
    // 先作废在途 layer GET：切题时 watch 触发的 loadAcademicLayer 可能仍在飞，其迟到响应
    // 会晚于本 job.result 落地并覆盖它；bump token 让那个响应被丢弃。
    academicLayerRequestId += 1
    academicLoading.value = false  // 在途 GET 的 finally 因 token 已变不会清，故此处显式清，避免 loading 卡死
    academicJob.value = job
    academicSteps.value = job.steps || []
    if (job.result) {
      academicLayer.value = job.result
    }
    const papers = academicLayer.value?.papers.length ?? 0
    const edges = academicLayer.value?.graph?.edges.length ?? 0
    academicMessage.value = `学界视角已更新：${papers} 篇论文，${edges} 条内部引用。`
  }

  async function finishSentimentJob(job: SearchJob, generation: number) {
    if (generation !== currentGeneration()) return
    if (job.status !== 'done' && job.status !== 'empty') {
      throw new Error(job.error || `民间情绪任务${stepStatusText(job.status)}`)
    }
    if (job.result && !isSentimentLayer(job.result)) {
      throw new Error('民间情绪任务返回了未知结果')
    }
    // 作废在途 sentiment layer GET，避免迟到响应覆盖本 job.result（同 academic）。
    sentimentLayerRequestId += 1
    sentimentLoading.value = false  // 同 academic：在途 GET 不会清 loading，此处显式清
    sentimentJob.value = job
    sentimentSteps.value = job.steps || []
    if (job.result) {
      sentimentLayer.value = job.result
    }
    const posts = sentimentLayer.value?.posts.length ?? 0
    sentimentMessage.value =
      posts > 0
        ? `民间情绪已更新：${posts} 条 Reddit 讨论。`
        : '民间情绪任务完成，但没有抓到可用帖子。'
  }

  async function finishCrossSynthesisJob(job: SearchJob, generation: number) {
    if (generation !== currentGeneration()) return
    if (job.status !== 'done') {
      throw new Error(job.error || `三方对照任务${stepStatusText(job.status)}`)
    }
    if (job.result && !isCrossSynthesis(job.result)) {
      throw new Error('三方对照任务返回了未知结果')
    }
    // 作废在途 cross layer GET，避免迟到响应覆盖本 job.result（同 academic）。
    crossSynthesisLayerRequestId += 1
    crossSynthesisLoading.value = false  // 同 academic：在途 GET 不会清 loading，此处显式清
    crossSynthesisJob.value = job
    crossSynthesisSteps.value = job.steps || []
    if (job.result) {
      crossSynthesisLayer.value = job.result
    }
    const voices = crossVoicesUsed.value.length
    crossSynthesisMessage.value =
      voices > 0
        ? `三方对照已更新：使用 ${voices} 个声部。`
        : '三方对照已更新，但当前没有可用声部数据。'
  }

  async function waitForSearchJob(jobId: string, isCurrent?: () => boolean) {
    return waitForJob(jobId, searchSteps, searchMessage, 1200, '任务', isCurrent)
  }

  async function waitForDeepAnalysisJob(jobId: string, isCurrent?: () => boolean) {
    return waitForJob(jobId, deepSteps, deepMessage, 1500, '深度分析', isCurrent)
  }

  async function waitForAcademicJob(jobId: string, isCurrent?: () => boolean) {
    return waitForJob(jobId, academicSteps, academicMessage, 1800, '学界任务', isCurrent)
  }

  async function waitForSentimentJob(jobId: string, isCurrent?: () => boolean) {
    return waitForJob(jobId, sentimentSteps, sentimentMessage, 1800, '民间情绪任务', isCurrent)
  }

  async function waitForCrossSynthesisJob(jobId: string, isCurrent?: () => boolean) {
    return waitForJob(jobId, crossSynthesisSteps, crossSynthesisMessage, 1800, '三方对照任务', isCurrent)
  }

  function contextualSubtopicQuery(term: string) {
    const subtopic = term.trim()
    const parent = selectedTopic.value?.name?.trim() || terminalJob.value?.query?.trim() || eventSearch.value.trim()
    if (!parent || subtopic.includes(parent) || parent.includes(subtopic)) return subtopic
    return `${parent} ${subtopic}`
  }

  // 点下钻/历史 chip: 把该线索填进搜索框并立刻跑一次新搜索 (各开各的档案)。
  async function searchRelated(term: string, kind: 'subtopic' | 'analogue' = 'subtopic') {
    const next = (term || '').trim()
    if (!next || searching.value) return
    eventSearch.value = kind === 'subtopic' ? contextualSubtopicQuery(next) : next
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
    openCliDiagnostics,
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
    cancelRunningJobs,
    currentGeneration,
    currentSearchOwnerToken,
    markPendingSearchNav,
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
