import axios from 'axios'
import type {
  AcademicLayer,
  Article,
  ArticlePerspective,
  CognitionLabel,
  CognitionMark,
  CognitionProfileItem,
  CountryCompare,
  CrossSynthesis,
  DiscoveryReport,
  DiscoveryReportMeta,
  DiscoveryTimelineTree,
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

export async function fetchArticlePerspective(topicId: number, articleId: number) {
  const res = await axios.get<ArticlePerspective>(
    `${API_BASE}/api/topics/${topicId}/articles/${articleId}/perspective`,
  )
  return res.data
}

export async function saveCognitionMark(payload: {
  target_type: 'topic' | 'article' | 'event' | 'seed'
  target_id?: number
  target_key?: string
  label: CognitionLabel
  topic_id?: number | null
  note?: string
}) {
  const res = await axios.put<CognitionMark>(`${API_BASE}/api/cognition/marks`, payload)
  return res.data
}

export async function fetchCognitionMarks(topicId?: number | null, targetType = 'article') {
  const res = await axios.get<CognitionMark[]>(`${API_BASE}/api/cognition/marks`, {
    params: { ...(topicId ? { topic_id: topicId } : {}), target_type: targetType },
  })
  return res.data
}

export async function fetchCognitionProfile() {
  const res = await axios.get<CognitionProfileItem[]>(`${API_BASE}/api/cognition/profile`)
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

export async function createCrossSynthesisJob(topicId: number, refreshVoices = true) {
  const res = await axios.post<SearchJob>(
    `${API_BASE}/api/topics/${topicId}/cross-synthesis/jobs`,
    { refresh_voices: refreshVoices },
  )
  return res.data
}

export async function fetchSearchJob(jobId: string) {
  const res = await axios.get<SearchJob>(`${API_BASE}/api/search/jobs/${jobId}`)
  return res.data
}

export async function fetchLatestDiscovery() {
  const res = await axios.get<DiscoveryReport>(`${API_BASE}/api/discovery/latest`)
  return res.data
}

export async function fetchDiscoveryReports() {
  const res = await axios.get<DiscoveryReportMeta[]>(`${API_BASE}/api/discovery/reports`)
  return res.data
}

export async function fetchDiscoveryReport(runId: string) {
  const res = await axios.get<DiscoveryReport>(`${API_BASE}/api/discovery/reports/${runId}`)
  return res.data
}

export async function fetchDiscoveryTimelineTree() {
  const res = await axios.get<DiscoveryTimelineTree>(`${API_BASE}/api/discovery/timeline-tree`)
  return res.data
}

export async function createDiscoveryJob(annotate = true) {
  const res = await axios.post<SearchJob>(`${API_BASE}/api/discovery/jobs`, null, {
    params: { annotate },
  })
  return res.data
}

export async function distillSeed(title: string, domain = '') {
  const res = await axios.post<{ query: string; llm: boolean }>(
    `${API_BASE}/api/discovery/distill`,
    { title, domain },
  )
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
