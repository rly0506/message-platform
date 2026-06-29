<script setup lang="ts">
import { computed } from 'vue'
import type {
  Article,
  ArticlePerspective,
  CognitionLabel,
  CognitionMark,
  CognitionSummary,
  CountryCompare,
  CountryCompareCountry,
  CountryFirstReporter,
  Criterion,
  EntityGroup,
  EvidenceArticle,
  Keyword,
  LocalEvent,
  NarrativeSignal,
  SourceFraming,
  SourceMatrixItem,
  StanceEvolution,
} from '../types/dossier'

type SelectOption = { key: string; label: string }
type ArticleGroup = { category: string; items: Article[] }
type StanceGroup = { name: string; count: number }

const props = defineProps<{
  query: string
  sourceTierFilter: string
  sourceMatrixSort: string
  articleCategoryFilter: string
  localLoading: boolean
  majorEvents: LocalEvent[]
  selectedEventIndex: number
  expandedTimelineIndex: number | null
  hasLlmAnalysis: boolean
  selectedEvent: LocalEvent | null
  countryCompareLoading: boolean
  countryCompareError: string
  visibleSourceMatrix: SourceMatrixItem[]
  sourceTierOptions: SelectOption[]
  hasCountryCompare: boolean
  visibleCountryCompare: CountryCompare | null
  firstReporterTimeline: CountryFirstReporter[]
  countryCards: CountryCompareCountry[]
  criteria: Criterion[]
  framing: SourceFraming[]
  totalArticles: number
  stanceGroups: StanceGroup[]
  articles: Article[]
  articleCategoryGroups: ArticleGroup[]
  articleCategoryOptions: SelectOption[]
  articleLoading: boolean
  filteredArticles: Article[]
  visibleArticleGroups: ArticleGroup[]
  entities: Keyword[]
  keywords: Keyword[]
  entityGroups: EntityGroup[]
  stancePeriods: StanceEvolution[]
  narrativeSignals: NarrativeSignal[]
  fmtDate: (value: string | null, withTime?: boolean) => string
  importanceText: (event: LocalEvent) => string
  coverageText: (event: LocalEvent) => string
  percent: (value: number) => string
  evidenceSnippet: (article: EvidenceArticle) => string
  countryFlag: (code: string) => string
  topStanceEntries: (country: CountryCompareCountry) => [string, number][]
  outletSummary: (country: CountryCompareCountry) => string
  countryCoverageNote: (country: CountryCompareCountry) => string
  titleFor: (article: Article) => string
  snippetFor: (article: Article) => string
  articlePerspectives: Record<number, ArticlePerspective>
  articlePerspectiveLoading: Record<number, boolean>
  articlePerspectiveErrors: Record<number, string>
  articleCognitionMarks: Record<number, CognitionMark>
  cognitionSummary: CognitionSummary | null
  cognitionMarkError: string
  keywordSize: (keyword: Keyword) => string
  toggleTimelineEvent: (index: number) => void
  loadCountryCompareForSelectedEvent: () => void
  showAuthoritySources: () => void
  showEarliestSources: () => void
  showMostCoveredSources: () => void
  loadArticlePerspective: (article: Article) => void
  markArticleCognition: (article: Article, label: CognitionLabel) => void
}>()

const cognitionLabels = [
  { key: 'known', label: '已知' },
  { key: 'unexpected', label: '意外' },
  { key: 'doubtful', label: '存疑' },
  { key: 'unfamiliar', label: '陌生' },
] as const

const substanceStats = computed(() => {
  const stats = { scored: 0, high: 0, mid: 0, low: 0, unscored: 0 }
  for (const article of props.articles) {
    const score = article.substance_score
    if (score === undefined || score < 0) {
      stats.unscored += 1
    } else {
      stats.scored += 1
      if (score >= 70) stats.high += 1
      else if (score <= 35) stats.low += 1
      else stats.mid += 1
    }
  }
  return stats
})

const emit = defineEmits<{
  'update:query': [value: string]
  'update:sourceTierFilter': [value: string]
  'update:sourceMatrixSort': [value: string]
  'update:articleCategoryFilter': [value: string]
}>()

function updateQuery(event: Event) {
  emit('update:query', (event.target as HTMLInputElement).value)
}

function updateSourceTierFilter(event: Event) {
  emit('update:sourceTierFilter', (event.target as HTMLSelectElement).value)
}

function updateSourceMatrixSort(event: Event) {
  emit('update:sourceMatrixSort', (event.target as HTMLSelectElement).value)
}

function updateArticleCategoryFilter(event: Event) {
  emit('update:articleCategoryFilter', (event.target as HTMLSelectElement).value)
}

// 干货密度配色: 高=绿(干货), 中=灰, 低=橙(水文警示)
function substanceClass(score: number) {
  if (score >= 70) return 'substance-high'
  if (score <= 35) return 'substance-low'
  return 'substance-mid'
}
</script>

