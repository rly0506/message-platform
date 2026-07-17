import type { Ref } from 'vue'
import { fetchSearchJob } from '../api/dossierApi'
import type { SearchJob } from '../types/dossier'

export type StepState = { key: string; label: string; status: string }

/** job 步骤状态 -> 中文展示文案。全站 job (搜索/深度/学界/民间/三方/发现) 共用。 */
export const stepStatusLabels: Record<string, string> = {
  pending: '等待中',
  running: '进行中',
  done: '已完成',
  warning: '已完成，有提示',
  empty: '没有新数据',
  skipped: '已跳过',
  failed: '失败',
  interrupted: '已中断',
}

export function stepStatusText(status: string) {
  return stepStatusLabels[status] || status
}

export function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

/**
 * 轮询一个后台 job 直到终态。所有 job 类型共用同一套 polling，
 * 调用方只需传入自己的 steps/message refs、轮询间隔与文案标签。
 *
 * `isCurrent` 是可选的 generation/取消守卫：切题或 reset 后它返回 false，
 * 此时 polling 立即停止写共享 steps/message 并抛 JobSupersededError，
 * 让在途 job 的 finish/写入路径彻底短路——迟到响应不再污染新专题面板。
 */
export class JobSupersededError extends Error {
  constructor() {
    super('job superseded by a newer topic generation')
    this.name = 'JobSupersededError'
  }
}

export function isJobSuperseded(err: unknown): err is JobSupersededError {
  return err instanceof JobSupersededError
}

export async function waitForJob(
  jobId: string,
  steps: Ref<StepState[]>,
  message: Ref<string>,
  intervalMs: number,
  label: string,
  isCurrent?: () => boolean,
): Promise<SearchJob> {
  const terminal = new Set(['done', 'empty', 'failed', 'interrupted'])
  for (;;) {
    // poll 前先校验 generation：已被切题/reset 作废则停轮询、停写入。
    if (isCurrent && !isCurrent()) throw new JobSupersededError()
    const job = await fetchSearchJob(jobId)
    // 迟到响应：本轮网络往返期间被作废，则不写共享 steps/message。
    if (isCurrent && !isCurrent()) throw new JobSupersededError()
    steps.value = job.steps || steps.value
    if (job.status === 'running' || job.status === 'queued') {
      message.value = `${label} ${jobId.slice(0, 8)} 正在${job.status === 'queued' ? '排队' : '执行'}...`
    }
    if (terminal.has(job.status)) {
      return job
    }
    await delay(intervalMs)
  }
}
