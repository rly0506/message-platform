<script setup lang="ts">
import { computed } from 'vue'
import type { CognitionLabel, CognitionMark, CognitionProfileItem, DiscoveryReport, DiscoverySeed, TopicSummary } from '../types/dossier'

type StepState = { key: string; label: string; status: string }
type BoundarySeed = { seed: DiscoverySeed; reason: string; profile: CognitionProfileItem | null }

const props = defineProps<{
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
  trackedTopics: TopicSummary[]
  seedCognitionMarks: Record<string, CognitionMark>
  cognitionProfile: CognitionProfileItem[]
  cognitionMarkError: string
  stepStatusText: (status: string) => string
}>()

defineEmits<{
  runDiscovery: []
  analyzeSeed: [seed: DiscoverySeed]
  trackTopic: [topicId: number]
  markSeedCognition: [seed: DiscoverySeed, label: CognitionLabel, note?: string]
}>()

const boundaryQueue = computed<BoundarySeed[]>(() => {
  return props.seeds
    // 已点「我懂了」(known) 的从队列移除 —— 形成可见闭环: 点完即少一条。
    .filter((seed) => props.seedCognitionMarks[seed.url]?.label !== 'known')
    .map((seed) => ({ seed, ...boundaryReason(seed) }))
    .sort((a, b) => reasonRank(a.reason) - reasonRank(b.reason) || b.seed.signal - a.seed.signal)
    .slice(0, 10)
})

function fmtRunId(runId: string | undefined) {
  if (!runId) return ''
  // 形如 20260628T123000Z 或 2026-06-28T12:30:00Z，统一抽出日期+时间显示
  const compact = runId.replace(/[-:]/g, '')
  const m = compact.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/)
  if (!m) return runId
  return `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]} UTC`
}

// 「正在追踪」: 把 latest_published_at 转成"最近变化"的相对天数, 让一眼看出哪个专题在动。
function freshness(iso: string | null): string {
  if (!iso) return '暂无报道'
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const days = Math.floor((Date.now() - then) / 86_400_000)
  if (days <= 0) return '今天有更新'
  if (days === 1) return '1 天前'
  if (days <= 30) return `${days} 天前`
  if (days <= 60) return '1 个月前'
  return `${Math.floor(days / 30)} 个月前`
}

function isStale(iso: string | null): boolean {
  if (!iso) return true
  const then = new Date(iso).getTime()
  return Number.isNaN(then) || (Date.now() - then) > 14 * 86_400_000
}

function boundaryReason(seed: DiscoverySeed): { reason: string; profile: CognitionProfileItem | null } {
  const profile = profileForSeed(seed)
  if (profile?.level === 'unfamiliar') return { reason: '边界外', profile }
  if (profile?.level === 'partial') return { reason: '机制缺口', profile }
  if (profile?.level === 'strong_partial') return { reason: '课程相关', profile }
  return { reason: seed.is_new ? '新信号' : '加速信号', profile: null }
}

function profileForSeed(seed: DiscoverySeed) {
  const text = `${seed.domain} ${seed.domain_label} ${seed.title} ${seed.what} ${seed.why}`.toLowerCase()
  const wanted = [
    ['energy', ['energy', 'nuclear', '新能源', '核能', '能源']],
    ['ai_infra', ['gpu', 'cpu', 'cpo', 'compute', '算力', '大模型']],
    ['finance', ['finance', 'credit', 'market', '银行', '金融', '融资']],
    ['crypto', ['crypto', 'stablecoin', 'bitcoin', 'ethereum', '稳定币', '比特币']],
    ['biotech', ['bio', 'drug', 'gene', '生物', '基因']],
    ['open_source', ['github', 'open source', '开源']],
    ['industrial_policy', ['industrial policy', '产业政策']],
    ['geopolitics', ['geopolitics', 'war', '地缘', '冲突']],
  ]
  const match = wanted.find(([, words]) => (words as string[]).some((word) => text.includes(word)))
  return props.cognitionProfile.find((item) => item.domain_key === match?.[0]) || null
}

function reasonRank(reason: string) {
  return ['边界外', '机制缺口', '课程相关'].indexOf(reason) + 1 || 9
}
</script>

