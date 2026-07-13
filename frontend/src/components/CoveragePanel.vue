<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Article, AnalysisMeta, CoverageBucket, CoverageSnapshot } from '../types/dossier'

const props = defineProps<{
  payload: CoverageSnapshot | null
  loading: boolean
  error: string
  analysisMeta: AnalysisMeta | null
  articles: Article[]
}>()

// 每个计数都要能点回证据（审计红线）。展开的桶用 key 记，点第二次收起。
const expandedKey = ref<string>('')

function toggle(key: string) {
  expandedKey.value = expandedKey.value === key ? '' : key
}

// id → 已加载文章。命中则给可点链接；未命中（不在当前页）诚实退化为「#id」纯文本，不伪造链接。
const articleById = computed(() => {
  const index = new Map<number, Article>()
  for (const article of props.articles) index.set(article.id, article)
  return index
})

function articleLabel(id: number): string {
  const article = articleById.value.get(id)
  if (!article) return `#${id}`
  return article.title_zh || article.title || `#${id}`
}

function articleUrl(id: number): string {
  return articleById.value.get(id)?.url || ''
}

const sample = computed(() => props.payload?.sample ?? null)
const registry = computed(() => props.payload?.source_registry ?? null)
const decoding = computed(() => props.payload?.url_decoding ?? null)

// 分层里对不上 SourceRegistry 的文章：诚实标「未分层」，不塞进某个层里冒充。
const unclassifiedCount = computed(() => registry.value?.unclassified_article_ids.length ?? 0)

// 解码率：eligible 为 0 → 后端给 null → 前端标「未知」，不显示 0%（没有 gnews 样本 ≠ 解码失败）。
const decodeRateLabel = computed(() => {
  const d = decoding.value
  if (!d || d.rate === null || d.rate === undefined) return '未知'
  return `${Math.round(d.rate * 100)}%`
})

// 顶部四个概览数：篇数 / 独立来源 / 语言数 / 国家数。语言/国家排除「unknown」桶后计真实种类数。
function realKinds(buckets: CoverageBucket[]): number {
  return buckets.filter((b) => b.key !== 'unknown').length
}

const languageKinds = computed(() => realKinds(props.payload?.language_distribution ?? []))
const countryKinds = computed(() => realKinds(props.payload?.country_distribution ?? []))

// analysis_meta 新鲜度：sample_* 为 null（旧行无快照）时诚实标「未知」，不猜。
const freshnessLabel = computed(() => {
  const meta = props.analysisMeta
  if (!meta) return ''
  if (meta.sample_changed === null || meta.sample_changed === undefined) {
    return '样本快照未知（此分析生成时未记录基线，无法判断是否已过时）'
  }
  if (!meta.sample_changed) return '分析样本与当前采集一致'
  if (meta.evidence_newer) return '已有更新证据：当前采集比分析所依据的样本更多/更新'
  return '样本已变化（数量或最新时间与分析基线不同）'
})

const freshnessTone = computed(() => {
  const meta = props.analysisMeta
  if (!meta || meta.sample_changed === null || meta.sample_changed === undefined) return 'unknown'
  if (!meta.sample_changed) return 'ok'
  return meta.evidence_newer ? 'newer' : 'changed'
})
</script>

