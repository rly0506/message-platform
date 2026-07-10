<script setup lang="ts">
import { computed } from 'vue'
import type { EventContrastPayload, EventContrastSource } from '../types/dossier'

const props = defineProps<{
  payload: EventContrastPayload | null
  loading: boolean
  error: string
}>()

// 立场徽标复用透镜色（克制，不新增色板）
function stanceTone(stance: string): string {
  const s = stance || ''
  if (/风险|冲突|安全|升级/.test(s)) return 'tone-hype'
  if (/影响|后果|市场/.test(s)) return 'tone-rising'
  if (/中性|观察|外交|降温/.test(s)) return 'tone-herding'
  return ''
}

// 干货/情绪分数只在 >=0 时显示（-1 = 未富化，诚实标"未评分"，不伪造）
function hasScore(value: number | null | undefined): boolean {
  return typeof value === 'number' && value >= 0
}

const sources = computed<EventContrastSource[]>(() => props.payload?.sources ?? [])
const gaps = computed(() => props.payload?.coverage_gaps ?? [])
const event = computed(() => props.payload?.event ?? null)
</script>

<template>
  <div class="event-contrast">
    <p class="event-structure-note">
      主题阅读：把同一事件下各来源的报道并排对照——各自强调什么、立场如何、证据密度差异在哪。
      「覆盖差异」= 某个对象/关键词只在部分来源被提及，是覆盖面差异，不代表蓄意隐瞒。
    </p>

    <p v-if="error" class="country-compare-error">{{ error }}</p>
    <p v-else-if="loading" class="muted">正在读取多源对照...</p>

    <template v-else-if="payload">
      <p v-if="payload.degraded" class="coverage-gap">{{ payload.note || '样本不足，无法生成多源对照。' }}</p>

      <template v-else-if="sources.length">
        <div v-if="event" class="contrast-head">
          <strong>{{ event.title_zh }}</strong>
          <span>{{ event.source_count }} 个来源 · {{ event.article_count }} 篇报道</span>
        </div>

        <!-- 来源并排列：横向滚动，每列一个来源 -->
        <div class="contrast-columns">
          <article v-for="src in sources" :key="src.source" class="contrast-col">
            <header class="contrast-col-head">
              <strong>{{ src.source }}</strong>
              <span class="contrast-tier">{{ src.tier_label || '其他来源' }}</span>
            </header>

            <span class="contrast-stance" :class="stanceTone(src.stance)">{{ src.stance || '立场未判定' }}</span>
            <p v-if="src.stance_summary" class="contrast-stance-summary">{{ src.stance_summary }}</p>

            <dl class="contrast-scores">
              <div>
                <dt>干货</dt>
                <dd v-if="hasScore(src.substance_score)">
                  {{ src.substance_score }}
                  <em v-if="src.substance_note">{{ src.substance_note }}</em>
                </dd>
                <dd v-else class="unscored">未评分</dd>
              </div>
              <div>
                <dt>情绪</dt>
                <dd v-if="hasScore(src.emotion_score)">
                  {{ src.emotion_score }}
                  <em v-if="src.emotion_note">{{ src.emotion_note }}</em>
                </dd>
                <dd v-else class="unscored">未评分</dd>
              </div>
            </dl>

            <div v-if="src.emphasized_entities.length || src.emphasized_keywords.length" class="contrast-emphasis">
              <strong>强调</strong>
              <span
                v-for="term in src.emphasized_entities"
                :key="`e-${term.term}`"
                class="emphasis-chip is-entity"
              >{{ term.term }}<i v-if="term.count > 1">×{{ term.count }}</i></span>
              <span
                v-for="term in src.emphasized_keywords"
                :key="`k-${term.term}`"
                class="emphasis-chip is-keyword"
              >{{ term.term }}<i v-if="term.count > 1">×{{ term.count }}</i></span>
            </div>

            <!-- 证据始终可见（审计红线）：代表文章可点回原文 -->
            <ul v-if="src.articles.length" class="contrast-articles">
              <li v-for="art in src.articles" :key="art.id">
                <a :href="art.url" target="_blank" rel="noopener noreferrer">{{ art.title }}</a>
              </li>
            </ul>
          </article>
        </div>

        <!-- 覆盖差异：中性措辞 + 可点回证据 -->
        <div v-if="gaps.length" class="contrast-gaps">
          <strong>覆盖差异</strong>
          <ul>
            <li
              v-for="gap in gaps"
              :key="`${gap.kind}-${gap.term}`"
              class="contrast-gap-row"
              :class="{ weak: gap.salience <= 1 }"
            >
              <span class="gap-term" :class="gap.kind === 'entity' ? 'is-entity' : 'is-keyword'">{{ gap.term }}</span>
              <span class="gap-strength">强调 ×{{ gap.salience }}</span>
              <span class="gap-covered">仅见于 {{ gap.covered_by.join('、') }}</span>
              <span class="gap-missing">未在 {{ gap.not_observed_in.join('、') }} 的样本中观察到</span>
            </li>
          </ul>
        </div>
      </template>

      <p v-else class="muted">该事件暂无足够来源生成对照。</p>
    </template>

    <p v-else class="muted">选择一个事件后可生成多源对照。</p>
  </div>