<template>
  <section class="feed-pane tab-pane-wide">
    <section class="wide-panel discovery-panel">
      <div class="pane-header compact">
        <div>
          <p class="eyebrow">Intelligence Desk</p>
          <h2>今日情报台</h2>
        </div>
        <button type="button" class="cross-primary-button" :disabled="analyzing" @click="$emit('runDiscovery')">
          {{ analyzing ? '分析中...' : '🔄 立即分析（LLM）' }}
        </button>
      </div>

      <div class="cross-synthesis-note">
        <strong>鸟瞰：下面是你正在追踪的专题，以及今日注意力前沿里还没出圈、但在加速的"种子"</strong>
        <span>「正在追踪」点任一专题即跳进事件分析台看它的最新档案；「今日前沿」每天中午自动跑基线，点上面按钮即时跑带 LLM 标注的深读。</span>
        <span>看到值得追的种子，点「🔍 深入分析」——系统提炼成话题词，送进事件分析台跨媒体追踪。</span>
      </div>

      <div v-if="trackedTopics.length" class="tracking-block">
        <div class="tracking-head">
          <strong>📌 正在追踪（{{ trackedTopics.length }}）</strong>
          <span>点一个跳进分析台看最新进展</span>
        </div>
        <ol class="tracking-list">
          <li
            v-for="topic in trackedTopics"
            :key="topic.id"
            class="tracking-row"
            :class="{ stale: isStale(topic.latest_published_at) }"
          >
            <button type="button" class="tracking-main" @click="$emit('trackTopic', topic.id)">
              <span class="tracking-name">{{ topic.name }}</span>
              <span class="tracking-meta">
                {{ topic.article_count }} 篇 · {{ topic.source_count }} 源 · {{ freshness(topic.latest_published_at) }}
              </span>
            </button>
          </li>
        </ol>
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
      <p v-if="cognitionMarkError" class="country-compare-error">{{ cognitionMarkError }}</p>

      <template v-else-if="hasReport">
        <p v-if="report?.run_id" class="discovery-meta">报告时间：{{ fmtRunId(report.run_id) }}</p>

        <div v-if="seeds.length" class="seed-stream">
          <div class="boundary-queue">
            <div class="seed-stream-head">
              <strong>认知边界队列（{{ boundaryQueue.length }}）</strong>
              <span>系统按你的认知边界挑出来的，点「我懂了」即收进已认识</span>
            </div>
            <ol class="boundary-list">
              <li v-for="item in boundaryQueue" :key="`boundary-${item.seed.url}`">
                <div class="boundary-main">
                  <span class="boundary-reason">{{ item.reason }}</span>
                  <strong>{{ item.seed.title }}</strong>
                  <em v-if="item.profile">{{ item.profile.domain_label }}</em>
                </div>
                <div class="boundary-actions">
                  <button
                    type="button"
                    class="boundary-got-it"
                    title="我已经认识这件事了，从队列收走"
                    @click="$emit('markSeedCognition', item.seed, 'known')"
                  >
                    我懂了
                  </button>
                  <button
                    type="button"
                    class="boundary-doubt"
                    title="存疑，先标记"
                    @click="$emit('markSeedCognition', item.seed, 'doubtful')"
                  >
                    存疑
                  </button>
                </div>
              </li>
            </ol>
            <p v-if="!boundaryQueue.length" class="seed-note">队列已清空，今天的认知边界都过了一遍 👍</p>
          </div>

          <div class="seed-stream-head">
            <strong>🌱 今日前沿种子（{{ seeds.length }}）</strong>
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
              </div>
              <div class="cognition-mark-row seed-mark-row" aria-label="认知标记">
                <button
                  type="button"
                  :class="['cognition-chip', { active: seedCognitionMarks[seed.url]?.label === 'known' }]"
                  title="我已经认识这件事了"
                  @click="$emit('markSeedCognition', seed, 'known')"
                >
                  我懂了
                </button>
                <button
                  type="button"
                  :class="['cognition-chip', { active: seedCognitionMarks[seed.url]?.label === 'doubtful' }]"
                  title="存疑，先标记"
                  @click="$emit('markSeedCognition', seed, 'doubtful')"
                >
                  存疑
                </button>
                <span v-if="seedCognitionMarks[seed.url]?.label === 'known'" class="seed-mark-done">已认识</span>
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

/* 正在追踪: 已建专题的鸟瞰, 点一个跳进分析台 */
.tracking-block {
  margin: 0 0 1.25rem;
  padding: 12px 14px;
  border: 1px solid #d7e0e4;
  border-radius: 10px;
  background: #fafcfd;
}

.tracking-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.tracking-head strong {
  color: #155a6e;
}

.tracking-head span {
  font-size: 0.8rem;
  color: #6b7280;
}

.tracking-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tracking-row {
  border-radius: 8px;
}

.tracking-main {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  border: none;
  border-left: 3px solid #27ae60;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: background 0.12s;
}

.tracking-main:hover {
  background: #eef7f9;
}

/* 14 天没新报道 = 转冷, 左轨变灰、文字变淡, 一眼区分"在动 vs 沉寂" */
.tracking-row.stale .tracking-main {
  border-left-color: #c2cdd2;
}

.tracking-row.stale .tracking-name {
  color: #8593a0;
}

.tracking-name {
  flex: 1;
  min-width: 0;
  font-weight: 700;
  color: #1c2329;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tracking-meta {
  flex-shrink: 0;
  font-size: 0.76rem;
  color: #6b7280;
  white-space: nowrap;
}

.seed-stream {
  margin: 0 0 1.25rem;
}

.boundary-queue {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid #d7e0e4;
  border-radius: 10px;
  background: #f8fbfc;
}

.boundary-list {
  display: grid;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.boundary-list li {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  color: #53636e;
  font-size: 0.78rem;
}

.boundary-main {
  display: flex;
  gap: 8px;
  align-items: center;
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
}

.boundary-reason {
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: 999px;
  background: #fff4e0;
  color: #8a5a00;
  font-weight: 800;
}

.boundary-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.boundary-got-it,
.boundary-doubt {
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid #c5d2d8;
  background: #fff;
  color: #2c3a44;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
}

.boundary-got-it:hover {
  background: #e6f5ec;
  border-color: #1e7e44;
  color: #1e7e44;
}

.boundary-doubt:hover {
  background: #f0f3f5;
}

.boundary-list strong {
  min-width: 0;
  overflow: hidden;
  color: #1c2329;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.boundary-list em {
  color: #71808a;
  font-style: normal;
  white-space: nowrap;
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
  flex-wrap: wrap;
  gap: 10px;
  padding: 7px 12px;
  border-top: 1px solid #eef2f4;
  border-left: 3px solid #cbd5db;
  background: #fff;
  transition: background 0.12s;
}

.seed-mark-row {
  flex: 0 0 auto;
  margin-top: 0;
  align-items: center;
}

.seed-mark-done {
  font-size: 0.72rem;
  color: #1e7e44;
  font-weight: 700;
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