<template>
  <section class="coverage-panel">
    <div class="pane-header compact">
      <div>
        <p class="eyebrow">Coverage</p>
        <h2>本次分析基于什么</h2>
      </div>
    </div>

    <p class="coverage-note">
      下面的每个数字都来自已持久化的采集样本，可点开看具体是哪几篇。
      「未采集到」= 本次我们没抓到，<strong>不代表来源没有报道</strong>——没抓到 ≠ 源没发。
    </p>

    <!-- 分析新鲜度：analysis_meta（后端 P1 契约） -->
    <div v-if="analysisMeta" class="freshness" :class="`tone-${freshnessTone}`">
      <span class="freshness-source">{{ analysisMeta.source === 'llm' ? 'LLM 分析' : '本地分析' }}</span>
      <span class="freshness-body">{{ freshnessLabel }}</span>
      <span v-if="analysisMeta.sample_article_count !== null" class="freshness-counts">
        分析样本 {{ analysisMeta.sample_article_count }} 篇 · 当前 {{ analysisMeta.current_article_count }} 篇
      </span>
    </div>

    <p v-if="error" class="coverage-error">{{ error }}</p>
    <p v-else-if="loading" class="muted">正在读取覆盖快照…</p>

    <template v-else-if="payload">
      <!-- 四个概览数，每个可点回证据 -->
      <div class="coverage-overview">
        <button type="button" class="coverage-stat" :class="{ open: expandedKey === 'sample' }" @click="toggle('sample')">
          <b>{{ sample?.article_count ?? 0 }}</b>
          <span>篇报道</span>
        </button>
        <div class="coverage-stat static">
          <b>{{ payload.independent_source_count }}</b>
          <span>个独立来源</span>
        </div>
        <div class="coverage-stat static">
          <b>{{ languageKinds }}</b>
          <span>种语言</span>
        </div>
        <div class="coverage-stat static">
          <b>{{ countryKinds }}</b>
          <span>个国家/地区</span>
        </div>
      </div>

      <!-- 样本篇目证据（点篇数展开） -->
      <ul v-if="expandedKey === 'sample' && sample" class="coverage-evidence">
        <li v-for="id in sample.article_ids" :key="id">
          <a v-if="articleUrl(id)" :href="articleUrl(id)" target="_blank" rel="noopener noreferrer">{{ articleLabel(id) }}</a>
          <span v-else class="muted">{{ articleLabel(id) }}（不在当前页）</span>
        </li>
        <li v-if="!sample.article_ids.length" class="muted">本次未采集到可归入此范围的报道。</li>
      </ul>

      <!-- 分布：采集器 / 语言 / 国家 / 来源类型 / 来源分层。每桶可点回证据。 -->
      <div class="coverage-dists">
        <div class="dist-block">
          <h3>采集渠道</h3>
          <button
            v-for="b in payload.collector_distribution"
            :key="`col-${b.key}`"
            type="button"
            class="dist-chip"
            :class="{ open: expandedKey === `col-${b.key}` }"
            @click="toggle(`col-${b.key}`)"
          >{{ b.key }} · {{ b.count }}</button>
          <ul v-if="expandedKey.startsWith('col-')" class="coverage-evidence inline">
            <li v-for="id in (payload.collector_distribution.find((x) => `col-${x.key}` === expandedKey)?.article_ids || [])" :key="id">
              <a v-if="articleUrl(id)" :href="articleUrl(id)" target="_blank" rel="noopener noreferrer">{{ articleLabel(id) }}</a>
              <span v-else class="muted">{{ articleLabel(id) }}（不在当前页）</span>
            </li>
          </ul>
        </div>

        <div class="dist-block">
          <h3>语言</h3>
          <button
            v-for="b in payload.language_distribution"
            :key="`lang-${b.key}`"
            type="button"
            class="dist-chip"
            :class="{ open: expandedKey === `lang-${b.key}`, unknown: b.key === 'unknown' }"
            @click="toggle(`lang-${b.key}`)"
          >{{ b.key === 'unknown' ? '未标注' : b.key }} · {{ b.count }}</button>
          <ul v-if="expandedKey.startsWith('lang-')" class="coverage-evidence inline">
            <li v-for="id in (payload.language_distribution.find((x) => `lang-${x.key}` === expandedKey)?.article_ids || [])" :key="id">
              <a v-if="articleUrl(id)" :href="articleUrl(id)" target="_blank" rel="noopener noreferrer">{{ articleLabel(id) }}</a>
              <span v-else class="muted">{{ articleLabel(id) }}（不在当前页）</span>
            </li>
          </ul>
        </div>

        <div class="dist-block">
          <h3>国家/地区</h3>
          <button
            v-for="b in payload.country_distribution"
            :key="`cty-${b.key}`"
            type="button"
            class="dist-chip"
            :class="{ open: expandedKey === `cty-${b.key}`, unknown: b.key === 'unknown' }"
            @click="toggle(`cty-${b.key}`)"
          >{{ b.key === 'unknown' ? '未标注' : b.key }} · {{ b.count }}</button>
          <ul v-if="expandedKey.startsWith('cty-')" class="coverage-evidence inline">
            <li v-for="id in (payload.country_distribution.find((x) => `cty-${x.key}` === expandedKey)?.article_ids || [])" :key="id">
              <a v-if="articleUrl(id)" :href="articleUrl(id)" target="_blank" rel="noopener noreferrer">{{ articleLabel(id) }}</a>
              <span v-else class="muted">{{ articleLabel(id) }}（不在当前页）</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- 来源分层 + 未分层诚实提示 -->
      <div v-if="registry" class="coverage-registry">
        <h3>来源分层</h3>
        <template v-if="registry.tier_distribution.length">
          <span v-for="b in registry.tier_distribution" :key="`tier-${b.key}`" class="tier-chip">{{ b.key }} · {{ b.count }}</span>
        </template>
        <span v-else class="muted">当前样本无可分层来源。</span>
        <p v-if="unclassifiedCount" class="registry-unclassified">
          另有 {{ unclassifiedCount }} 篇来源未登记在源库、暂无法分层（诚实标注，不归入任一层）。
        </p>
      </div>

      <!-- 解码率 + 正文状态（诚实 unknown） -->
      <div class="coverage-meta-row">
        <div class="coverage-meta-item">
          <span class="meta-label">GNews 链接解码率</span>
          <span class="meta-value">
            {{ decodeRateLabel }}
            <em v-if="decoding && decoding.eligible_count">（{{ decoding.decoded_count }}/{{ decoding.eligible_count }} 篇）</em>
            <em v-else>（本次无 GNews 样本）</em>
          </span>
        </div>
        <div class="coverage-meta-item">
          <span class="meta-label">正文全文指标</span>
          <span class="meta-value unknown">未知（正文未落库，V1 无法统计，不估算填充）</span>
        </div>
      </div>
    </template>

    <p v-else class="muted">覆盖快照暂不可用（该接口可能尚未上线）。</p>
  </section>
