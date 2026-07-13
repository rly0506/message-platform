import axios from 'axios'
import type {
  AcademicLayer,
  Article,
  ArticlePerspective,
  AutoRefreshStatus,
  CognitionLabel,
  CognitionMark,
  CognitionProfileItem,
  CountryCompare,
  CoverageSnapshot,
  CrossSynthesis,
  DiscoveryReport,
  DiscoveryReportMeta,
  DiscoveryTimelineTree,
  EventContrastPayload,
  EventGraphPayload,
  EventAnaloguesPayload,
  LocalEventsPayload,
  OpenCliDiagnostics,
  ProjectSummary,
  SearchJob,
  SentimentLayer,
  SourceImportResult,
  SourceRegistry,
  TopicDetail,
  TopicSummary,
} from '../types/dossier'

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export async function fetchTopics() {
  const res = await axios.get<TopicSummary[]>(`${API_BASE}/api/topics`)
  return res.data
}

export async function fetchProjects() {
  const res = await axios.get<ProjectSummary[]>(`${API_BASE}/api/projects`)
  return res.data
}

export async function fetchSources() {
  const res = await axios.get<SourceRegistry[]>(`${API_BASE}/api/sources`)
  return res.data
}

export async function createSource(payload: Partial<SourceRegistry>) {
  const res = await axios.post<SourceRegistry>(`${API_BASE}/api/sources`, payload)
  return res.data
}

export async function importSources(payload: {
  text: string
  country?: string
  language?: string
  source_type?: string
  quality_tier?: string
  notes?: string
}) {
  const res = await axios.post<SourceImportResult>(`${API_BASE}/api/sources/import`, payload)
  return res.data
}

export async function updateSource(id: number, payload: Partial<SourceRegistry>) {
  const res = await axios.patch<SourceRegistry>(`${API_BASE}/api/sources/${id}`, payload)
  return res.data
}

export async function createProject(payload: {
  name: string
  description?: string
  status?: string
}) {
  const res = await axios.post<ProjectSummary>(`${API_BASE}/api/projects`, payload)
  return res.data
}

export async function updateProject(
  id: number,
  payload: {
    name?: string
    description?: string
    status?: string
  },
) {
  const res = await axios.patch<ProjectSummary>(`${API_BASE}/api/projects/${id}`, payload)
  return res.data
}

export async function deleteProject(id: number) {
  const res = await axios.delete<{ deleted: boolean; project_id: number }>(`${API_BASE}/api/projects/${id}`)
  return res.data
}

export async function createTopic(payload: {
  project_id?: number | null
  name: string
  description?: string
  queries?: string[]
  status?: string
}) {
  const res = await axios.post<TopicSummary>(`${API_BASE}/api/topics`, payload)
  return res.data
}

export async function updateTopic(
  id: number,
  payload: {
    project_id?: number | null
    name?: string
    description?: string
    queries?: string[]
    status?: string
  },
) {
  const res = await axios.patch<TopicSummary>(`${API_BASE}/api/topics/${id}`, payload)
  return res.data
}

export async function deleteTopic(id: number) {
  const res = await axios.delete<{ deleted: boolean; topic_id: number }>(`${API_BASE}/api/topics/${id}`)
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
  domain?: string
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

export async function fetchEventGraph(topicId: number) {
  const res = await axios.get<EventGraphPayload>(`${API_BASE}/api/topics/${topicId}/event-graph`)
  return res.data
}

export async function fetchEventContrast(topicId: number, eventId: number) {
  const res = await axios.get<EventContrastPayload>(
    `${API_BASE}/api/topics/${topicId}/events/${eventId}/contrast`,
  )
  return res.data
}

export async function fetchEventAnalogues(topicId: number, eventId: number) {
  const res = await axios.get<EventAnaloguesPayload>(
    `${API_BASE}/api/topics/${topicId}/events/${eventId}/analogues`,
  )
  return res.data
}

// RM-055 Phase 1 契约（GPT 交付，纯 SQL 无 LLM）。event_id 可选：给了就按事件证据子集聚合。
export async function fetchCoverage(topicId: number, eventId?: number | null) {
  const res = await axios.get<CoverageSnapshot>(`${API_BASE}/api/topics/${topicId}/coverage`, {
    params: eventId != null ? { event_id: eventId } : undefined,
  })
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

export async function fetchOpenCliDiagnostics() {
  const res = await axios.get<OpenCliDiagnostics>(`${API_BASE}/api/integrations/opencli/diagnostics`)
  return res.data
}

export async function fetchAutoRefreshStatus() {
  const res = await axios.get<AutoRefreshStatus>(`${API_BASE}/api/auto-refresh/status`)
  return res.data
}

export async function runAutoRefreshNow() {
  const res = await axios.post<AutoRefreshStatus>(`${API_BASE}/api/auto-refresh/run`)
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
