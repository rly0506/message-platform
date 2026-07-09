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
    topics.value.find((topic) => topic.id === selectedTopicId.value) || detail.value,
  )

  async function loadTopics(preferTopicId?: number) {
    loading.value = true
    error.value = ''
    try {
      const data = await fetchTopics()
      try {
        projects.value = await fetchProjects()
      } catch {
        projects.value = []
      }
      topics.value = data
      const preferred = preferTopicId || selectedTopicId.value
      // 初次加载(无 preferred)不自动选最新创建的专题，进空状态由用户挑/搜；
      // 有 preferred 且仍存在则保持(新建/刷新后不跳走)。
      selectedTopicId.value = data.some((topic) => topic.id === preferred) ? preferred || null : null
    } catch (err) {
      error.value = readableError(err)
    } finally {
      loading.value = false
    }
  }

  async function loadTopic(id: number) {
    detail.value = await fetchTopic(id)
  }

  async function loadArticles(id: number) {
    articleLoading.value = true
    try {
      const data = await fetchArticles(id, pageSize)
      articles.value = data.items
      totalArticles.value = data.total
    } finally {
      articleLoading.value = false
    }
  }

  async function loadLocalEvents(id: number) {
    localLoading.value = true
    try {
      localData.value = await fetchLocalEvents(id)
    } finally {
      localLoading.value = false
    }
  }

  async function loadEventGraph(id: number) {
    eventGraphLoading.value = true
    try {
      eventGraph.value = await fetchEventGraph(id)
    } catch {
      // 事件图是增量增强，后端失败/未分析时静默回退到前端现算，绝不因此让页面崩。
      eventGraph.value = null
    } finally {
      eventGraphLoading.value = false
    }
  }

  async function createTopicInProject(payload: {
    project_id?: number | null
    name: string
    description?: string
    queries?: string[]
  }) {
    const topic = await createTopic(payload)
    await loadTopics(topic.id)
    await loadTopic(topic.id)
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
    await loadTopics(topic.id)
    await loadTopic(topic.id)
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
