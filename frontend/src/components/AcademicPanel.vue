<script setup lang="ts">
import { computed } from 'vue'
import type { AcademicFoundationalPaper, AcademicLayer, AcademicPaper } from '../types/dossier'

type StepState = { key: string; label: string; status: string }
type AcademicSchool = {
  name: string
  paper_count: number
  years: number[]
  top_papers: { openalex_id: string; title: string; year: number | null }[]
  concepts: string[]
}
type AcademicCitationEdge = { citing_openalex_id: string; cited_openalex_id: string }

const props = defineProps<{
  academicAnalyzing: boolean
  hasAcademicLayer: boolean
  activeAcademicJobId: string
  academicMessage: string
  academicSteps: StepState[]
  academicLoading: boolean
  academicError: string
  academicLayer: AcademicLayer | null
  academicPapers: AcademicPaper[]
  academicCitationEdges: AcademicCitationEdge[]
  academicSchools: AcademicSchool[]
  academicFoundationalPapers: AcademicFoundationalPaper[]
  safeAcademicSummaryHtml: string
  stepStatusText: (status: string) => string
  academicPaperUrl: (paper: AcademicPaper | AcademicFoundationalPaper) => string
  isFoundationalPaper: (paper: AcademicPaper) => boolean
  foundationalStats: (paper: AcademicPaper) => AcademicFoundationalPaper | undefined
  academicVenue: (paper: AcademicPaper) => string
  academicAuthors: (paper: AcademicPaper) => string
}>()

defineEmits<{
  runAcademicAnalysis: []
}>()

type AcademicSignal = '高引用' | '新近' | '样本内奠基' | 'venue明确' | '低信息'

const currentYear = new Date().getFullYear()

const highCitationCutoff = computed(() => {
  const positiveCitations = props.academicPapers
    .map((paper) => paper.cited_by_count || 0)
    .filter((count) => count > 0)
    .sort((a, b) => b - a)
  if (!positiveCitations.length) return Number.POSITIVE_INFINITY
  const index = Math.max(0, Math.ceil(positiveCitations.length * 0.25) - 1)
  return positiveCitations[index]
})

function hasClearVenue(paper: AcademicPaper) {
  const venue = props.academicVenue(paper).trim().toLowerCase()
  return Boolean(venue) && venue !== 'unknown venue'
}

function isRecentPaper(paper: AcademicPaper) {
  return Boolean(paper.year && paper.year >= currentYear - 3)
}

function isLowInformationPaper(paper: AcademicPaper) {
  const abstract = (paper.abstract || '').trim()
  return !hasClearVenue(paper) && abstract.length < 80
}

function academicSignals(paper: AcademicPaper): AcademicSignal[] {
  const signals: AcademicSignal[] = []
  if (props.isFoundationalPaper(paper)) signals.push('样本内奠基')
  if ((paper.cited_by_count || 0) > 0 && (paper.cited_by_count || 0) >= highCitationCutoff.value) signals.push('高引用')
  if (isRecentPaper(paper)) signals.push('新近')
  if (hasClearVenue(paper)) signals.push('venue明确')
  if (isLowInformationPaper(paper)) signals.push('低信息')
  return signals
}

const academicSignalSummary = computed(() => {
  const counts = { high: 0, recent: 0, foundational: 0, lowInfo: 0 }
  for (const paper of props.academicPapers) {
    const signals = academicSignals(paper)
    if (signals.includes('高引用')) counts.high += 1
    if (signals.includes('新近')) counts.recent += 1
    if (signals.includes('样本内奠基')) counts.foundational += 1
    if (signals.includes('低信息')) counts.lowInfo += 1
  }
  return counts
})

const literatureNetwork = computed(() => props.academicLayer?.literature_network || { nodes: [], edges: [] })
const literatureNetworkNodes = computed(() => literatureNetwork.value.nodes || [])
const literatureNetworkEdges = computed(() => literatureNetwork.value.edges || [])
const academicSourceSummary = computed(() => {
  const labels = new Map<string, string>()
  for (const paper of props.academicPapers) {
    for (const source of paper.sources || []) {
      labels.set(source.toLowerCase(), academicSourceLabel(source))
    }
    for (const link of paper.source_links || []) {
      labels.set(link.source.toLowerCase(), academicSourceLabel(link.source))
    }
    if (paper.openalex_id || paper.openalex_url) labels.set('openalex', 'OpenAlex')
  }
  return [...labels.values()]
})

function paperDoiUrl(paper: AcademicPaper) {
  return paper.doi || ''
}

function paperOpenAlexUrl(paper: AcademicPaper) {
  return paper.openalex_url || paper.openalex_id
}

function academicSourceLabel(source: string) {
  const normalized = source.trim().toLowerCase()
  const labels: Record<string, string> = {
    openalex: 'OpenAlex',
    crossref: 'Crossref',
    semantic_scholar: 'Semantic Scholar',
    semanticscholar: 'Semantic Scholar',
    arxiv: 'arXiv',
  }
  return labels[normalized] || source
}

