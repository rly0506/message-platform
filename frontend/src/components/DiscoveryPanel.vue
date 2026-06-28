<script setup lang="ts">
import type { DiscoveryReport, DiscoverySeed } from '../types/dossier'

type StepState = { key: string; label: string; status: string }

defineProps<{
  report: DiscoveryReport | null
  loading: boolean
  analyzing: boolean
  loaded: boolean
  error: string
  message: string
  activeJobId: string
  steps: StepState[]
  safeReportHtml: string
  hasReport: boolean
  seeds: DiscoverySeed[]
  seedBusy: boolean
  activeSeedUrl: string
  seedNote: string
  stepStatusText: (status: string) => string
}>()

defineEmits<{
  runDiscovery: []
  analyzeSeed: [seed: DiscoverySeed]
}>()

function fmtRunId(runId: string | undefined) {
  if (!runId) return ''
  // 形如 20260628T123000Z 或 2026-06-28T12:30:00Z，统一抽出日期+时间显示
  const compact = runId.replace(/[-:]/g, '')
  const m = compact.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/)
  if (!m) return runId
  return `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]} UTC`
}
</script>

<template>
  <section class="feed-pane tab-pane-wide">
    <section class="wide-panel discovery-panel">
      <div class="pane-header compact">
        <div>
          <p class="eyebrow">Cognitive Frontier</p>
          <h2>认知前沿</h2>
        </div>
        <button type="button" class="cross-primary-button" :disabled="analyzing" @click="$emit('runDiscovery')">
          {{ analyzing ? '分析中...' : '🔄 立即分析（LLM）' }}
        </button>
      </div>

      <div class="cross-synthesis-note">
        <strong>全局视角：从注意力前沿（Hacker News + arXiv + 智库）里捞出还没出圈、但在加速的"种子"</strong>
        <span>每天中午自动跑一份基线日报；点上面的按钮则即时跑一轮带 LLM 标注的深读（给每条种子标"这是什么/为何重要"）。</span>
        <span>看到值得追的种子，点它的「🔍 深入分析」——系统会把它提炼成话题词，送进事件分析台跨媒体追踪。</span>
      </div>

      <p v-if="activeJobId" class="search-message">发现任务：{{ activeJobId.slice(0, 8) }}</p>
      <p v-if="message" class="search-message">{{ message }}</p>
      <div v-if="steps.length" class="step-list deep-step-list">
        <span v-for="step in steps" :key="step.key" :class="`step-${step.status}`">
          {{ step.label }} · {{ stepStatusText(step.status) }}
        </span>
      </div>

      <p v-if="loading" class="muted">正在读取最新日报...</p>
      <p v-else-if="error" class="country-compare-error">{{ error }}</p>

      <template v-else-if="hasReport">
        <p v-if="report?.run_id" class="discovery-meta">报告时间：{{ fmtRunId(report.run_id) }}</p>

        <div v-if="seeds.length" class="seed-stream">
          <div class="seed-stream-head">
            <strong>🌱 可追踪的种子（{{ seeds.length }}）</strong>
            <span>一眼扫过去，看到值得追的点「深入」送进事件分析台</span>
          </div>
          <p v-if="seedNote" class="seed-note">{{ seedNote }}</p>
          <ol class="stream">
            <li
              v-for="seed in seeds"
              :key="seed.url"
              class="stream-row"
              :class="`tier-${seed.domain}`"
            >
              <span class="stream-tag">{{ seed.domain_label }}</span>
              <div class="stream-main">
                <a class="stream-title" :href="seed.url" target="_blank" rel="noopener">{{ seed.title }}</a>
                <p v-if="seed.what || seed.why" class="stream-note">
                  {{ seed.what }}<template v-if="seed.why"> — {{ seed.why }}</template>
                </p>
              </div>
              <div class="stream-signals">
                <span v-if="seed.is_new" class="sig sig-new">新</span>
                <span v-else-if="seed.delta > 0" class="sig sig-up">↑{{ seed.delta }}</span>
                <span class="sig sig-heat" :title="`关注度信号 ${seed.signal}`">🔥{{ seed.signal }}</span>
              </div>
              <button
                type="button"
                class="stream-go"
                :disabled="seedBusy"
                @click="$emit('analyzeSeed', seed)"
              >
                {{ seedBusy && activeSeedUrl === seed.url ? '…' : '深入 →' }}
              </button>
            </li>
          </ol>
        </div>

        <div class="analysis markdown-body discovery-report" v-html="safeReportHtml" />
      </template>

      <p v-else-if="loaded" class="muted">
        还没有任何认知前沿日报。点上面的「🔄 立即分析」生成第一份（首次只建基线，明天起才有加速信号）。
      </p>
    </section>
  </section>
</template>

<style scoped>
.discovery-meta {
  margin: 0 0 0.75rem;
  font-size: 0.85rem;
  color: var(--muted, #6b7280);
}

.seed-stream {
  margin: 0 0 1.25rem;
}

.seed-stream-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.seed-stream-head strong {
  color: #155a6e;
}

.seed-stream-head span {
  font-size: 0.8rem;
  color: #6b7280;
}

.seed-note {
  margin: 0 0 10px;
  padding: 6px 10px;
  border-radius: 6px;
  background: #fff4e0;
  color: #8a5a00;
  font-size: 0.82rem;
}

/* Trading Economics 式信息流：每条一行，密集、可扫 */
.stream {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid #e2eaed;
  border-radius: 10px;
  overflow: hidden;
}

.stream-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px;
  border-top: 1px solid #eef2f4;
  border-left: 3px solid #cbd5db;
  background: #fff;
  transition: background 0.12s;
}

.stream-row:first-child {
  border-top: none;
}

.stream-row:hover {
  background: #f8fbfc;
}

/* 领域色轨：科技/财经/地缘一眼区分 */
.stream-row.tier-tech { border-left-color: #2f80ed; }
.stream-row.tier-finance { border-left-color: #27ae60; }
.stream-row.tier-geopolitics { border-left-color: #c0392b; }
.stream-row.tier-science { border-left-color: #8e44ad; }

.stream-tag {
  flex-shrink: 0;
  width: 64px;
  font-size: 0.72rem;
  font-weight: 800;
  color: #24515f;
  line-height: 1.2;
}

.stream-main {
  flex: 1;
  min-width: 0;
}

.stream-title {
  display: block;
  color: #1c2329;
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stream-row:hover .stream-title {
  white-space: normal;
}

.stream-title:hover {
  text-decoration: underline;
}

.stream-note {
  margin: 2px 0 0;
  font-size: 0.78rem;
  color: #7a8590;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stream-row:hover .stream-note {
  white-space: normal;
}

.stream-signals {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 5px;
}

.sig {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.sig-new { background: #e8f5ee; color: #1e7e44; }
.sig-up { background: #fdeaea; color: #c0392b; }
.sig-heat { background: #fff3e0; color: #b5651d; }

.stream-go {
  flex-shrink: 0;
  border: 1px solid #cbd5db;
  background: #fff;
  color: #155a6e;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}

.stream-go:hover:not(:disabled) {
  background: #155a6e;
  color: #fff;
  border-color: #155a6e;
}

.stream-go:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