</template>

<style scoped>
.coverage-panel {
  display: grid;
  gap: var(--space-3);
}

.coverage-note {
  margin: 0;
  color: var(--text-faint);
  font-size: var(--font-size-0);
  line-height: 1.6;
}

.coverage-note strong {
  color: var(--text-muted);
}

.freshness {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-2);
  border: 1px solid var(--border-soft);
  background: var(--surface-tint);
  font-size: var(--font-size-0);
}

.freshness.tone-newer {
  border-color: var(--lens-rising-border);
  background: var(--lens-rising-bg);
}

.freshness.tone-changed {
  border-color: var(--lens-hype-border);
  background: var(--lens-hype-bg);
}

.freshness-source {
  font-weight: 800;
  color: var(--text-strong);
}

.freshness-body {
  color: var(--text-muted);
}

.freshness-counts {
  margin-left: auto;
  color: var(--text-faint);
  font-weight: 700;
}

.coverage-error {
  color: var(--lens-hype-fg);
  font-size: var(--font-size-0);
}

.coverage-overview {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.coverage-stat {
  display: grid;
  gap: 2px;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-2);
  border: 1px solid var(--border-soft);
  background: var(--surface);
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
}

.coverage-stat.static {
  cursor: default;
}

.coverage-stat.open {
  border-color: var(--border-strong);
  background: var(--surface-tint);
}

.coverage-stat b {
  color: var(--text-heading);
  font-size: var(--font-size-3);
  font-weight: 800;
}

.coverage-stat span {
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.coverage-evidence {
  margin: 0;
  padding-left: var(--space-4);
  display: grid;
  gap: 2px;
}

.coverage-evidence.inline {
  padding-left: var(--space-3);
  margin-top: var(--space-1);
}

.coverage-evidence li {
  font-size: var(--font-size-0);
  line-height: 1.5;
}

.coverage-evidence a {
  color: var(--link);
}

.coverage-dists {
  display: grid;
  gap: var(--space-3);
}

.dist-block h3,
.coverage-registry h3 {
  margin: 0 0 var(--space-1);
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.dist-chip {
  display: inline-flex;
  align-items: center;
  margin: 0 var(--space-1) var(--space-1) 0;
  padding: 2px var(--space-2);
  border-radius: var(--radius-1);
  border: 1px solid var(--border-soft);
  background: var(--surface);
  font: inherit;
  font-size: var(--font-size-0);
  font-weight: 700;
  color: var(--text-muted);
  cursor: pointer;
}

.dist-chip.open {
  border-color: var(--border-strong);
  background: var(--surface-tint);
  color: var(--text-strong);
}

.dist-chip.unknown {
  color: var(--text-faint);
  font-style: italic;
}

.coverage-registry {
  display: grid;
  gap: var(--space-1);
}

.tier-chip {
  display: inline-block;
  margin: 0 var(--space-1) var(--space-1) 0;
  padding: 2px var(--space-2);
  border-radius: var(--radius-1);
  border: 1px solid var(--border-soft);
  background: var(--surface-tint);
  font-size: var(--font-size-0);
  font-weight: 700;
  color: var(--text-muted);
}

.registry-unclassified {
  margin: 0;
  color: var(--text-faint);
  font-size: var(--font-size-0);
  line-height: 1.5;
}

.coverage-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
}

.coverage-meta-item {
  display: grid;
  gap: 2px;
}

.meta-label {
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.meta-value {
  color: var(--text-heading);
  font-size: var(--font-size-1);
  font-weight: 800;
}

.meta-value em {
  font-style: normal;
  font-weight: 500;
  color: var(--text-faint);
}

.meta-value.unknown {
  color: var(--text-faint);
  font-weight: 700;
  font-size: var(--font-size-0);
}
</style>
