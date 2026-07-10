<script setup lang="ts">
import { computed } from 'vue'
import type {
  CognitionLabel,
  CognitionMark,
  CognitionProfileItem,
  DiscoveryReport,
  DiscoveryReportMeta,
  DiscoverySeed,
  DiscoveryTimelineItem,
  DiscoveryTimelineTree,
  TopicSummary,
} from '../types/dossier'

type StepState = { key: string; label: string; status: string }
type BoundarySeed = {
  seed: DiscoverySeed
  reason: string
  profile: CognitionProfileItem | null
  score: number
  workflow: string
}
type DomainRule = {
  key: string
  words: string[]
  workflow: string
}

const domainRules: DomainRule[] = [
  {
    key: 'energy',
    words: ['energy', 'nuclear', 'battery', 'grid', '新能源', '核能', '能源', '电力'],
    workflow: '先拆清能源类型、电力供给、成本曲线和替代能源，再看谁真正受益。',
  },
  {
    key: 'electricity',
    words: ['electricity', 'power grid', 'data center power', '电网', '发电', '供电', '数据中心用电'],
    workflow: '先看负荷曲线、发电结构、电网约束和长期用电合同，再判断受益者。',
  },
  {
    key: 'ai_infra',
    words: ['gpu', 'cpu', 'cpo', 'compute', 'inference', '算力', '推理', '大模型', '数据中心'],
    workflow: '先区分训练与推理，再追问成本口径、芯片供给、利用率和替代方案。',
  },
  {
    key: 'finance',
    words: ['finance', 'credit', 'market', 'bank', 'valuation', '融资', '银行', '金融', '估值', '财报'],
    workflow: '用财报、现金流、成本和需求曲线追问，不只看标题里的增长叙事。',
  },
  {
    key: 'macro_finance',
    words: ['fed', 'rate cut', 'liquidity', 'dollar', 'interest rate', '美联储', '降息', '流动性', '美元'],
    workflow: '先拆利率、流动性、汇率和资产配置链条，再找数据口径验证。',
  },
  {
    key: 'open_source',
    words: ['github', 'open source', 'oss', '开源', 'star'],
    workflow: '先看维护者、许可证、提交活跃度、安全记录和商业使用边界。',
  },
  {
    key: 'crypto',
    words: ['crypto', 'stablecoin', 'bitcoin', 'ethereum', '加密', '稳定币', '比特币', '以太币'],
    workflow: '先追问锚定资产、储备透明度、监管责任、流动性和极端赎回风险。',
  },
  {
    key: 'biotech',
    words: ['bio', 'drug', 'gene', 'clinical', '生物', '医药', '基因', '临床'],
    workflow: '先找论文和临床阶段，再分开看科学突破、监管审批和资本市场叙事。',
  },
  {
    key: 'geopolitics',
    words: ['geopolitics', 'war', 'export control', 'chip ban', '地缘', '冲突', '出口限制', '芯片禁令'],
    workflow: '先拆各方激励、替代品、政策周期和产业能力，不用单一阵营叙事下结论。',
  },
  {
    key: 'industrial_policy',
    words: ['industrial policy', 'supply chain', '产业政策', '供应链', '补贴'],
    workflow: '先看政策工具、产业瓶颈、补贴对象和替代路径，再判断长期效果。',
  },
  {
    key: 'law_regulation',
    words: ['regulation', 'law', 'compliance', 'privacy', '监管', '法律', '合规', '隐私'],
    workflow: '先看监管主体、责任边界、处罚案例和数据/支付/平台规则。',
  },
  {
    key: 'social_structure',
    words: ['demographic', 'labor', 'society', 'population', '人口', '就业', '社会结构'],
    workflow: '先区分情绪样本和结构数据，再看群体、地区、时间和制度约束。',
  },
  {
    key: 'engineering_infra',
    words: ['infrastructure', 'engineering', 'manufacturing', '工程', '制造', '基础设施'],
    workflow: '先追问物理约束、供应链、良率、维护成本和规模化瓶颈。',
  },
  {
    key: 'media_literacy',
    words: ['must', 'forever', 'only winner', '6 months', '焦虑', '永远错过', '唯一受益', '必须'],
    workflow: '先标出绝对化词语，再追问证据、时间口径、反例和利益相关方。',
  },
]

