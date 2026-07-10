export type TopicSummary = {
  id: number
  project_id?: number | null
  project_name?: string
  name: string
  description: string
  queries: string[]
  status: string
  archived_at?: string | null
  article_count: number
  source_count: number
  enriched_count: number
  relevant_count: number
  latest_published_at: string | null
  updated_at?: string | null
}

export type ProjectSummary = {
  id: number
  name: string
  description: string
  status: string
  archived_at: string | null
  created_at: string | null
  updated_at: string | null
  topic_count: number
  topics: TopicSummary[]
}

export type SourceRegistry = {
  id: number
  name: string
  url: string
  country: string
  language: string
  source_type: string
  quality_tier: string
  requires_login: boolean
  fulltext_support: boolean
  enabled: boolean
  last_status: string
  last_error: string
  last_fetched_at: string | null
  article_count: number
  notes: string
  coverage?: string
  access?: string
  coverage_reason?: string
  last_tested?: string | null
  state_media?: boolean
  created_at: string | null
  updated_at: string | null
}

export type SourceImportResult = {
  created_count: number
  duplicate_count: number
  invalid_count: number
  created: SourceRegistry[]
  duplicates: Array<Partial<SourceRegistry> & { line?: string; reason?: string }>
  invalid: Array<{ line: string; error: string }>
}

export type TopicDetail = TopicSummary & {
  timeline: TimelineEvent[]
  framing: SourceFraming[]
  analysis: Analysis | null
}

export type CountryRef = {
  code: string
  name: string
  mention_count?: number
}

export type CountryFirstReport = {
  date: string | null
  outlet: string
  title: string
  article_id: number
}

export type CountryCompareCountry = {
  code: string
  name: string
  is_g20: boolean
  is_party: boolean
  party_mention_count: number
  article_count: number
  stance_distribution: Record<string, number>
  outlets: string[]
  first_report: CountryFirstReport | null
  sample_titles: string[]
}

export type CountryFirstReporter = {
  date: string | null
  country_code: string
  country_name: string
  outlet: string
  title: string
  article_id: number
}

export type CountryCompare = {
  topic_id: number
  topic_name: string
  article_scope_count: number
  anchor_countries: CountryRef[]
  countries: CountryCompareCountry[]
  first_reporters: CountryFirstReporter[]
  unmapped_count: number
}

export type AcademicPaperConcept = {
  name: string
  score?: number
  level?: number | null
}

export type AcademicPaper = {
  id?: number
  openalex_id: string
  citation_key?: string
  citation?: string
  title: string
  abstract?: string
  year: number | null
  cited_by_count: number
  authors: string[]
  venue: string
  concepts?: AcademicPaperConcept[]
  doi?: string
  openalex_url?: string
  sources?: string[]
  source_count?: number
  source_links?: { source: string; url: string }[]
  url: string
}

export type AcademicGraphNode = {
  id: string
  title: string
  year: number | null
  cited_by_count: number
}

export type AcademicGraphEdge = {
  citing_openalex_id: string
  cited_openalex_id: string
}

export type AcademicLiteratureNetworkNode = {
  id: string
  citation_key: string
  title: string
  year: number | null
  venue: string
  cited_by_count: number
}

export type AcademicLiteratureNetworkEdge = {
  citing_openalex_id: string
  cited_openalex_id: string
  citing_title: string
  cited_title: string
  relation: string
}

export type AcademicSchoolPaper = {
  openalex_id: string
  title: string
  year: number | null
  cited_by_count: number
}

export type AcademicSchool = {
  name: string
  paper_count: number
  years: number[]
  top_papers: AcademicSchoolPaper[]
  concepts: string[]
}

export type AcademicFoundationalPaper = {
  openalex_id: string
  title: string
  year: number | null
  cited_by_count: number
  internal_citations: number
}

