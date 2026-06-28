import { computed, ref } from 'vue'
import {
  errorMessage,
  fetchArticles,
  fetchLocalEvents,
  fetchTopic,
  fetchTopics,
  isNetworkError,
} from '../api/dossierApi'
import type { Article, LocalEventsPayload, TopicDetail, TopicSummary } from '../types/dossier'

const pageSize = 80

export function useTopicData() {
  const topics = ref<TopicSummary[]>([])
  const selectedTopicId = ref<number | null>(null)
  const detail = ref<TopicDetail | null>(null)
  const localData = ref<LocalEventsPayload | null>(null)
  const articles = ref<Article[]>([])
  const totalArticles = ref(0)
  const loading = ref(true)
  const articleLoading = ref(false)
  const localLoading = ref(false)
  const error = ref('')

  const selectedTopic = computed(() =>
    topics.value.find((topic) => topic.id === selectedTopicId.value) || detail.value,
  )

  async function loadTopics(preferTopicId?: number) {
    loading.value = true
    error.value = ''
    try {
      const data = await fetchTopics()
      topics.value = data
      selectedTopicId.value = preferTopicId || selectedTopicId.value || data[0]?.id || null
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

  return {
    topics,
    selectedTopicId,
    detail,
    localData,
    articles,
    totalArticles,
    loading,
    articleLoading,
    localLoading,
    error,
    selectedTopic,
    loadTopics,
    loadTopic,
    loadArticles,
    loadLocalEvents,
  }
}

export function readableError(err: unknown) {
  if (isNetworkError(err)) {
    return '无法连接到后端服务'
  }
  return errorMessage(err)
}