const props = defineProps<{
  report: DiscoveryReport | null
  loading: boolean
  analyzing: boolean
  loaded: boolean
  error: string
  message: string
  activeJobId: string
  steps: StepState[]
  discoveryReports: DiscoveryReportMeta[]
  selectedDiscoveryRunId: string
  discoveryTimelineTree: DiscoveryTimelineTree
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

const emit = defineEmits<{
  runDiscovery: []
  analyzeSeed: [seed: DiscoverySeed]
  trackTopic: [topicId: number]
  markTopicForDig: [topic: { id: number; name: string }]
  markSeedCognition: [seed: DiscoverySeed, label: CognitionLabel, note?: string]
  selectDiscoveryReport: [runId: string]
}>()

const boundaryQueue = computed<BoundarySeed[]>(() => {
  return props.seeds
    // 已点「我懂了」(known) 的从队列移除 —— 形成可见闭环: 点完即少一条。
    .filter((seed) => props.seedCognitionMarks[seed.url]?.label !== 'known')
    .map((seed) => ({ seed, ...boundaryReason(seed) }))
    .sort((a, b) => b.score - a.score || b.seed.signal - a.seed.signal)
    .slice(0, 10)
})

// 「其余种子」= 全量种子里, 排除 (a) 当前边界队列展示的 10 条 + (b) 已点「我懂了」的。
// 避免与队列重复, 也避免"我懂了"后又冒出来。默认折叠, 想扫全量再展开。
const restSeeds = computed(() => {
  const inQueue = new Set(boundaryQueue.value.map((item) => item.seed.url))
  return props.seeds.filter(
    (seed) => !inQueue.has(seed.url) && props.seedCognitionMarks[seed.url]?.label !== 'known',
  )
})

const headlineItems = computed(() => boundaryQueue.value.slice(0, 5))

// 今日头版「追踪动态」: 追踪话题里"最近有新报道"的挑出来置顶, 打开就见"我关注的事今天有什么动静"。
// 纯前端派生自 latest_published_at, 无后端新端点。非 stale(14天内有更新)才算"在动", 按最新时间排序取前 4。
const trackedUpdates = computed(() => {
  return props.trackedTopics
    .filter((topic) => !isStale(topic.latest_published_at))
    .slice()
    .sort((a, b) => {
      const ta = a.latest_published_at ? new Date(a.latest_published_at).getTime() : 0
      const tb = b.latest_published_at ? new Date(b.latest_published_at).getTime() : 0
      return tb - ta
    })
    .slice(0, 4)
})
const latestRunId = computed(() => props.discoveryReports[0]?.run_id || props.report?.run_id || '')
const isHistoricalReport = computed(() => Boolean(props.report?.run_id && latestRunId.value && props.report.run_id !== latestRunId.value))
const timelineBranches = computed(() => props.discoveryTimelineTree?.branches || [])

function fmtRunId(runId: string | undefined) {
  if (!runId) return ''
  // 形如 20260628T123000Z 或 2026-06-28T12:30:00Z，统一抽出日期+时间显示
  const compact = runId.replace(/[-:]/g, '')
  const m = compact.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/)
  if (!m) return runId
  return `${m[1]}-${m[2]}-${m[3]} ${m[4]}:${m[5]} UTC`
}

function selectReport(event: Event) {
  const runId = (event.target as HTMLSelectElement).value
  if (runId) {
    emit('selectDiscoveryReport', runId)
  }
}

