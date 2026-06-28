import axios from 'axios'
import type {
  AcademicLayer,
  Article,
  CountryCompare,
  CrossSynthesis,
  LocalEventsPayload,
  SearchJob,
  SentimentLayer,
  TopicDetail,
  TopicSummary,
} from '../types/dossier'

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export async function fetchTopics() {
  const res = await axios.get<TopicSummary[]>(`${API_BASE}/api/topics`)
  return res.data
}

export async function fetchTopic(id: number) {
  const res = await axios.get<TopicDetail>(`${API_BASE}/api/topics/${id}`)
  return res.data
}

export async function fetchArticles(id: number, limit: number) {
  const res = await axios.get<{ total: number; items: Article[] }>(
    `${API_BASE}/api/topics/${id}/articles`,
    { params: { limit } },
  )
  return res.data
}

export async function fetchLocalEvents(id: number) {
  const res = await axios.get<LocalEventsPayload>(`${API_BASE}/api/topics/${id}/local-events`)
  return res.data
}

export async function fetchCountryCompare(topicId: number, articleIds?: number[]) {
  const res = await axios.get<CountryCompare>(`${API_BASE}/api/topics/${topicId}/country-compare`, {
    params: articleIds?.length ? { article_ids: articleIds } : undefined,
    paramsSerializer: { indexes: null },
  })
  return res.data
}

export async function fetchAcademic(topicId: number) {
  const res = await axios.get<AcademicLayer>(`${API_BASE}/api/topics/${topicId}/academic`)
  return res.data
}

export async function fetchSentiment(topicId: number) {
  const res = await axios.get<SentimentLayer>(`${API_BASE}/api/topics/${topicId}/sentiment`)
  return res.data
}

export async function fetchCrossSynthesis(topicId: number) {
  const res = await axios.get<CrossSynthesis>(`${API_BASE}/api/topics/${topicId}/cross-synthesis`)
  return res.data
}

export async function createSearchJob(query: string) {
  const res = await axios.post<SearchJob>(`${API_BASE}/api/search/jobs`, {
    query,
    collect: true,
    gdelt: false,
    min_relevance: 0,
  })
  return res.data
}

export async function createDeepAnalysisJob(topicId: number, enrichLimit = 30) {
  const res = await axios.post<SearchJob>(`${API_BASE}/api/topics/${topicId}/deep-analysis/jobs`, {
    enrich_limit: enrichLimit,
  })
  return res.data
}

export async function createAcademicJob(topicId: number, topN = 30) {
  const res = await axios.post<SearchJob>(`${API_BASE}/api/topics/${topicId}/academic/jobs`, {
    top_n: topN,
  })
  return res.data
}

export async function createSentimentJob(topicId: number, limit = 25) {
  const res = await axios.post<SearchJob>(`${API_BASE}/api/topics/${topicId}/sentiment/jobs`, {
    limit,
  })
  return res.data
}

export async function createCrossSynthesisJob(topicId: number) {
  const res = await axios.post<SearchJob>(`${API_BASE}/api/topics/${topicId}/cross-synthesis/jobs`)
  return res.data
}

export async function fetchSearchJob(jobId: string) {
  const res = await axios.get<SearchJob>(`${API_BASE}/api/search/jobs/${jobId}`)
  return res.data
}

export async function rerunSearchJob(jobId: string) {
  const res = await axios.post<SearchJob>(`${API_BASE}/api/search/jobs/${jobId}/rerun`)
  return res.data
}

export function isNetworkError(err: unknown) {
  return axios.isAxiosError(err) && err.code === 'ERR_NETWORK'
}

export function errorMessage(err: unknown) {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail || err.message
  }
  return err instanceof Error ? err.message : '未知错误'
}
