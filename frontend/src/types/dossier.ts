export type TopicSummary = {
  id: number
  name: string
  description: string
  queries: string[]
  status: string
  article_count: number
  source_count: number
  enriched_count: number
  relevant_count: number
  latest_published_at: string | null
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
  title: string
  abstract?: string
  year: number | null
  cited_by_count: number
  authors: string[]
  venue: string
  concepts?: AcademicPaperConcept[]
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

export type SentimentLayer = {
  topic_id: number
  topic_name: string
  query?: string
  queries?: Record<string, string>
  platform: string
  platforms?: string[]
  warning: string
  posts: SentimentPost[]
  errors?: Array<{ platform: string; error: string }>
  summary_md: string
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