function seedFromTimelineItem(item: DiscoveryTimelineItem): DiscoverySeed {
  return {
    title: item.title,
    url: item.url,
    domain: item.domain,
    domain_label: item.domain_label,
    signal: item.signal,
    delta: item.delta,
    is_new: false,
    what: item.title,
    why: item.why,
    still_niche: true,
  }
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

function boundaryReason(seed: DiscoverySeed): Omit<BoundarySeed, 'seed'> {
  const { profile, rule } = profileForSeed(seed)
  const reason = reasonForProfile(seed, profile)
  return {
    reason,
    profile,
    score: boundaryScore(seed, profile, reason),
    workflow: rule?.workflow || workflowForStyle(profile?.recommended_seed_style),
  }
}

function recommendationText(item: BoundarySeed) {
  if (item.reason === '边界外') return '你的画像里这块较陌生，适合放进认知边界。'
  if (item.reason === '机制缺口') return '你知道相关名词，但机制仍有缺口。'
  if (item.reason === '课程相关') return '它接近你的课程背景，但可能给出新的应用场景。'
  if (item.reason === '新信号') return '这是新出现的前沿信号，值得先看一眼。'
  return '这个方向正在加速，适合判断是否继续追踪。'
}

function nextActionText(item: BoundarySeed) {
  const style = styleLabel(item.profile?.recommended_seed_style)
  if (item.seed.what) return `送进事件分析台：${item.seed.what}；${style}`
  return `送进事件分析台做跨媒体追踪；${style}`
}

function seedSummary(seed: DiscoverySeed) {
  return seed.what || seed.title || '暂无摘要'
}

function seedReportConnection(seed: DiscoverySeed) {
  const branch = timelineBranches.value.find((item) =>
    item.branch_key === seed.domain ||
    item.label === seed.domain_label ||
    item.items.some((entry) => entry.url === seed.url),
  )
  if (!branch) return '今日日报新线索，尚未形成跨日报分支。'
  const related = branch.items
    .filter((item) => item.url !== seed.url)
    .map((item) => item.why || item.title)
    .filter(Boolean)
    .slice(0, 2)
  const suffix = related.length ? `；相关：${related.join(' / ')}` : ''
  return `认知时间树：${branch.label}${suffix}`
}

function seedDeepReason(item: BoundarySeed) {
  return item.seed.why || recommendationText(item)
}

function profileForSeed(seed: DiscoverySeed) {
  const text = `${seed.domain} ${seed.domain_label} ${seed.title} ${seed.what} ${seed.why}`.toLowerCase()
  const direct = props.cognitionProfile.find((item) => item.domain_key === seed.domain)
  const directRule = domainRules.find((rule) => rule.key === direct?.domain_key)
  if (direct) return { profile: direct, rule: directRule }
  const rule = domainRules.find((item) => item.words.some((word) => text.includes(word)))
  return {
    profile: props.cognitionProfile.find((item) => item.domain_key === rule?.key) || null,
    rule,
  }
}

function reasonForProfile(seed: DiscoverySeed, profile: CognitionProfileItem | null) {
  if (profile?.level === 'unfamiliar') return '边界外'
  if (profile?.level === 'partial') return profile.depth === 'terms' ? '机制缺口' : '模型校准'
  if (profile?.level === 'strong_partial') return '课程相关'
  return seed.is_new ? '新信号' : '加速信号'
}

function boundaryScore(seed: DiscoverySeed, profile: CognitionProfileItem | null, reason: string) {
  const reasonBoost: Record<string, number> = {
    边界外: 80,
    机制缺口: 65,
    模型校准: 58,
    课程相关: 52,
    新信号: 42,
    加速信号: 35,
  }
  // interest(想不想看)是干净的"想要更多"信号, 保留。
  const interestBoost = profile?.interest === 'high' ? 16 : profile?.interest === 'medium' ? 8 : 0
  // confidence(懂多少)不再参与排序: 标"已懂"抬 confidence 若前排会造回音壁, 与"戳盲区"相反。
  // confidence 仍在画像证据(profileEvidenceText)透明显示, 只是不暗中重排 feed。方向待认知测试验证后再定。
  return (reasonBoost[reason] || 30) + interestBoost + Math.min(seed.signal / 10, 10)
}

function profileEvidenceText(item: BoundarySeed) {
  if (!item.profile) return '暂无画像命中；按新信号与加速程度推荐。'
  const parts = [
    `${item.profile.domain_label}`,
    item.profile.depth ? `depth ${item.profile.depth}` : '',
    item.profile.interest ? `interest ${item.profile.interest}` : '',
    typeof item.profile.confidence === 'number' ? `confidence ${item.profile.confidence}%` : '',
  ].filter(Boolean)
  return `${parts.join(' · ')}。${item.profile.evidence || item.profile.note}`
}

function workflowText(item: BoundarySeed) {
  return item.workflow || workflowForStyle(item.profile?.recommended_seed_style)
}

function workflowForStyle(style: string | undefined) {
  const fallback = '先看来源可信度、关键数字口径、反例和下一步可验证证据。'
  const workflows: Record<string, string> = {
    mechanism: '先拆概念、参与方、成本结构、技术瓶颈和可验证指标。',
    comparison: '先列替代方案和受益方，再比较约束、成本、周期和反例。',
    financial_model: '用财报、现金流、成本和需求曲线追问，不只看标题里的增长叙事。',
    macro_model: '先拆利率、流动性、汇率和资产配置链条，再找数据口径验证。',
    evaluation: '先看维护者、许可证、提交活跃度、安全记录和商业使用边界。',
    risk_check: '先找锚定资产、责任主体、极端情景和监管边界。',
    paper_check: '先找论文和临床阶段，再分开看科学突破、监管审批和资本市场叙事。',
    multi_angle: '先列各方激励、约束和反例，避免单一叙事直接盖棺定论。',
    rhetoric_check: '先标出绝对化词语，再追问证据、时间口径、反例和利益相关方。',
  }
  return workflows[style || ''] || fallback
}

function styleLabel(style: string | undefined) {
  const labels: Record<string, string> = {
    mechanism: '适合机制补课',
    comparison: '适合做替代方案比较',
    financial_model: '适合套财务/需求模型',
    macro_model: '适合套宏观流动性模型',
    evaluation: '适合做项目评估',
    risk_check: '适合做风险核查',
    paper_check: '适合先查论文证据',
    multi_angle: '适合多方视角拆解',
    rhetoric_check: '适合识别话术压力',
  }
  return labels[style || ''] || '适合先做证据核查'
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
          {{ analyzing ? '分析中...' : '立即分析（LLM）' }}
        </button>
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
      <p v-if="cognitionMarkError" class="country-compare-error cognition-mark-error">{{ cognitionMarkError }}</p>

      <template v-if="!loading && !error && hasReport">
        <div v-if="report?.run_id" class="discovery-archive-bar">
          <p class="discovery-meta">
            报告时间：{{ fmtRunId(report.run_id) }}
            <span v-if="isHistoricalReport" class="discovery-report-kind">历史日报</span>
          </p>
          <label v-if="discoveryReports.length" class="discovery-archive-selector">
            <span>历史日报</span>
            <select
              aria-label="Discovery report archive"
              :value="selectedDiscoveryRunId || report.run_id"
              @change="selectReport"
            >
              <option v-for="item in discoveryReports" :key="item.run_id" :value="item.run_id">
                {{ fmtRunId(item.run_id) }} · {{ item.seed_count }}
              </option>
            </select>
          </label>
        </div>

        <section v-if="headlineItems.length" class="headline-frontpage" aria-label="今日头版">
          <div class="headline-head">
            <div>
              <p class="eyebrow">Front Page</p>
              <h3>今日头版</h3>
            </div>
            <span>{{ headlineItems.length }} 条</span>
          </div>
          <ol class="headline-deck">
            <li v-for="item in headlineItems" :key="`headline-${item.seed.url}`" class="headline-card">
              <div class="headline-card-main">
                <div class="headline-meta">
                  <span>{{ item.reason }}</span>
                  <em>{{ item.seed.domain_label || item.seed.domain }}</em>
                </div>
                <h4>{{ item.seed.title }}</h4>
                <div v-if="item.seed.info_value_labels?.length" class="value-lens-chips">
                  <span
                    v-for="label in item.seed.info_value_labels"
                    :key="`hl-${item.seed.url}-${label.code}`"
                    class="value-lens-chip"
                    :class="`vlc-${label.code}`"
                    :title="label.note"
                  >
                    {{ label.label }}
                  </span>
                </div>
                <p>{{ seedSummary(item.seed) }}</p>
                <small>{{ seedDeepReason(item) }}</small>
              </div>
              <div class="headline-actions">
                <a :href="item.seed.url" target="_blank" rel="noopener">原文</a>
                <button
                  type="button"
                  class="headline-primary"
                  :disabled="seedBusy"
                  @click="$emit('analyzeSeed', item.seed)"
                >
                  {{ seedBusy && activeSeedUrl === item.seed.url ? '…' : '深入' }}
                </button>
                <button
                  type="button"
                  class="headline-secondary"
                  @click="$emit('markSeedCognition', item.seed, 'known')"
                >
                  我懂了
                </button>
                <button
                  type="button"
                  class="headline-secondary"
                  @click="$emit('markSeedCognition', item.seed, 'doubtful')"
                >
                  存疑
                </button>
              </div>
            </li>
          </ol>

          <div v-if="trackedUpdates.length" class="frontpage-updates" aria-label="追踪动态">
            <p class="frontpage-updates-head">追踪动态 · 你关注的事最近有新报道</p>
            <ol class="frontpage-updates-deck">
              <li
                v-for="topic in trackedUpdates"
                :key="`update-${topic.id}`"
                class="frontpage-update-card"
              >
                <button type="button" class="frontpage-update-main" @click="$emit('trackTopic', topic.id)">
                  <span class="frontpage-update-flag">{{ freshness(topic.latest_published_at) }}</span>
                  <span class="frontpage-update-name">{{ topic.name }}</span>
                  <span class="frontpage-update-meta">{{ topic.article_count }} 篇 · {{ topic.source_count }} 源</span>
                </button>
                <!-- 双模式桥梁：手机低意图场景「先标记，回头深挖」，缓冲到电脑消化，不硬逼当场跳转 -->
                <button
                  type="button"
                  class="frontpage-update-dig"
                  @click="$emit('markTopicForDig', { id: topic.id, name: topic.name })"
                >回头深挖</button>
              </li>
            </ol>
          </div>
        </section>

        <div v-if="trackedTopics.length" class="tracking-block">
          <div class="tracking-head">
            <strong>正在追踪（{{ trackedTopics.length }}）</strong>
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

        <details class="cognition-timeline-tree">
          <summary class="seed-stream-head timeline-tree-summary">
            <strong>认知时间树</strong>
            <span>本地跨日报信号</span>
          </summary>
          <p class="timeline-tree-note">本地相似信号，不代表因果链。</p>
          <ol v-if="timelineBranches.length" class="timeline-tree-branches">
            <li v-for="branch in timelineBranches.slice(0, 5)" :key="branch.branch_key">
              <div class="timeline-branch-head">
                <strong>{{ branch.label }}</strong>
                <span>{{ branch.evidence_basis }}</span>
              </div>
              <ol class="timeline-tree-items">
                <li v-for="item in branch.items" :key="`${branch.branch_key}-${item.run_id}-${item.url}`">
                  <span class="timeline-run">{{ fmtRunId(item.run_id) }}</span>
                  <a :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a>
                  <small v-if="item.why">{{ item.why }}</small>
                  <button
                    type="button"
                    class="timeline-go"
                    :disabled="seedBusy"
                    @click="$emit('analyzeSeed', seedFromTimelineItem(item))"
                  >
                    深入
                  </button>
                </li>
              </ol>
            </li>
          </ol>
          <p v-else class="timeline-empty">至少需要两天日报才能生成认知时间树。</p>
        </details>

        <div v-if="seeds.length" class="seed-stream">
          <div class="boundary-queue">
            <div class="seed-stream-head">
              <strong>认知边界队列（{{ boundaryQueue.length }}）</strong>
              <span>系统按你的认知边界挑出来的，点「我懂了」即收进已认识</span>
            </div>
            <ol class="boundary-list">
              <li v-for="item in boundaryQueue" :key="`boundary-${item.seed.url}`">
                <div class="boundary-main">
                  <div class="boundary-title-row">
                    <span class="boundary-reason">{{ item.reason }}</span>
                    <strong>{{ item.seed.title }}</strong>
                    <em v-if="item.profile">{{ item.profile.domain_label }}</em>
                  </div>
                  <div v-if="item.seed.info_value_labels?.length" class="value-lens-chips">
                    <span
                      v-for="label in item.seed.info_value_labels"
                      :key="`bq-${item.seed.url}-${label.code}`"
                      class="value-lens-chip"
                      :class="`vlc-${label.code}`"
                      :title="label.note"
                    >
                      {{ label.label }}
                    </span>
                  </div>
                  <dl class="boundary-card-notes">
                    <div class="note-primary">
                      <dt>摘要</dt>
                      <dd>{{ seedSummary(item.seed) }}</dd>
                    </div>
                    <div class="note-primary">
                      <dt>为什么现在重要</dt>
                      <dd>{{ recommendationText(item) }}</dd>
                    </div>
                    <div class="note-secondary">
                      <dt>相关日报线索</dt>
                      <dd>{{ seedReportConnection(item.seed) }}</dd>
                    </div>
                    <div class="note-secondary">
                      <dt>深入理由</dt>
                      <dd>{{ seedDeepReason(item) }}</dd>
                    </div>
                    <div class="note-secondary">
                      <dt>建议路径</dt>
                      <dd>{{ nextActionText(item) }}</dd>
                    </div>
                    <div class="note-secondary">
                      <dt>画像依据</dt>
                      <dd>{{ profileEvidenceText(item) }}</dd>
                    </div>
                    <div class="note-secondary">
                      <dt>分析工作流</dt>
                      <dd>{{ workflowText(item) }}</dd>
                    </div>
                  </dl>
                </div>
                <div class="boundary-actions">
                  <button
                    type="button"
                    class="boundary-deep"
                    :disabled="seedBusy"
                    @click="$emit('analyzeSeed', item.seed)"
                  >
                    {{ seedBusy && activeSeedUrl === item.seed.url ? '…' : '深入' }}
                  </button>
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
            <p v-if="!boundaryQueue.length" class="seed-note">队列已清空，今天的认知边界都过了一遍</p>
          </div>

          <details v-if="restSeeds.length" class="rest-seeds">
            <summary class="seed-stream-head rest-seeds-summary">
              <strong>其余种子（{{ restSeeds.length }}）</strong>
              <span>展开浏览全量前沿；点「深入」送进事件分析台</span>
            </summary>
            <p v-if="seedNote" class="seed-note">{{ seedNote }}</p>
            <ol class="stream">
              <li
                v-for="seed in restSeeds"
                :key="seed.url"
                class="stream-row"
                :class="`tier-${seed.domain}`"
              >
                <div class="stream-main">
                  <a
                    class="stream-title"
                    :href="seed.url"
                    :title="seed.domain_label"
                    :aria-label="`${seed.title}，领域：${seed.domain_label}`"
                    target="_blank"
                    rel="noopener"
                  >{{ seed.title }}</a>
                  <p v-if="seed.what || seed.why" class="stream-note">
                    {{ seed.what }}<template v-if="seed.why"> — {{ seed.why }}</template>
                  </p>
                </div>
                <div class="stream-signals">
                  <span v-if="seed.is_new" class="sig sig-new">新</span>
                  <span v-else-if="seed.delta > 0" class="sig sig-up">↑{{ seed.delta }}</span>
                </div>
                <div class="seed-row-actions">
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
                  <button
                    type="button"
                    class="stream-go"
                    :disabled="seedBusy"
                    @click="$emit('analyzeSeed', seed)"
                  >
                    {{ seedBusy && activeSeedUrl === seed.url ? '…' : '深入' }}
                  </button>
                </div>
              </li>
            </ol>
          </details>
        </div>

        <div class="analysis markdown-body discovery-report" v-html="safeReportHtml" />
      </template>

      <p v-else-if="loaded" class="muted">
        还没有任何认知前沿日报。点上面的「立即分析」生成第一份（首次只建基线，明天起才有加速信号）。
      </p>
    </section>
  </section>
</template>

<style scoped>
.discovery-meta {
  margin: 0;
  font-size: 0.85rem;
  color: var(--muted, #6b7280);
}

.discovery-archive-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin: 0 0 0.75rem;
}

.discovery-report-kind {
  margin-left: 8px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid #cbd5db;
  background: #f8fbfc;
  color: #155a6e;
  font-size: 0.72rem;
  font-weight: 800;
}

.discovery-archive-selector {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #53636e;
  font-size: 0.78rem;
  font-weight: 700;
}

.discovery-archive-selector select {
  max-width: min(70vw, 260px);
  padding: 4px 8px;
  border: 1px solid #cbd5db;
  border-radius: 6px;
  background: #fff;
  color: #2c3a44;
  font: inherit;
}

.headline-frontpage {
  margin: 0 0 14px;
}

.headline-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.headline-head .eyebrow,
.headline-head h3 {
  margin: 0;
}

.headline-head h3 {
  color: #1c2329;
  font-size: 1.08rem;
  line-height: 1.2;
}

.headline-head span {
  color: #6b7280;
  font-size: 0.78rem;
  font-weight: 800;
}

.headline-deck {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.headline-card {
  display: grid;
  grid-template-rows: 1fr auto;
  gap: 10px;
  min-width: 0;
  min-height: 220px;
  padding: 12px;
  border: 1px solid #cfdbe0;
  border-left: 4px solid #155a6e;
  border-radius: 8px;
  background: #fff;
}

.headline-card-main {
  min-width: 0;
}

.headline-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.headline-meta span,
.headline-meta em {
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-style: normal;
  font-weight: 800;
}

.headline-meta span {
  background: #fff4e0;
  color: #8a5a00;
}

.headline-meta em {
  background: #eef7f9;
  color: #155a6e;
}

.headline-card h4 {
  margin: 0 0 8px;
  color: #1c2329;
  font-size: 0.98rem;
  line-height: 1.28;
}

.headline-card p,
.headline-card small {
  display: block;
  margin: 0;
  color: #53636e;
  line-height: 1.42;
}

.headline-card p {
  font-size: 0.84rem;
}

.headline-card small {
  margin-top: 6px;
  font-size: 0.76rem;
}

.headline-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.headline-actions a,
.headline-actions button {
  min-height: 28px;
  padding: 4px 10px;
  border: 1px solid #c5d2d8;
  border-radius: 6px;
  background: #fff;
  color: #2c3a44;
  font: inherit;
  font-size: 0.76rem;
  font-weight: 800;
  line-height: 1.2;
  text-decoration: none;
  cursor: pointer;
}

.headline-primary {
  border-color: #8fb8c8 !important;
  background: #eef7f9 !important;
  color: #155a6e !important;
}

.headline-actions button:disabled {
  opacity: 0.5;
  cursor: default;
}

/* 行为金融学信息价值透镜 chip: 阅读提示, 非警告。克制的中性色, 不用红色告警。 */
.value-lens-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin: 0 0 var(--space-2);
  padding: 0;
  list-style: none;
}

.value-lens-chip {
  padding: 1px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-round);
  background: var(--surface-tint);
  color: var(--text-muted);
  font-size: 0.68rem;
  font-weight: 700;
  cursor: default;
}

/* 分类微差异色(仍克制): 造势/羊群偏暖提示, 小样本偏中性 */
.value-lens-chip.vlc-suspected_hype,
.value-lens-chip.vlc-availability_high {
  border-color: #e6d3a8;
  background: #fbf5e6;
  color: #7a5a12;
}

.value-lens-chip.vlc-availability_rising_seed {
  border-color: #b9cfdd;
  background: #eef4f9;
  color: #2f5f7e;
}

.value-lens-chip.vlc-suspected_herding {
  border-color: #cdd9c6;
  background: #f2f7ef;
  color: #4a6540;
}

/* 今日头版「追踪动态」: 关注的事最近有新报道, 打开即见动静 */
.frontpage-updates {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px dashed var(--border);
}

.frontpage-updates-head {
  margin: 0 0 var(--space-3);
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.frontpage-updates-deck {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.frontpage-update-card {
  min-width: 0;
}

.frontpage-update-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--border-soft);
  border-left: 4px solid var(--brand-accent);
  border-radius: var(--radius-3);
  background: var(--surface);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s, border-color 0.12s;
}

.frontpage-update-main:hover {
  background: var(--surface-tint);
  border-color: var(--brand-accent);
}

.frontpage-update-flag {
  align-self: flex-start;
  padding: 1px 8px;
  border-radius: var(--radius-round);
  background: #eef7f9;
  color: var(--brand);
  font-size: 0.68rem;
  font-weight: 800;
}

.frontpage-update-name {
  color: var(--text);
  font-size: 0.92rem;
  font-weight: 600;
  line-height: 1.35;
}

.frontpage-update-meta {
  color: var(--text-faint);
  font-size: 0.74rem;
}

/* 双模式桥梁: 头版「回头深挖」标记按钮, 克制副操作样式(不与主跳转抢视觉) */
.frontpage-update-dig {
  margin-top: var(--space-1);
  padding: 3px 10px;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-round);
  background: transparent;
  color: var(--text-faint);
  font: inherit;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
}

