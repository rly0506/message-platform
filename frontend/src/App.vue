<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { fetchArticlePerspective, fetchCountryCompare } from './api/dossierApi'
import AcademicPanel from './components/AcademicPanel.vue'
import CrossPanel from './components/CrossPanel.vue'
import DiscoveryPanel from './components/DiscoveryPanel.vue'
import LlmPanel from './components/LlmPanel.vue'
import MediaPanel from './components/MediaPanel.vue'
import SentimentPanel from './components/SentimentPanel.vue'
import { useDiscovery } from './composables/useDiscovery'
import { useEventWorkbench } from './composables/useEventWorkbench'
import { useJobRunner } from './composables/useJobRunner'
import { readableError, useTopicData } from './composables/useTopicData'
import type {
  AcademicFoundationalPaper,
  AcademicPaper,
  Article,
  ArticlePerspective,
  CountryCompare,
  CountryCompareCountry,
  DiscoverySeed,
  EvidenceArticle,
  Keyword,
  LocalEvent,
  SearchResponse,
  SentimentPost,
} from './types/dossier'

const countryCompareLoading = ref(false)
const countryCompare = ref<CountryCompare | null>(null)
const countryCompareError = ref('')
const countryCompareEventKey = ref('')
const articlePerspectives = ref<Record<number, ArticlePerspective>>({})
const articlePerspectiveLoading = ref<Record<number, boolean>>({})
const articlePerspectiveErrors = ref<Record<number, string>>({})

type AppMode = 'workbench' | 'discovery'
const appMode = ref<AppMode>('workbench')
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
  safeReportHtml: discoverySafeHtml,
  hasReport: discoveryHasReport,
  seeds: discoverySeeds,
  loadLatest: loadLatestDiscovery,
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
  topics,
  selectedTopicId,
  detail,
  localData,
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
} = useTopicData()

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
  sentimentLayer,
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
  localData,
  selectedEventIndex,
  error,
  loadTopics,
  loadTopic,
  loadArticles,
  loadLocalEvents,
})

onMounted(async () => {
  await loadTopics()
})

watch(appMode, (mode) => {
  if (mode === 'discovery' && !discoveryLoaded.value) {
    loadLatestDiscovery()
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

// 情报台「正在追踪」: 点已建专题 -> 切到事件分析台并选中它 (watch(selectedTopicId) 自动加载档案)。
function trackTopic(topicId: number) {
  selectedTopicId.value = topicId
  appMode.value = 'workbench'
}

watch(selectedTopicId, async (id) => {
  if (id) {
    localData.value = null
    resetCountryCompare()
    resetCrossSynthesisState()
    resetAcademicState()
    resetSentimentState()
    resetSelectedEvent()
    articlePerspectives.value = {}
    articlePerspectiveLoading.value = {}
    articlePerspectiveErrors.value = {}
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
        <select v-if="appMode === 'workbench'" v-model="selectedTopicId" class="topic-select" aria-label="选择专题">
          <option v-for="topic in topics" :key="topic.id" :value="topic.id">
            #{{ topic.id }} {{ topic.name }}
          </option>
        </select>
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
      :safe-report-html="discoverySafeHtml"
      :has-report="discoveryHasReport"
      :seeds="discoverySeeds"
      :seed-busy="seedBusy"
      :active-seed-url="activeSeedUrl"
      :seed-note="seedNote"
      :tracked-topics="topics"
      :step-status-text="discoveryStepStatusText"
      @run-discovery="runDiscovery"
      @analyze-seed="analyzeSeed"
      @track-topic="trackTopic"
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
            @click="searchRelated(topic)"
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
            @click="searchRelated(ana)"
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
        <MediaPanel
          v-if="activeWorkspaceTab === 'media'"
          v-model:query="query"
          v-model:source-tier-filter="sourceTierFilter"
          v-model:source-matrix-sort="sourceMatrixSort"
          v-model:article-category-filter="articleCategoryFilter"
          :local-loading="localLoading"
          :major-events="majorEvents"
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
          :keyword-size="keywordSize"
          :toggle-timeline-event="toggleTimelineEvent"
          :load-country-compare-for-selected-event="loadCountryCompareForSelectedEvent"
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
          :active-deep-job-id="activeDeepJobId"
          :deep-message="deepMessage"
          :deep-steps="deepSteps"
          :safe-analysis-html="safeAnalysisHtml"
          :display-analysis-text="displayAnalysisText"
          :step-status-text="stepStatusText"
          @run-deep-analysis="runDeepAnalysis"
        />
      </section>
    </template>
    </template>
  </main>
</template>
