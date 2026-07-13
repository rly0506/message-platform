<script setup lang="ts">
import { computed } from 'vue'
import type { EventAnaloguesPayload, EventAnalogueBasis } from '../types/dossier'

const props = defineProps<{
  payload: EventAnaloguesPayload | null
  loading: boolean
  error: string
}>()

// basis.kind → 中文标签（后端只给英文 kind，前端不新增语义、只翻译）
const BASIS_LABELS: Record<string, string> = {
  shared_entity: '共享实体',
  shared_keyword: '共享关键词',
  shared_narrative_signal: '共享叙事信号',
  shared_source_tier: '共享来源层',
  similar_sample_shape: '样本形态相近',
}

function basisLabel(basis: EventAnalogueBasis): string {
  return BASIS_LABELS[basis.kind] || basis.kind
}

// 较强相似 = 实心徽标；有限相似 = 弱化。分数只是样本内结构信号重合度，不是可信度。
function scoreTone(label: string): string {
  return label === '较强相似' ? 'tone-strong' : 'tone-limited'
}

const items = computed(() => props.payload?.items ?? [])
const scan = computed(() => props.payload?.scan ?? null)
</script>

<template>
  <div class="event-analogues">
    <p class="event-structure-note">
      类比阅读：以下是全库其它话题中，与本事件在<b>样本内结构信号</b>（实体 / 关键词 / 叙事 / 来源层 / 样本形态）上重合的事件。
      相似≠同因、≠同果、≠会重演；每张卡片的<b>「差异提醒」必读</b>——类比用来对照，不用来预言。
    </p>

    <p v-if="error" class="country-compare-error">{{ error }}</p>
    <p v-else-if="loading" class="muted">正在扫描全库候选事件...</p>

    <template v-else-if="payload">
      <!-- 降级：诚实说明「为什么没有」，不伪造相似事件 -->
      <p v-if="payload.degraded" class="coverage-gap">
        {{ payload.degraded_reason || '该话题暂无持久化事件，无法生成类比。' }}
      </p>

      <template v-else>
        <div class="analogue-cards">
          <article
            v-for="item in items"
            :key="`${item.topic_id}-${item.event_id}`"
            class="analogue-card"
          >
            <header class="analogue-card-head">
              <div class="analogue-title">
                <strong>{{ item.title_zh }}</strong>
                <span class="analogue-meta">
                  {{ item.topic_name }}<template v-if="item.date"> · {{ item.date }}</template>
                </span>
              </div>
              <span class="analogue-score" :class="scoreTone(item.score_label)">{{ item.score_label }}</span>
            </header>

            <!-- 相似依据逐项：每条给出 kind + 具体命中项，不给黑箱分数 -->
            <div v-if="item.basis.length" class="analogue-basis">
              <strong class="analogue-section-label">相似依据</strong>
              <ul>
                <li v-for="basis in item.basis" :key="basis.kind">
                  <span class="basis-kind">{{ basisLabel(basis) }}</span>
                  <span class="basis-items">{{ basis.items.join('、') }}</span>
                </li>
              </ul>
            </div>

            <!-- 差异提醒：红线——必显、且视觉上必须显眼（类比不预言） -->
            <div class="analogue-diff">
              <strong class="analogue-section-label">差异提醒</strong>
              <ul v-if="item.differences.length">
                <li v-for="(diff, idx) in item.differences" :key="idx">{{ diff }}</li>
              </ul>
              <p v-else class="muted">后端未返回差异项——出于「类比不预言」原则，缺差异时请谨慎对待此相似。</p>
            </div>

            <footer class="analogue-card-foot">
              <div v-if="item.evidence_article_ids.length" class="analogue-evidence">
                <span>样本证据 {{ item.evidence_article_ids.length }} 篇</span>
                <a
                  v-for="article in item.evidence_articles"
                  :key="article.id"
                  :href="article.url"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ article.title }}</a>
              </div>
              <span class="analogue-item-note">{{ item.note }}</span>
            </footer>
          </article>
        </div>

        <!-- 空结果诚实措辞：区分「扫描过但未达阈值」与「不存在」——不说「无相似事件」 -->
        <p v-if="!items.length" class="muted analogue-empty">
          在已扫描的候选事件中，没有一个达到相似度阈值（有限相似 40 / 较强相似 70）。
          <template v-if="scan">这不代表全网无先例，只代表本库当前样本内未命中。</template>
        </p>

        <!-- 扫描范围诚实交代：扫了多少、是否被上限截断 -->
        <p v-if="scan" class="analogue-scan">{{ scan.note }}</p>
        <p v-if="payload.note" class="analogue-foot-note">{{ payload.note }}</p>
      </template>
    </template>

    <p v-else class="muted">选择一个事件后可扫描相似先例。</p>
  </div>