.frontpage-update-dig:hover {
  border-color: var(--brand-accent);
  color: var(--brand);
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

.cognition-timeline-tree {
  margin: 0 0 12px;
  padding: 10px 12px;
  border: 1px solid #d7e0e4;
  border-radius: 10px;
  background: #fbfcfd;
}

.timeline-tree-summary {
  margin-bottom: 0;
  cursor: pointer;
}

.cognition-timeline-tree[open] .timeline-tree-summary {
  margin-bottom: 8px;
}

.timeline-tree-note,
.timeline-empty {
  margin: 0 0 8px;
  color: #6b7280;
  font-size: 0.78rem;
}

.timeline-tree-branches,
.timeline-tree-items {
  list-style: none;
  margin: 0;
  padding: 0;
}

.timeline-tree-branches {
  display: grid;
  gap: 8px;
}

.timeline-tree-branches > li {
  padding: 8px 10px;
  border: 1px solid #e2eaed;
  border-radius: 8px;
  background: #fff;
}

.timeline-branch-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.timeline-branch-head strong {
  color: #155a6e;
}

.timeline-branch-head span {
  color: #6b7280;
  font-size: 0.76rem;
}

.timeline-tree-items {
  display: grid;
  gap: 5px;
}

.timeline-tree-items li {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  color: #53636e;
  font-size: 0.78rem;
}

.timeline-tree-items a {
  flex: 1 1 240px;
  min-width: 0;
  color: #1c2329;
  font-weight: 700;
  text-decoration: none;
}

.timeline-tree-items a:hover {
  text-decoration: underline;
}

.timeline-tree-items small {
  color: #71808a;
}

.timeline-run {
  flex-shrink: 0;
  color: #8a97a0;
  font-size: 0.72rem;
}

.timeline-go {
  flex-shrink: 0;
  padding: 3px 10px;
  border: 1px solid #8fb8c8;
  border-radius: 999px;
  background: #eef7f9;
  color: #155a6e;
  font-size: 0.74rem;
  font-weight: 800;
  cursor: pointer;
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
  gap: 10px;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  color: #53636e;
  font-size: 0.78rem;
}

.boundary-main {
  display: grid;
  gap: 8px;
  flex: 1 1 360px;
  min-width: 0;
}

.boundary-title-row {
  display: flex;
  gap: 8px;
  align-items: center;
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

.boundary-deep,
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

.boundary-deep {
  border-color: #8fb8c8;
  background: #eef7f9;
  color: #155a6e;
}

.boundary-deep:hover:not(:disabled) {
  background: #dff0f5;
  border-color: #155a6e;
}

.boundary-deep:disabled {
  opacity: 0.5;
  cursor: default;
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

.boundary-card-notes {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2) var(--space-4);
  margin: 0;
}

.boundary-card-notes div {
  min-width: 0;
}

/* 主信息：摘要 + 为什么现在重要 —— 全宽、可读、有呼吸 */
.boundary-card-notes .note-primary {
  grid-column: 1 / -1;
}

.boundary-card-notes .note-primary dt {
  margin: 0 0 var(--space-1);
  color: var(--brand);
  font-size: var(--font-size-0);
  font-weight: 800;
  letter-spacing: 0.02em;
}

.boundary-card-notes .note-primary dd {
  margin: 0;
  color: var(--text-heading);
  font-size: 0.9rem;
  line-height: 1.5;
}

/* 次要元信息：紧凑、弱化，两列铺开 */
.boundary-card-notes .note-secondary dt {
  margin: 0 0 2px;
  color: var(--text-faint);
  font-size: 0.68rem;
  font-weight: 700;
}

.boundary-card-notes .note-secondary dd {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.75rem;
  line-height: 1.4;
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
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 14px;
  border-top: 1px solid #eef2f4;
  border-left: 4px solid #cbd5db;
  background: var(--surface);
  transition: background 0.12s;
}

.stream-row:first-child {
  border-top: none;
}

.stream-row:hover {
  background: #f8fbfc;
}

/* 领域色轨(行左边框)：科技/财经/地缘一眼区分, 悬停标题有 domain_label 提示 */
.stream-row.tier-tech { border-left-color: #2f80ed; }
.stream-row.tier-finance { border-left-color: #27ae60; }
.stream-row.tier-geopolitics { border-left-color: #c0392b; }
.stream-row.tier-science { border-left-color: #8e44ad; }

.stream-main {
  flex: 1;
  min-width: 0;
}

.stream-title {
  display: block;
  color: var(--text);
  font-weight: 600;
  font-size: 0.9rem;
  line-height: 1.4;
  text-decoration: none;
}

.stream-title:hover {
  text-decoration: underline;
}

.stream-note {
  margin: 3px 0 0;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--text-faint);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.stream-row:hover .stream-note {
  -webkit-line-clamp: unset;
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

/* 行尾动作组: 我懂了/存疑/深入 收在一起, 收紧但保持可见(触屏桌面一致, 不用 hover-only) */
.seed-row-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 5px;
}

/* 其余种子: 默认折叠的浏览区, 与顶部边界队列(要动作)分层 */
.rest-seeds {
  margin-top: 12px;
  border-top: 1px solid #eef2f4;
  padding-top: 10px;
}

.rest-seeds-summary {
  cursor: pointer;
  list-style: none;
}

.rest-seeds-summary::-webkit-details-marker {
  display: none;
}

.rest-seeds-summary::before {
  content: '▸ ';
  color: #8a97a0;
}

.rest-seeds[open] .rest-seeds-summary::before {
  content: '▾ ';
}

@media (max-width: 720px) {
  .headline-deck {
    grid-template-columns: 1fr;
  }

  .headline-card {
    min-height: auto;
  }

  .headline-actions a,
  .headline-actions button {
    flex: 1 1 auto;
    text-align: center;
  }

  .boundary-card-notes {
    grid-template-columns: 1fr;
  }

  .boundary-actions {
    width: 100%;
  }
}
</style>