</template>

<style scoped>
.event-contrast {
  display: grid;
  gap: var(--space-3);
}

.event-structure-note {
  margin: 0;
  color: var(--text-faint);
  font-size: var(--font-size-0);
  line-height: 1.5;
}

.contrast-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--space-2);
}

.contrast-head strong {
  color: var(--text-heading);
  font-size: var(--font-size-2);
}

.contrast-head span {
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.contrast-columns {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding-bottom: var(--space-2);
}

.contrast-col {
  display: grid;
  gap: var(--space-2);
  align-content: start;
  flex: 0 0 220px;
  padding: var(--space-3);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-3);
  background: var(--surface);
}

.contrast-col-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-2);
}

.contrast-col-head strong {
  color: var(--text-strong);
  font-size: var(--font-size-1);
}

.contrast-tier {
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.contrast-stance {
  justify-self: start;
  padding: 2px var(--space-2);
  border-radius: var(--radius-round);
  border: 1px solid var(--border-strong);
  background: var(--surface-tint);
  color: var(--text-muted);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.contrast-stance.tone-hype {
  border-color: var(--lens-hype-border);
  background: var(--lens-hype-bg);
  color: var(--lens-hype-fg);
}

.contrast-stance.tone-rising {
  border-color: var(--lens-rising-border);
  background: var(--lens-rising-bg);
  color: var(--lens-rising-fg);
}

.contrast-stance.tone-herding {
  border-color: var(--lens-herding-border);
  background: var(--lens-herding-bg);
  color: var(--lens-herding-fg);
}

.contrast-stance-summary {
  margin: 0;
  color: var(--text-muted);
  font-size: var(--font-size-1);
  line-height: 1.5;
}

.contrast-scores {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
  margin: 0;
}

.contrast-scores dt {
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.contrast-scores dd {
  margin: 0;
  color: var(--text-heading);
  font-size: var(--font-size-1);
  font-weight: 800;
}

.contrast-scores dd em {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--font-size-0);
  font-weight: 500;
  font-style: normal;
  line-height: 1.4;
}

.contrast-scores dd.unscored {
  color: var(--text-faint);
  font-weight: 700;
}

.contrast-emphasis {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
}

.contrast-emphasis strong {
  color: var(--text-faint);
  font-size: var(--font-size-0);
  margin-right: var(--space-1);
}

.emphasis-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 1px var(--space-2);
  border-radius: var(--radius-1);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.emphasis-chip i {
  font-style: normal;
  opacity: 0.7;
}

.emphasis-chip.is-entity {
  background: var(--lens-rising-bg);
  color: var(--lens-rising-fg);
}

.emphasis-chip.is-keyword {
  background: var(--surface-tint);
  color: var(--text-muted);
}

.contrast-articles {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.contrast-articles a {
  color: var(--brand);
  font-size: var(--font-size-0);
  line-height: 1.4;
  text-decoration: none;
}

.contrast-articles a:hover {
  text-decoration: underline;
}

.contrast-gaps {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-3);
  background: var(--surface-tint);
}

.contrast-gaps > strong {
  color: var(--text-heading);
  font-size: var(--font-size-1);
}

.contrast-gaps ul {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.contrast-gap-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-0);
}

.gap-term {
  padding: 1px var(--space-2);
  border-radius: var(--radius-1);
  font-weight: 800;
}

.gap-term.is-entity {
  background: var(--lens-rising-bg);
  color: var(--lens-rising-fg);
}

.gap-term.is-keyword {
  background: var(--surface-tint-2);
  color: var(--text-muted);
}

.gap-covered {
  color: var(--text-muted);
  font-weight: 700;
}

.gap-missing {
  color: var(--text-faint);
}

.gap-strength {
  color: var(--text-faint);
  font-weight: 700;
}

/* 弱差异（salience==1，仅单次提及）淡化：不隐藏、不静默丢，只降视觉权重，让强信号先被看见 */
.contrast-gap-row.weak {
  opacity: 0.55;
}
</style>
