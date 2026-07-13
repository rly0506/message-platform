import { computed, ref, watch } from 'vue'
import { deleteDigQueueItem, fetchDigQueue, saveDigQueueItem } from '../api/dossierApi'
import type { DigQueueRecord } from '../types/dossier'

// 深挖队列（双模式桥梁 V1a）：手机/低意图场景「标记好奇心」，电脑/高意图场景「消化好奇心」。
// localStorage 是离线缓存；专用 DigQueueItem API 负责跨设备同步，与 CognitionProfile 严格隔离。
// 标记入口 = 头版卡 + 事件详情；消化入口 = 分析台顶部卡带。
export type DigQueueItem = {
  // 稳定去重键：topic 级 = `t:{topicId}`；event 级 = `t:{topicId}:e:{eventId}`。
  id: string
  topicId: number
  topicName: string
  // 后端稳定 Event.id（仅后端事件图节点有）；本地兜底事件无 id 时为 null，只做话题级标记。
  eventId: number | null
  eventTitle: string
  // 打开哪个透镜（contrast/analogue…）。默认对照，消化时据此定位。
  view: 'contrast' | 'analogue'
  // ISO 时间戳（标记时刻）。用 new Date().toISOString()，仅在用户动作里取，不进渲染纯函数。
  addedAt: string
}

const STORAGE_KEY = 'message-platform:dig-queue:v1'
const SYNC_STORAGE_KEY = 'message-platform:dig-queue-sync:v1'

type PendingMutation =
  | { kind: 'upsert'; item: DigQueueItem; version: number }
  | { kind: 'delete'; id: string; version: number }

type PendingMutationInput =
  | { kind: 'upsert'; item: DigQueueItem }
  | { kind: 'delete'; id: string }

type DigQueueSyncState = {
  initialized: true
  nextVersion: number
  pending: Record<string, PendingMutation>
}

function isDigQueueItem(item: unknown): item is DigQueueItem {
  if (!item || typeof item !== 'object') return false
  const value = item as Partial<DigQueueItem>
  return (
    typeof value.id === 'string' &&
    typeof value.topicId === 'number' &&
    typeof value.topicName === 'string' &&
    (value.eventId === null || typeof value.eventId === 'number') &&
    typeof value.eventTitle === 'string' &&
    (value.view === 'contrast' || value.view === 'analogue') &&
    typeof value.addedAt === 'string'
  )
}

function loadFromStorage(): DigQueueItem[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    // 诚实过滤：只保留结构完整的条目，坏数据静默丢弃不崩。
    return parsed.filter(isDigQueueItem)
  } catch {
    return []
  }
}

function loadSyncState(localItems: DigQueueItem[]): DigQueueSyncState {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(SYNC_STORAGE_KEY) || 'null')
    if (parsed?.initialized === true && typeof parsed.nextVersion === 'number' && parsed.pending) {
      const pending: Record<string, PendingMutation> = {}
      for (const [id, mutation] of Object.entries(parsed.pending as Record<string, PendingMutation>)) {
        if (
          mutation?.kind === 'delete' &&
          mutation.id === id &&
          typeof mutation.version === 'number'
        ) {
          pending[id] = mutation
        } else if (
          mutation?.kind === 'upsert' &&
          isDigQueueItem(mutation.item) &&
          mutation.item.id === id &&
          typeof mutation.version === 'number'
        ) {
          pending[id] = mutation
        }
      }
      return { initialized: true, nextVersion: parsed.nextVersion, pending }
    }
  } catch {
    // Corrupt sync metadata is rebuilt from the still-valid local queue below.
  }

  const pending: Record<string, PendingMutation> = {}
  let nextVersion = 0
  for (const item of localItems) {
    nextVersion += 1
    pending[item.id] = { kind: 'upsert', item, version: nextVersion }
  }
  return { initialized: true, nextVersion, pending }
}

