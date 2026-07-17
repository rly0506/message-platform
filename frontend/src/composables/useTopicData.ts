import { computed, ref } from 'vue'
import {
  createProject,
  createTopic,
  deleteProject,
  deleteTopic,
  errorMessage,
  fetchArticles,
  fetchEventGraph,
  fetchLocalEvents,
  fetchProjects,
  fetchTopic,
  fetchTopics,
  isNetworkError,
  updateProject,
  updateTopic,
} from '../api/dossierApi'
import type { Article, EventGraphPayload, LocalEventsPayload, ProjectSummary, TopicDetail, TopicSummary } from '../types/dossier'

const pageSize = 80

export function useTopicData() {
  const projects = ref<ProjectSummary[]>([])
  const topics = ref<TopicSummary[]>([])
  const selectedTopicId = ref<number | null>(null)
  const detail = ref<TopicDetail | null>(null)
  const localData = ref<LocalEventsPayload | null>(null)
  const eventGraph = ref<EventGraphPayload | null>(null)
  const articles = ref<Article[]>([])
  const totalArticles = ref(0)
  const loading = ref(true)
  const articleLoading = ref(false)
  const localLoading = ref(false)
  const eventGraphLoading = ref(false)
  const error = ref('')

  const selectedTopic = computed(() =>
    topics.value.find((topic) => topic.id === selectedTopicId.value)
    // detail 回退必须仍属当前选题：删除选中专题后 loadTopics 已把选题重置为 null，
    // 而 detail 仍是被删专题（removeTopic 的清 detail 分支因选题已变而跳过）——
    // 无 id 门控时已删面板会在空选题状态「复活」（P0-T4 null 腿 RED 证据）。
    || (detail.value && detail.value.id === selectedTopicId.value ? detail.value : null),
  )

  // 话题级异步加载的 request-token：切话题时旧请求的迟到响应必须丢弃，绝不写进新话题
  // （证据归属红线，与对照/类比/覆盖/国家对照同构）。每个 loader 一个单调计数器，
  // await 后同时校验「本次仍是最新请求」且「选中话题未变」，两者任一不满足即丢弃。
  let topicDetailRequestId = 0
  let articlesRequestId = 0
  let localEventsRequestId = 0
  let eventGraphRequestId = 0
  // loadTopics 也需单调 token：一个迟到的 loadTopics(A)（如 finishSearchJob 的续体）
  // 绝不能在用户已切到 B 后把 selectedTopicId 改回 A（选题归属红线）。
  let topicsRequestId = 0

  // 手动切题（watch(selectedTopicId)）时调用：作废所有在途话题级加载，
  // 让一个迟到的 loadTopics(A)/loadArticles(A) 续体既不改选题也不写数据到 B。
  // 这补上 topicsRequestId 此前只在 loadTopics 内自增、不随手动切题失效的缺口。
  function invalidateTopicLoads() {
    topicsRequestId += 1
    topicDetailRequestId += 1
    articlesRequestId += 1
    localEventsRequestId += 1
    eventGraphRequestId += 1
    // 作废在途 loadTopics 后，其 finally 因 token mismatch 不会再清 loading；
    // 手动切题的 watcher 又不发新 loadTopics，list loading 可能永久为 true。
    // 作废入口必须同步终止该 loading ownership（审计 finding #2）。
    loading.value = false
    articleLoading.value = false
    localLoading.value = false
    eventGraphLoading.value = false
  }

  async function loadTopics(preferTopicId?: number) {
    const requestId = ++topicsRequestId
    loading.value = true
    error.value = ''
    try {
      const data = await fetchTopics()
      let nextProjects: ProjectSummary[] = []
      try {
        nextProjects = await fetchProjects()
      } catch {
        nextProjects = []
      }
      // 迟到响应：已有更新的 loadTopics 发起或已手动切题作废，则既不写列表/projects、也不改选题。
      // projects 必须在 token 校验之后写（此前先写会让迟到响应污染新专题的项目列表）。
      if (requestId !== topicsRequestId) return
      projects.value = nextProjects
      topics.value = data
      const preferred = preferTopicId || selectedTopicId.value
      // 初次加载(无 preferred)不自动选最新创建的专题，进空状态由用户挑/搜；
      // 有 preferred 且仍存在则保持(新建/刷新后不跳走)。
      selectedTopicId.value = data.some((topic) => topic.id === preferred) ? preferred || null : null
    } catch (err) {
      if (requestId !== topicsRequestId) return
      error.value = readableError(err)
    } finally {
      if (requestId === topicsRequestId) loading.value = false
    }
  }

  async function loadTopic(id: number) {
    const requestId = ++topicDetailRequestId
    const data = await fetchTopic(id)
    // 迟到响应：已切到别的话题或有更新请求，丢弃不写。
    if (requestId !== topicDetailRequestId || selectedTopicId.value !== id) return
    detail.value = data
  }

  async function loadArticles(id: number) {
    const requestId = ++articlesRequestId
    articleLoading.value = true
    try {
      const data = await fetchArticles(id, pageSize)
      if (requestId !== articlesRequestId || selectedTopicId.value !== id) return
      articles.value = data.items
      totalArticles.value = data.total
    } finally {
      if (requestId === articlesRequestId) articleLoading.value = false
    }
  }

  async function loadLocalEvents(id: number) {
    const requestId = ++localEventsRequestId
    localLoading.value = true
    try {
      const data = await fetchLocalEvents(id)
      if (requestId !== localEventsRequestId || selectedTopicId.value !== id) return
      localData.value = data
    } finally {
      if (requestId === localEventsRequestId) localLoading.value = false
    }
  }

  async function loadEventGraph(id: number) {
    const requestId = ++eventGraphRequestId
    eventGraphLoading.value = true
    try {
      const data = await fetchEventGraph(id)
      if (requestId !== eventGraphRequestId || selectedTopicId.value !== id) return
      eventGraph.value = data
    } catch {
      // 事件图是增量增强，后端失败/未分析时静默回退到前端现算，绝不因此让页面崩。
      // 迟到失败同样按 token 隔离，不清掉新话题已加载的图。
      if (requestId !== eventGraphRequestId || selectedTopicId.value !== id) return
      eventGraph.value = null
    } finally {
      if (requestId === eventGraphRequestId) eventGraphLoading.value = false
    }
  }

  async function createTopicInProject(payload: {
    project_id?: number | null
    name: string
    description?: string
    queries?: string[]
  }) {
    const topic = await createTopic(payload)
    // 新建必然切到新 id：loadTopics 改 selectedTopicId → 触发 App.vue watch 整包加载
    // （含 loadTopic）。不再显式 loadTopic，避免新专题双 owner 重复请求。
    await loadTopics(topic.id)
    if (selectedTopicId.value !== topic.id) await loadTopic(topic.id)
    return topic
  }

  async function saveProject(payload: { id?: number; name: string; description?: string }) {
    const project = payload.id
      ? await updateProject(payload.id, { name: payload.name, description: payload.description || '' })
      : await createProject({ name: payload.name, description: payload.description || '' })
    await loadTopics(selectedTopicId.value || undefined)
    return project
  }

  async function archiveProject(id: number) {
    const project = await updateProject(id, { status: 'archived' })
    await loadTopics(selectedTopicId.value || undefined)
    return project
  }

  async function removeProject(id: number) {
    const result = await deleteProject(id)
    await loadTopics(selectedTopicId.value || undefined)
    return result
  }

  async function saveTopic(payload: {
    id?: number
    project_id?: number | null
    name: string
    description?: string
    queries?: string[]
  }) {
    const topic = payload.id
      ? await updateTopic(payload.id, {
          project_id: payload.project_id,
          name: payload.name,
          description: payload.description || '',
          queries: payload.queries || [],
        })
      : await createTopic(payload)
    // 单一所有者：切到新专题时 watch(selectedTopicId) 会整包加载；仅同题保存（watch 不触发）才显式补 detail。
    const isNavigation = topic.id !== selectedTopicId.value
    await loadTopics(topic.id)
    if (!isNavigation) await loadTopic(topic.id)
    return topic
  }

  async function archiveTopic(id: number) {
    const topic = await updateTopic(id, { status: 'archived' })
    await loadTopics(selectedTopicId.value || undefined)
    if (selectedTopicId.value === id) {
      detail.value = { ...detail.value, ...topic } as TopicDetail
    }
    return topic
  }

  async function removeTopic(id: number) {
    const result = await deleteTopic(id)
    const fallbackId = selectedTopicId.value === id ? undefined : selectedTopicId.value || undefined
    await loadTopics(fallbackId)
    if (selectedTopicId.value === id) {
      selectedTopicId.value = topics.value[0]?.id || null
      detail.value = null
    }
    return result
  }

  return {
    projects,
    topics,
    selectedTopicId,
    detail,
    localData,
    eventGraph,
    articles,
    totalArticles,
    loading,
    articleLoading,
    localLoading,
    eventGraphLoading,
    error,
    selectedTopic,
    loadTopics,
    loadTopic,
    loadArticles,
    loadLocalEvents,
    loadEventGraph,
    invalidateTopicLoads,
    createTopicInProject,
    saveProject,
    archiveProject,
    removeProject,
    saveTopic,
    archiveTopic,
    removeTopic,
  }
}

export function readableError(err: unknown) {
  if (isNetworkError(err)) {
    return '无法连接到后端服务'
  }
  return errorMessage(err)
}