export type AcademicLayer = {
  topic_id: number
  topic_name: string
  papers: AcademicPaper[]
  graph: {
    nodes: AcademicGraphNode[]
    edges: AcademicGraphEdge[]
  }
  literature_network?: {
    nodes: AcademicLiteratureNetworkNode[]
    edges: AcademicLiteratureNetworkEdge[]
  }
  schools: AcademicSchool[]
  foundational_papers: AcademicFoundationalPaper[]
  summary_md: string
  paper_count?: number
  edge_count?: number
  sort_strategy?: string
}

export type SentimentPost = {
  id?: number | string
  platform: string
  kind?: string
  parent_post_id?: string
  subreddit: string
  title: string
  author: string
  score: number
  num_comments: number
  url: string
  created_utc: string
  selftext_snippet: string
}

export type SentimentTimelineItem = {
  time_bucket: string
  platform: string
  dominant_frame: string
  sentiment_label: string
  sample_count: number
  confidence: number
  representative_posts: SentimentPost[]
}

export type SentimentLayer = {
  topic_id: number
  topic_name: string
  query?: string
  queries?: Record<string, string>
  platform: string
  platforms?: string[]
  warning: string
  posts: SentimentPost[]
  timeline?: SentimentTimelineItem[]
  errors?: Array<{ platform: string; error: string }>
  summary_md: string
}

export type OpenCliDiagnostics = {
  configured_command: string
  available: boolean
  resolved_path: string
  recommended_command: string
  browser_required_platforms: string[]
  start_error?: {
    kind: string
    errno: number | null
    detail: string
  } | null
  message: string
}

export type AutoRefreshStatus = {
  enabled: boolean
  running: boolean
  last_started_at: string | null
  last_finished_at: string | null
  last_error: string
  news_refreshed: number
  news_errors: string[]
  frontier_refreshed: boolean
  skipped_active: number
}

export type CrossSynthesis = {
  topic_id: number
  topic_name: string
  content_md: string
  voices_used: string[]
  chain?: Record<string, { status: string; error?: string }>
  generated_at: string | null
}

export type Article = {
  id: number
  url: string
  title: string
  title_zh: string
  source: string
  source_lang: string
  source_country: string
  published_at: string | null
  snippet: string
  snippet_zh: string
  collector: string
  enriched: boolean
  relevance: number
  relevant: boolean
  stance: string
  stance_summary: string
  substance_score?: number
  substance_note?: string
  emotion_score?: number
  emotion_note?: string
  category?: string
  category_reason?: string
  info_value_labels?: InfoValueLabel[]
}

// 行为金融学信息价值透镜标签（后端 value_lens.py 产出，本地无 LLM）。
// severity=hint 表示阅读提示，非警告；code 供样式，label/note 供展示。
export type InfoValueLabel = {
  code: string
  label: string
  note: string
  severity: 'hint'
}

export type ArticlePerspectiveItem = {
  sentence: string
  kind: 'substance' | 'emotion'
  reason: string
}

export type ArticlePerspective = {
  article_id: number
  mode: 'summary' | 'fulltext'
  items: ArticlePerspectiveItem[]
  error: string
  source_error: string
}

export type CognitionLabel = 'known' | 'unexpected' | 'doubtful' | 'unfamiliar'

export type CognitionMark = {
  id: number
  target_type: string
  target_id: number
  target_key: string
  topic_id: number | null
  label: CognitionLabel
  note: string
  domain?: string
  updated_at: string | null
}

export type CognitionSummary = {
  counts: Partial<Record<CognitionLabel, number>>
  recent: CognitionMark[]
  unfamiliar_topics: { topic_id: number; topic: string; count: number }[]
}

export type CognitionProfileItem = {
  id: number
  domain_key: string
  domain_label: string
  level: 'partial' | 'strong_partial' | 'unfamiliar' | string
  note: string
  depth?: string
  interest?: string
  confidence?: number
  evidence?: string
  recommended_seed_style?: string
  updated_at: string | null
}