function remoteToLocal(item: DigQueueRecord): DigQueueItem {
  return {
    id: item.item_key,
    topicId: item.topic_id,
    topicName: item.topic_name,
    eventId: item.event_id,
    eventTitle: item.event_title,
    view: item.view,
    addedAt: item.added_at,
  }
}

// 模块级单例：全 app 共享同一份响应队列（标记处与消化处看到的是同一个列表）。
const items = ref<DigQueueItem[]>(loadFromStorage())
const syncState = loadSyncState(items.value)
const digQueueSyncing = ref(false)
const digQueueSyncError = ref('')
let syncPromise: Promise<void> | null = null

function persistSyncState(): void {
  try {
    window.localStorage.setItem(SYNC_STORAGE_KEY, JSON.stringify(syncState))
  } catch {
    // The in-memory outbox still protects the current session.
  }
}

persistSyncState()

watch(
  items,
  (value) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
    } catch {
      // localStorage 不可用（隐私模式/配额）时静默降级：队列仍在内存里可用，只是不持久化。
    }
  },
  { deep: true },
)

export function digItemKey(topicId: number, eventId: number | null): string {
  return eventId == null ? `t:${topicId}` : `t:${topicId}:e:${eventId}`
}

function queueMutation(id: string, mutation: PendingMutationInput): void {
  syncState.nextVersion += 1
  syncState.pending[id] = mutation.kind === 'upsert'
    ? { kind: 'upsert', item: mutation.item, version: syncState.nextVersion }
    : { kind: 'delete', id: mutation.id, version: syncState.nextVersion }
  persistSyncState()
}

async function flushPendingMutations(): Promise<void> {
  while (true) {
    const next = Object.entries(syncState.pending)[0]
    if (!next) return
    const [id, mutation] = next
    if (mutation.kind === 'upsert') {
      const item = mutation.item
      await saveDigQueueItem({
        topic_id: item.topicId,
        topic_name: item.topicName,
        event_id: item.eventId,
        event_title: item.eventTitle,
        view: item.view,
        added_at: item.addedAt,
      })
    } else {
      await deleteDigQueueItem(id)
    }
    if (syncState.pending[id]?.version === mutation.version) {
      delete syncState.pending[id]
      persistSyncState()
    }
  }
}

async function runSync(): Promise<void> {
  digQueueSyncing.value = true
  digQueueSyncError.value = ''
  try {
    while (true) {
      await flushPendingMutations()
      const remoteItems = await fetchDigQueue()
      if (Object.keys(syncState.pending).length) continue
      items.value = remoteItems.map(remoteToLocal)
      return
    }
  } catch {
    digQueueSyncError.value = '跨设备同步暂不可用，本机队列已保留；下次操作或刷新时重试。'
  } finally {
    digQueueSyncing.value = false
    syncPromise = null
  }
}

function syncDigQueue(): Promise<void> {
  if (!syncPromise) syncPromise = runSync()
  return syncPromise
}

export function useDigQueue() {
  const digItems = computed(() => items.value)
  const digCount = computed(() => items.value.length)

  // 加入队列：按 id 去重。已存在则把它提到最前（重新表达好奇心 = 顶上来），不重复堆积。
  function addToDigQueue(item: Omit<DigQueueItem, 'addedAt'> & { addedAt?: string }): void {
    const addedAt = item.addedAt ?? new Date().toISOString()
    const next = items.value.filter((existing) => existing.id !== item.id)
    const queued = { ...item, addedAt }
    next.unshift(queued)
    items.value = next
    queueMutation(queued.id, { kind: 'upsert', item: queued })
    void syncDigQueue()
  }

  function removeFromDigQueue(id: string): void {
    items.value = items.value.filter((item) => item.id !== id)
    queueMutation(id, { kind: 'delete', id })
    void syncDigQueue()
  }

  return {
    digItems,
    digCount,
    digQueueSyncing,
    digQueueSyncError,
    addToDigQueue,
    removeFromDigQueue,
    syncDigQueue,
  }
}