function paperSourceLabels(paper: AcademicPaper) {
  const labels = new Map<string, string>()
  for (const source of paper.sources || []) {
    labels.set(source.toLowerCase(), academicSourceLabel(source))
  }
  for (const link of paper.source_links || []) {
    labels.set(link.source.toLowerCase(), academicSourceLabel(link.source))
  }
  if (!labels.size && (paper.openalex_id || paper.openalex_url)) labels.set('openalex', 'OpenAlex')
  return [...labels.values()]
}

function paperSourceCount(paper: AcademicPaper) {
  return paper.source_count || paperSourceLabels(paper).length
}

function paperSourceLinks(paper: AcademicPaper) {
  const links = [...(paper.source_links || [])]
  if (paperOpenAlexUrl(paper) && !links.some((link) => link.source.toLowerCase() === 'openalex')) {
    links.unshift({ source: 'openalex', url: paperOpenAlexUrl(paper) })
  }
  return links.filter((link) => link.url)
}
</script>

<template>
  <section class="feed-pane tab-pane-wide">
    <section class="wide-panel academic-panel">
      <div class="pane-header compact">
        <div>
          <p class="eyebrow">Academic Layer</p>
          <h2>学界视角</h2>
        </div>
        <button type="button" class="ghost-button" :disabled="academicAnalyzing" @click="$emit('runAcademicAnalysis')">
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
        <div class="academic-source-scope" aria-label="学界样本范围">
          <strong>当前学界样本：{{ academicSourceSummary.length ? academicSourceSummary.join(' + ') : 'OpenAlex' }}</strong>
          <span>综述引用必须保留作者、年份、期刊/会议、DOI 或来源链接。</span>
          <span>文献网络只显示样本内部引用，不代表完整学术谱系。</span>
        </div>

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

        <div v-if="academicPapers.length" class="academic-signal-summary" aria-label="优先阅读信号">
          <strong>优先阅读信号</strong>
          <span><b>{{ academicSignalSummary.high }}</b> 高引用</span>
          <span><b>{{ academicSignalSummary.recent }}</b> 新近</span>
          <span><b>{{ academicSignalSummary.foundational }}</b> 样本内奠基</span>
          <span><b>{{ academicSignalSummary.lowInfo }}</b> 低信息</span>
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

        <div class="academic-section academic-literature-network">
          <div class="evidence-header">
            <strong>文献网络</strong>
            <span>{{ academicCitationEdges.length }} 条样本内部引用</span>
          </div>
          <p v-if="!literatureNetworkEdges.length" class="source-matrix-empty">暂无内部引用关系。</p>
          <div v-else class="academic-network">
            <div v-if="literatureNetworkNodes.length" class="academic-network-nodes">
              <article v-for="node in literatureNetworkNodes.slice(0, 8)" :key="node.id" class="academic-network-node">
                <b>{{ node.citation_key }}</b>
                <strong>{{ node.title }}</strong>
                <span>{{ node.year || '未知年份' }} · {{ node.venue || 'Unknown venue' }} · 被引 {{ node.cited_by_count }}</span>
              </article>
            </div>
            <div class="academic-network-edges">
              <article
                v-for="edge in literatureNetworkEdges.slice(0, 12)"
                :key="`${edge.citing_openalex_id}-${edge.cited_openalex_id}`"
                class="academic-network-edge"
              >
                <strong>{{ edge.citing_title || edge.citing_openalex_id.split('/').pop() }}</strong>
                <span>引用</span>
                <strong>{{ edge.cited_title || edge.cited_openalex_id.split('/').pop() }}</strong>
              </article>
            </div>
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
                <b>来源 {{ paperSourceCount(paper) || 1 }}</b>
                <span>{{ paperSourceLabels(paper).join(' + ') || 'OpenAlex' }}</span>
                <span>{{ academicVenue(paper) }}</span>
                <span v-for="signal in academicSignals(paper)" :key="signal" class="academic-signal-badge">
                  {{ signal }}
                </span>
              </div>
              <h3>
                <a :href="academicPaperUrl(paper)" target="_blank" rel="noreferrer">{{ paper.title }}</a>
              </h3>
              <p>{{ paper.citation || `${academicAuthors(paper)} · ${academicVenue(paper)}` }}</p>
              <div class="academic-paper-links">
                <a v-if="paperDoiUrl(paper)" :href="paperDoiUrl(paper)" target="_blank" rel="noreferrer">DOI</a>
                <a
                  v-for="link in paperSourceLinks(paper)"
                  :key="`${paper.openalex_id}-${link.source}-${link.url}`"
                  :href="link.url"
                  target="_blank"
                  rel="noreferrer"
                >
                  {{ academicSourceLabel(link.source) }}
                </a>
              </div>
            </article>
          </div>
        </div>
      </template>
    </section>
  </section>
</template>