</template>

<style scoped>
.event-analogues {
  display: grid;
  gap: var(--space-3);
}

.event-structure-note {
  margin: 0;
  color: var(--text-faint);
  font-size: var(--font-size-0);
  line-height: 1.5;
}

.analogue-cards {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding-bottom: var(--space-2);
}

.analogue-card {
  display: grid;
  gap: var(--space-2);
  align-content: start;
  flex: 0 0 300px;
  padding: var(--space-3);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-3);
  background: var(--surface);
}

.analogue-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
}

.analogue-title {
  display: grid;
  gap: 2px;
}

.analogue-title strong {
  color: var(--text-strong);
  font-size: var(--font-size-1);
  line-height: 1.35;
}

.analogue-meta {
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.analogue-score {
  flex: 0 0 auto;
  padding: 2px var(--space-2);
  border-radius: var(--radius-round);
  border: 1px solid var(--border-strong);
  background: var(--surface-tint);
  color: var(--text-muted);
  font-size: var(--font-size-0);
  font-weight: 700;
  white-space: nowrap;
}

.analogue-score.tone-strong {
  border-color: var(--lens-rising-border);
  background: var(--lens-rising-bg);
  color: var(--lens-rising-fg);
}

.analogue-score.tone-limited {
  color: var(--text-faint);
}

.analogue-section-label {
  display: block;
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 700;
  margin-bottom: 2px;
}

.analogue-basis ul,
.analogue-diff ul {
  margin: 0;
  padding-left: 0;
  list-style: none;
  display: grid;
  gap: var(--space-1);
}

.analogue-basis li {
  display: grid;
  gap: 2px;
  font-size: var(--font-size-0);
  line-height: 1.45;
}

.basis-kind {
  color: var(--text-muted);
  font-weight: 700;
}

.basis-items {
  color: var(--text-heading);
}

/* 差异提醒视觉必须比依据更「拦人」：左侧警示条 + 暖色底 */
.analogue-diff {
  border-left: 3px solid var(--lens-hype-border);
  background: var(--lens-hype-bg);
  padding: var(--space-2);
  border-radius: var(--radius-1);
}

.analogue-diff .analogue-section-label {
  color: var(--lens-hype-fg);
}

.analogue-diff li {
  color: var(--text-muted);
  font-size: var(--font-size-0);
  line-height: 1.45;
}

.analogue-card-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2);
  border-top: 1px solid var(--border-soft);
  padding-top: var(--space-2);
}

.analogue-evidence {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  color: var(--text-muted);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.analogue-evidence a {
  color: var(--link);
  font-weight: 600;
}

.analogue-item-note {
  color: var(--text-faint);
  font-size: var(--font-size-0);
  line-height: 1.4;
}

.analogue-empty {
  line-height: 1.5;
}

.analogue-scan,
.analogue-foot-note {
  margin: 0;
  color: var(--text-faint);
  font-size: var(--font-size-0);
  line-height: 1.5;
}
</style>
