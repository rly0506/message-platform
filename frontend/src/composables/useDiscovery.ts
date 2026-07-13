import { computed, ref } from 'vue'
import {
  createDiscoveryJob,
  distillSeed,
  fetchDiscoveryReport,
  fetchDiscoveryReports,
  fetchDiscoveryTimelineTree,
  fetchLatestBriefing,
  fetchLatestDiscovery,
  isNetworkError,
} from '../api/dossierApi'
import type { DailyBriefing, DiscoveryReport, DiscoveryReportMeta, DiscoveryResult, DiscoverySeed, DiscoveryTimelineTree, SearchJob } from '../types/dossier'
import { renderMarkdown } from '../utils/markdown'
import { stepStatusText, waitForJob, type StepState } from './jobPolling'
import { readableError } from './useTopicData'

export function useDiscovery() {
  const report = ref<DiscoveryReport | null>(null)
  const loading = ref(false)
  const analyzing = ref(false)
  const loaded = ref(false)
  const error = ref('')
  const message = ref('')
  const activeJobId = ref('')
  const steps = ref<StepState[]>([])
  const reports = ref<DiscoveryReportMeta[]>([])
  const selectedRunId = ref('')
  const timelineTree = ref<DiscoveryTimelineTree>({ branches: [] })
  const briefing = ref<DailyBriefing | null>(null)
  const briefingLoading = ref(false)
  const briefingError = ref('')

  const safeReportHtml = computed(() => renderMarkdown(report.value?.markdown))
  const hasReport = computed(() => Boolean(report.value?.markdown?.trim()))
  const seeds = computed<DiscoverySeed[]>(() => report.value?.seeds || [])

  async function loadLatest() {
    // 事实早报是独立增强；失败或慢响应不能门控发现日报、队列或 deep-link。
    void loadBriefing()
    loading.value = true
    error.value = ''
    try {
      report.value = await fetchLatestDiscovery()
      selectedRunId.value = report.value.run_id
    } catch (err) {
      // 404 = 还没有任何报告，是正常初始态，不当错误。网络错误才提示。
      if (isNetworkError(err)) {
        error.value = readableError(err)
      } else {
        report.value = null
      }
    } finally {
      await Promise.all([loadReports(), loadTimelineTree()])
      loading.value = false
      loaded.value = true
    }
  }

  async function loadBriefing() {
    if (briefingLoading.value) return
    briefingLoading.value = true
    briefingError.value = ''
    try {
      briefing.value = await fetchLatestBriefing()
    } catch (err) {
      briefing.value = null
      briefingError.value = readableError(err)
    } finally {
      briefingLoading.value = false
    }
  }

  async function loadReports() {
    try {
      reports.value = await fetchDiscoveryReports()
    } catch {
      reports.value = []
    }
  }

  async function loadReport(runId: string) {
    if (!runId || runId === selectedRunId.value) return
    loading.value = true
    error.value = ''
    try {
      report.value = await fetchDiscoveryReport(runId)
      selectedRunId.value = report.value.run_id
    } catch (err) {
      error.value = readableError(err)
    } finally {
      loading.value = false
      loaded.value = true
    }
  }

  async function loadTimelineTree() {
    try {
      timelineTree.value = await fetchDiscoveryTimelineTree()
    } catch {
      timelineTree.value = { branches: [] }
    }
  }

  async function runDiscovery(annotate = true) {
    if (analyzing.value) return
    analyzing.value = true
    error.value = ''
    message.value = '正在提交发现任务...'
    // 步骤文案由后端 job.steps 提供（单一事实源），前端不再维护一份重复的标签。
    steps.value = []
    try {
      const job = await createDiscoveryJob(annotate)
      activeJobId.value = job.id
      steps.value = job.steps || []
      message.value = `发现任务已提交：${job.id.slice(0, 8)}`
      const resultJob = await waitForJob(job.id, steps, message, 1800, '发现任务')
      await finishDiscoveryJob(resultJob)
    } catch (err) {
      error.value = readableError(err)
      steps.value = steps.value.map((step) =>
        step.status === 'running' ? { ...step, status: 'failed' } : step,
      )
    } finally {
      analyzing.value = false
      activeJobId.value = ''
    }
  }

  async function finishDiscoveryJob(job: SearchJob) {
    if (job.status !== 'done') {
      throw new Error(job.error || `发现任务${stepStatusText(job.status)}`)
    }
    steps.value = job.steps || []
    if (isDiscoveryResult(job.result)) {
      report.value = {
        markdown: job.result.markdown,
        run_id: job.result.run_id,
        path: job.result.path,
        seeds: job.result.seeds || [],
      }
      selectedRunId.value = job.result.run_id
      await Promise.all([loadReports(), loadTimelineTree()])
      void loadBriefing()
      message.value = `认知前沿日报已生成：${job.result.run_id}`
    } else {
      // 结果形状意外时回退到读最新文件，保证显示不空。
      await loadLatest()
      message.value = '发现任务完成。'
    }
  }

  /**
   * 把一条种子的长标题提炼成简短话题词（供事件分析台搜索）。
   * 返回 { query, llm }；llm=false 表示后端降级到启发式（无 LLM 时）。
   * 协调逻辑（切模式、填搜索框、触发搜索）由 App.vue 负责，这里只管拿话题词。
   */
  async function distill(seed: DiscoverySeed) {
    return distillSeed(seed.title, seed.domain)
  }

  return {
    report,
    loading,
    analyzing,
    loaded,
    error,
    message,
    activeJobId,
    steps,
    reports,
    selectedRunId,
    timelineTree,
    briefing,
    briefingLoading,
    briefingError,
    seeds,
    safeReportHtml,
    hasReport,
    loadLatest,
    loadReports,
    loadReport,
    loadTimelineTree,
    loadBriefing,
    runDiscovery,
    distill,
    stepStatusText,
  }
}

function isDiscoveryResult(result: SearchJob['result']): result is DiscoveryResult {
  return Boolean(result && 'kind' in result && (result as DiscoveryResult).kind === 'discovery')
}