<template>
  <section class="feed-pane">
    <div class="pane-header">
      <div>
        <p class="eyebrow">Event Timeline</p>
        <h2>事件发展轴</h2>
      </div>
      <input :value="query" class="search" placeholder="筛选报道标题、来源、摘要" @input="updateQuery" />
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
            <select :value="sourceTierFilter" aria-label="来源层级筛选" @change="updateSourceTierFilter">
              <option v-for="option in sourceTierOptions" :key="option.key" :value="option.key">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label>
            <span>排序</span>
            <select :value="sourceMatrixSort" aria-label="来源矩阵排序" @change="updateSourceMatrixSort">
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

    <details class="media-collapse wide-panel framing-panel">
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

    <details class="media-collapse article-feed-collapse">
      <summary>
        <strong>原始报道流</strong>
        <span>{{ totalArticles }} 篇 · 已评分 {{ substanceStats.scored }}/{{ articles.length }}</span>
      </summary>
      <div class="collapse-body">
        <div class="section-divider">
          <div>
            <p class="eyebrow">News Feed</p>
            <h2>原始报道流</h2>
          </div>
        </div>

        <div class="substance-summary" aria-label="干货密度分布">
          <span class="substance-high">高干货 {{ substanceStats.high }}</span>
          <span class="substance-mid">中等 {{ substanceStats.mid }}</span>
          <span class="substance-low">低干货 {{ substanceStats.low }}</span>
          <span>未评分 {{ substanceStats.unscored }}</span>
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
            <select :value="articleCategoryFilter" aria-label="报道功能分类筛选" @change="updateArticleCategoryFilter">
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
                <span
                  v-if="article.substance_score !== undefined && article.substance_score >= 0"
                  class="substance-badge"
                  :class="substanceClass(article.substance_score)"
                  :title="article.substance_note || '干货密度：可证伪事实 vs 空话情绪'"
                >
                  干货 {{ article.substance_score }}
                </span>
              </div>
              <h3>
                <a :href="article.url" target="_blank" rel="noreferrer">{{ titleFor(article) }}</a>
              </h3>
              <p>{{ snippetFor(article) }}</p>
              <button
                type="button"
                class="ghost-button article-perspective-trigger"
                :disabled="articlePerspectiveLoading[article.id]"
                @click="loadArticlePerspective(article)"
              >
                {{ articlePerspectiveLoading[article.id] ? '透视中...' : '透视' }}
              </button>
              <div class="cognition-mark-row" aria-label="认知标记">
                <button
                  v-for="mark in cognitionLabels"
                  :key="mark.key"
                  type="button"
                  :class="['cognition-chip', { active: articleCognitionMarks[article.id]?.label === mark.key }]"
                  @click="markArticleCognition(article, mark.key)"
                >
                  {{ mark.label }}
                </button>
              </div>
              <p v-if="articlePerspectiveErrors[article.id]" class="country-compare-error">
                {{ articlePerspectiveErrors[article.id] }}
              </p>
              <div v-if="articlePerspectives[article.id]" class="article-perspective">
                <strong>{{ articlePerspectives[article.id].mode === 'fulltext' ? '全文透视' : '摘要透视' }}</strong>
                <span v-if="articlePerspectives[article.id].source_error">
                  全文不可用，已降级
                </span>
                <article
                  v-for="item in articlePerspectives[article.id].items"
                  :key="`${item.kind}-${item.sentence}`"
                  :class="`perspective-${item.kind}`"
                >
                  <b>{{ item.kind === 'substance' ? '干货' : '情绪' }}</b>
                  <p>{{ item.sentence }}</p>
                  <small>{{ item.reason }}</small>
                </article>
                <p v-if="!articlePerspectives[article.id].items.length" class="muted">暂无可标出的句子。</p>
              </div>
            </div>
            <aside>
              <strong>{{ percent(article.relevance) }}</strong>
              <span>{{ article.stance || (article.enriched ? '未标注' : '本地待判定') }}</span>
            </aside>
          </article>
        </details>
      </div>
    </details>

    <details class="media-collapse cognition-overview">
      <summary>
        <strong>认知积累</strong>
        <span>{{ cognitionSummary?.recent.length || 0 }} 条最近标记</span>
      </summary>
      <div class="collapse-body">
        <p v-if="cognitionMarkError" class="country-compare-error">{{ cognitionMarkError }}</p>
        <div class="cognition-counts">
          <span v-for="mark in cognitionLabels" :key="mark.key">
            {{ mark.label }} {{ cognitionSummary?.counts?.[mark.key] || 0 }}
          </span>
        </div>
        <div v-if="cognitionSummary?.unfamiliar_topics.length" class="cognition-unfamiliar">
          <strong>陌生领域排行</strong>
          <span v-for="item in cognitionSummary.unfamiliar_topics" :key="item.topic_id">
            {{ item.topic }} {{ item.count }}
          </span>
        </div>
        <p v-else class="muted">先用一键标记积累你的判断，地图以后再画。</p>
      </div>
    </details>
  </section>

  <aside class="insight-pane">
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
                @click="emit('update:query', word.term)"
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

  <details class="media-collapse narrative-panel">
    <summary>
      <strong>叙事趋同信号</strong>
      <span>{{ narrativeSignals.length }} 条</span>
    </summary>
    <div class="collapse-body">
      <article v-for="signal in narrativeSignals" :key="signal.claim" class="narrative-signal">
        <div>
          <strong>{{ signal.claim }}</strong>
          <span>{{ signal.source_count }} 源 · {{ signal.article_count }} 篇</span>
        </div>
        <p>{{ signal.sources.join('、') }}</p>
        <ul>
          <li v-for="title in signal.representative_titles" :key="title">{{ title }}</li>
        </ul>
      </article>
      <p v-if="!narrativeSignals.length" class="muted">当前主题内还没有足够多源重复说法。</p>
    </div>
  </details>
</template>