export type TimelineEvent = {
  id: number
  date: string | null
  title_zh: string
  summary_zh: string
  article_ids: number[]
}

export type SourceFraming = {
  id: number
  party: string
  stance: string
  summary_zh: string
  article_ids: number[]
}

export type Analysis = {
  id: number
  generated_at: string | null
  content_md: string
}

export type ScoreBreakdown = Record<
  string,
  {
    label: string
    value: number
    weight: number
    reason: string
  }
>

export type Keyword = {
  term: string
  count: number
  weight: number
  kind?: string
  kind_label?: string
}

export type EntityGroup = {
  kind: string
  label: string
  items: Keyword[]
}

export type Criterion = {
  key: string
  label: string
  description: string
  weight: number
}

export type EvidenceArticle = {
  id: number
  url: string
  title: string
  source: string
  published_at: string | null
  snippet: string
  collector: string
  relevance: number
  stance: string
  category?: string
  category_reason?: string
}

export type SourceMatrixItem = {
  source: string
  tier: string
  tier_label: string
  article_count: number
  first_published_at: string | null
  latest_published_at: string | null
  dominant_stance: string
  stance_counts: Record<string, number>
  dominant_category?: string
  category_counts?: Record<string, number>
  representative_title: string
  article_ids: number[]
}

export type LocalEvent = {
  date: string | null
  title_zh: string
  summary_zh: string
  article_ids: number[]
  score: number
  importance_label?: string
  coverage_label?: string
  selection_basis?: string[]
  source_count: number
  article_count: number
  sources?: { name: string; count: number; tier?: string; tier_label?: string }[]
  source_matrix?: SourceMatrixItem[]
  source_tiers?: { key: string; label: string; count: number }[]
  category?: string
  category_reason?: string
  stance: string
  score_breakdown?: ScoreBreakdown
  evidence?: {
    authority_sources: string[]
    source_count: number
    article_count: number
    impact_terms: string[]
    date_span_days: number
    first_sources?: {
      name: string
      published_at: string | null
      title: string
      tier?: string
      tier_label?: string
    }[]
    source_tiers?: { key: string; label: string; count: number }[]
  }
  keywords?: Keyword[]
  entities?: Keyword[]
  location_signals?: Keyword[]
  evidence_articles?: EvidenceArticle[]
}

export type StanceEvolution = {
  period: string
  dominant_stance: string
  counts: Record<string, number>
  article_ids: number[]
}

export type NarrativeSignal = {
  claim: string
  source_count: number
  article_count: number
  first_seen: string | null
  last_seen: string | null
  sources: string[]
  article_ids: number[]
  representative_titles: string[]
}

export type LocalEventsPayload = {
  events: LocalEvent[]
  framing: SourceFraming[]
  analysis_md: string
  stance_evolution: StanceEvolution[]
  keywords: Keyword[]
  entities: Keyword[]
  entity_groups: EntityGroup[]
  criteria: Criterion[]
  narrative_signals?: NarrativeSignal[]
}

export type EventGraphNodeDTO = {
  id: number
  date: string | null
  title_zh: string
  summary_zh: string
  source_count: number
  article_count: number
}

export type EventGraphEdgeDTO = {
  from_id: number
  to_id: number
  relation_type: 'chronological' | 'shared_article' | 'shared_entity' | 'shared_source'
  direction: 'directed' | 'symmetric'
  evidence: string
  items: string[]
}

export type EventGraphPayload = {
  nodes: EventGraphNodeDTO[]
  edges: EventGraphEdgeDTO[]
  degraded: boolean
  note: string
}

// —— U2 对比透镜（理解层透镜2）契约。字段严格照 GPT 已定形状：中性 not_observed_in、可点回证据。 ——
export type EventContrastTerm = {
  term: string
  count: number
  kind: string
}

