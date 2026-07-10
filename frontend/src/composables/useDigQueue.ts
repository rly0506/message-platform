import { computed, ref, watch } from 'vue'

// 深挖队列（双模式桥梁 V1a）：手机/低意图场景「标记好奇心」，电脑/高意图场景「消化好奇心」。
// 纯前端 localStorage，零后端依赖；V1b 再由后端 CognitionMark(dig_later) 跨设备同步。
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
  view: string
  // ISO 时间戳（标记时刻）。用 new Date().toISOString()，仅在用户动作里取，不进渲染纯函数。
  addedAt: string
}

const STORAGE_KEY = 'message-platform:dig-queue:v1'

function loadFromStorage(): DigQueueItem[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    // 诚实过滤：只保留结构完整的条目，坏数据静默丢弃不崩。
    return parsed.filter(
      (item): item is DigQueueItem =>
        item &&
        typeof item.id === 'string' &&
        typeof item.topicId === 'number' &&
        typeof item.topicName === 'string',
    )
  } catch {
    return []
  }
}

// 模块级单例：全 app 共享同一份响应队列（标记处与消化处看到的是同一个列表）。
const items = ref<DigQueueItem[]>(loadFromStorage())

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

export function useDigQueue() {
  const digItems = computed(() => items.value)
  const digCount = computed(() => items.value.length)

  // 加入队列：按 id 去重。已存在则把它提到最前（重新表达好奇心 = 顶上来），不重复堆积。
  function addToDigQueue(item: Omit<DigQueueItem, 'addedAt'> & { addedAt?: string }): void {
    const addedAt = item.addedAt ?? new Date().toISOString()
    const next = items.value.filter((existing) => existing.id !== item.id)
    next.unshift({ ...item, addedAt })
    items.value = next
  }

  function removeFromDigQueue(id: string): void {
    items.value = items.value.filter((item) => item.id !== id)
  }

  return {
    digItems,
    digCount,
    addToDigQueue,
    removeFromDigQueue,
  }
}
