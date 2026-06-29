import type { Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import { renderMarkdown } from '../utils/markdown'
import type {
  Article,
  CountryCompare,
  EntityGroup,
  LocalEvent,
  LocalEventsPayload,
  TopicDetail,
} from '../types/dossier'

type UseEventWorkbenchOptions = {
  detail: Ref<TopicDetail | null>
  localData: Ref<LocalEventsPayload | null>
  articles: Ref<Article[]>
  selectedTopicId: Ref<number | null>
  countryCompare: Ref<CountryCompare | null>
  countryCompareEventKey: Ref<string>
  resetCountryCompare: () => void
}

const llmAnalysisMarker = '<!-- analysis-source: llm -->'
const authorityTierKeys = new Set(['wire', 'official', 'professional', 'mainstream'])

export function useEventWorkbench(options: UseEventWorkbenchOptions) {
  const {
    detail,
    localData,
    articles,
    selectedTopicId,
    countryCompare,
    countryCompareEventKey,
    resetCountryCompare,
  } = options

  const query = ref('')
  const selectedEventIndex = ref(0)
  const activeWorkspaceTab = ref<'media' | 'academic' | 'sentiment' | 'cross' | 'llm'>('media')
  const expandedTimelineIndex = ref<number | null>(null)
  const sourceTierFilter = ref('all')
  const sourceMatrixSort = ref('tier')
  const articleCategoryFilter = ref('all')

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
  const safeAnalysisHtml = computed(() => renderMarkdown(displayAnalysisText.value))
  const stancePeriods = computed(() => localData.value?.stance_evolution || [])
  const criteria = computed(() => localData.value?.criteria || [])
  const keywords = computed(() => localData.value?.keywords || [])
  const entities = computed(() => localData.value?.entities || [])
  const entityGroups = computed<EntityGroup[]>(() => localData.value?.entity_groups || [])
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
      .map(([category, items]) => ({
        category,
        // 组内按干货密度降序: 干货浮顶、水文沉底 (A=事前筛)。未评分按中性 50, 不全沉底。
        items: [...items].sort((a, b) => substanceKey(b) - substanceKey(a)),
      }))
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

  function toggleTimelineEvent(index: number) {
    selectedEventIndex.value = index
    expandedTimelineIndex.value = expandedTimelineIndex.value === index ? null : index
  }

  function resetSelectedEvent() {
    selectedEventIndex.value = 0
    expandedTimelineIndex.value = null
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

  return {
    query,
    selectedEventIndex,
    activeWorkspaceTab,
    expandedTimelineIndex,
    sourceTierFilter,
    sourceMatrixSort,
    articleCategoryFilter,
    storedAnalysisText,
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
    analysisText,
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
  }
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

// 干货排序键: 已评分用其分数, 未评分(-1/缺失)按中性 50, 避免未富化的文章全沉底。
function substanceKey(article: Article) {
  const score = article.substance_score
  return score === undefined || score < 0 ? 50 : score
}
