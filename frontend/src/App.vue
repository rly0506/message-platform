<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { fetchCountryCompare } from './api/dossierApi'
import { useEventWorkbench } from './composables/useEventWorkbench'
import { useJobRunner } from './composables/useJobRunner'
import { readableError, useTopicData } from './composables/useTopicData'
import type {
  AcademicFoundationalPaper,
  AcademicPaper,
  Article,
  CountryCompare,
  CountryCompareCountry,
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

watch(selectedTopicId, async (id) => {
  if (id) {
    localData.value = null
    resetCountryCompare()
    resetCrossSynthesisState()
    resetAcademicState()
    resetSentimentState()
    resetSelectedEvent()
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

          <details class="media-collapse criteria-panel">
            <summary>
              <strong>关键节点判定标准</strong>
              <span>{{ criteria.length || (hasLlmAnalysis ? 1 : 0) }} 项</span>
            </summary>
            <div class="collapse-body">
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
            </div>
          </details>
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

          <details v-if="activeWorkspaceTab === 'media'" class="media-collapse wide-panel framing-panel">
            <summary>
              <strong>各方态度</strong>
              <span>{{ framing.length }} 方</span>
            </summary>
            <div class="collapse-body">
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
            </div>
          </details>

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
          <details class="media-collapse article-feed-collapse">
            <summary>
              <strong>原始报道流</strong>
              <span>{{ totalArticles }} 篇</span>
            </summary>
            <div class="collapse-body">
              <div class="section-divider">
                <div>
                  <p class="eyebrow">News Feed</p>
                  <h2>原始报道流</h2>
                </div>
              </div>

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
            </div>
          </details>
          </template>
        </section>

        <aside v-if="activeWorkspaceTab === 'media'" class="insight-pane">
          <details class="media-collapse">
            <summary>
              <strong>关键人物/组织</strong>
              <span>{{ entities.length || keywords.length }} 个</span>
            </summary>
            <div class="collapse-body">
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
            </div>
          </details>

          <details class="media-collapse">
            <summary>
              <strong>态度随时间变化</strong>
              <span>{{ stancePeriods.length }} 期</span>
            </summary>
            <div class="collapse-body">
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
            </div>
          </details>
        </aside>
      </section>
    </template>
  </main>
</template>