export type EventContrastArticle = {
  id: number
  title: string
  url: string
  published_at: string | null
  stance?: string
  substance_score?: number
  emotion_score?: number
}

export type EventContrastSource = {
  source: string
  tier: string
  tier_label: string
  stance: string
  stance_summary: string
  substance_score: number
  substance_note: string
  emotion_score: number
  emotion_note: string
  emphasized_entities: EventContrastTerm[]
  emphasized_keywords: EventContrastTerm[]
  representative_title: string
  url: string
  article_ids: number[]
  articles: EventContrastArticle[]
}

// 覆盖差异：某实体/关键词被部分来源提及、另一部分未观察到。中性措辞（not_observed_in ≠ 蓄意隐瞒）。
export type EventContrastGap = {
  term: string
  kind: string
  salience: number
  covered_by: string[]
  not_observed_in: string[]
  evidence_article_ids: number[]
}

export type EventContrastPayload = {
  event: {
    id: number
    date: string | null
    title_zh: string
    summary_zh: string
    source_count: number
    article_count: number
  }
  sources: EventContrastSource[]
  coverage_gaps: EventContrastGap[]
  degraded: boolean
  note: string
}

export type SearchResponse = LocalEventsPayload & {
  topic: TopicSummary
  collect: {
    raw: number
    kept: number
    new_articles: number
    new_links: number
    source_count?: number
    collector_counts?: Record<string, number>
    time_span?: { start: string | null; end: string | null }
    requests?: {
      id: string
      collector: string
      query: string
      raw_count: number
      kept_count: number
      status: string
      error?: string
    }[]
    errors?: string[]
  }
  steps: { key: string; label: string; status: string }[]
  subtopics?: string[]  // 下钻: 同一主题的更细切面 (前 3 条已并进采集, 全部供点击)
  analogues?: string[]  // 历史: 相似先例事件 (仅供点击开新搜索, 不并进本档案)
}

export type DeepAnalysisResult = {
  topic_id: number
  topic_name: string
  enrich: {
    limit: number
    pending: number
    processed: number
    relevant: number
    batches: number
    calls: number
    errors: string[]
  }
  synthesize: {
    input_articles: number
    timeline: number
    framing: number
    analysis_chars: number
    calls: number
  }
  timeline: {
    date: string | null
    title_zh: string
    summary_zh: string
    article_ids: number[]
  }[]
  framing: {
    party: string
    stance: string
    summary_zh: string
    article_ids: number[]
  }[]
  analysis_md: string
}

export type DiscoverySeed = {
  title: string
  url: string
  domain: string
  domain_label: string
  signal: number
  delta: number
  is_new: boolean
  what: string
  why: string
  still_niche: boolean
  info_value_labels?: InfoValueLabel[]
}

export type DiscoveryResult = {
  kind: 'discovery'
  markdown: string
  run_id: string
  path?: string
  annotated?: boolean
  seeds?: DiscoverySeed[]
}

export type DiscoveryReport = {
  markdown: string
  run_id: string
  path?: string
  seeds?: DiscoverySeed[]
}

export type DiscoveryReportMeta = {
  run_id: string
  created_at: string
  seed_count: number
  has_sidecar: boolean
}

export type DiscoveryTimelineItem = {
  run_id: string
  title: string
  url: string
  domain: string
  domain_label: string
  signal: number
  delta: number
  why: string
}

export type DiscoveryTimelineBranch = {
  branch_key: string
  label: string
  evidence_basis: string
  connection_kind: 'local_similarity'
  items: DiscoveryTimelineItem[]
}

export type DiscoveryTimelineTree = {
  branches: DiscoveryTimelineBranch[]
}

export type SearchJob = {
  id: string
  query: string
  status: string
  steps: { key: string; label: string; status: string }[]
  created_at: string
  updated_at: string
  result: SearchResponse | DeepAnalysisResult | AcademicLayer | SentimentLayer | CrossSynthesis | DiscoveryResult | null
  error: string
}
