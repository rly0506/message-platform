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
  analysis_meta?: AnalysisMeta | null // 分析新鲜度（后端 P1 契约；无分析时 null）
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

export type DigQueueRecord = {
  id: number
  item_key: string
  topic_id: number
  topic_name: string
  event_id: number | null
  event_title: string
  view: 'contrast' | 'analogue'
  added_at: string
  revision: number
  deleted: boolean
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
  article_ids: number[]
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

// U1 类比卡带（消费 /events/{id}/analogues）。只读、样本内结构信号，不建事件、不预言。
export type EventAnalogueBasis = {
  kind: string // shared_entity / shared_keyword / shared_narrative_signal / shared_source_tier / similar_sample_shape
  items: string[]
  weight: number
}

export type EventAnalogueItem = {
  topic_id: number
  topic_name: string
  event_id: number
  date: string | null
  title_zh: string
  similarity_score: number
  score_label: string // 较强相似 / 有限相似（后端阈值判定）
  basis: EventAnalogueBasis[]
  differences: string[] // 差异提醒必显（类比不预言）——后端保证非空
  evidence_article_ids: number[]
  evidence_articles: EventAnalogueEvidenceArticle[]
  note: string
}

export type EventAnalogueEvidenceArticle = {
  id: number
  title: string
  url: string
  source: string
  published_at: string | null
}

export type EventAnalogueScan = {
  total_events: number
  eligible_candidates: number
  scanned_candidates: number
  candidate_cap: number
  truncated: boolean
  note: string
}

export type EventAnaloguesPayload = {
  target: {
    topic_id: number
    event_id: number
    title_zh: string
    entities: string[]
    keywords: unknown[]
  }
  items: EventAnalogueItem[]
  scan: EventAnalogueScan
  degraded: boolean
  degraded_reason: string
  note: string
}

// 覆盖快照（消费 /api/topics/{id}/coverage）。纯 SQL 聚合，无 LLM。
// 红线：每个计数带 article_ids 可点回；算不出的正文指标返回 unknown；"未采集到"≠"未报道"。
export type CoverageBucket = {
  key: string // 采集器/语言/国家/来源类型/分层名；空值后端归一化为 'unknown'
  count: number
  article_ids: number[] // 证据点回
}

export type CoverageDecoding = {
  eligible_count: number // gnews 采集的文章数（只有它需要解码原始链接）
  decoded_count: number
  rate: number | null // eligible 为 0 时 null，不伪造 0
  decoded_article_ids: number[]
  not_decoded_article_ids: number[]
}

export type CoverageRegistry = {
  type_distribution: CoverageBucket[] // 来源类型（join SourceRegistry）
  tier_distribution: CoverageBucket[] // 质量分层
  unclassified_article_ids: number[] // 未登记来源→诚实标"未分层"，不猜
}

export type CoverageSnapshot = {
  topic_id: number
  event_id: number | null
  sample: {
    basis: string // persisted_topic_articles / persisted_event_articles
    article_count: number
    article_ids: number[]
    note: string // "缺席不证明来源未报道"——后端英文原文，前端不改写其语义
  }
  independent_source_count: number
  source_distribution: CoverageBucket[]
  collector_distribution: CoverageBucket[]
  language_distribution: CoverageBucket[]
  country_distribution: CoverageBucket[]
  url_decoding: CoverageDecoding
  source_registry: CoverageRegistry
  fulltext: {
    status: string // 'unknown'——正文当前不落库，V1 算不了
    reason: string
  }
}

// 分析新鲜度（GET /api/topics/{id} 的 analysis_meta）。null=无分析；sample_* null=旧行无快照→诚实"未知"。
export type AnalysisMeta = {
  source: 'llm' | 'local'
  generated_at: string | null
  sample_article_count: number | null // 分析当时的样本量（旧行为 null）
  sample_latest_published_at: string | null
  current_article_count: number // 当前话题实际文章数
  current_latest_published_at: string | null
  evidence_newer: boolean | null // 当前样本是否比分析当时更新；null=无法判断
  sample_changed: boolean | null // 样本是否变过；null=无法判断
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

export type DailyBriefingCoverage = {
  scope: 'event' | 'topic'
  article_count: number
  independent_source_count: number
  unknown_source_article_count: number
  known_language_count: number
  unknown_language_article_count: number
  article_ids: number[]
  label: string
  note: string
}

export type DailyBriefingItem = {
  topic_id: number
  topic_name: string
  event_id: number | null
  article_id: number
  title: string
  fact_summary: string
  summary_basis: 'persisted_title_and_snippet' | 'persisted_title_only'
  source: string
  published_at: string | null
  evidence_url: string
  deep_link_path: string
  deep_link_url: string | null
  fulltext: {
    status: 'unknown'
    reason: 'article_bodies_not_persisted'
  }
  coverage: DailyBriefingCoverage
}

export type DailyBriefingDomain = {
  date: string
  domain_key: string
  domain_label: string
  profile_level: string
  profile_confidence: number
  selection_basis: 'deterministic_local_profile_rotation'
  questions: string[]
  note: string
}

export type DailyBriefing = {
  generated_at: string
  basis: 'persisted_article_metadata'
  note: string
  items: DailyBriefingItem[]
  domain_today: DailyBriefingDomain | null
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
