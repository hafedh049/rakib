export type Role = 'claimant' | 'agent' | 'supervisor' | 'admin'

export type Status =
  | 'new'
  | 'triaged'
  | 'assigned'
  | 'in_progress'
  | 'pending_claimant'
  | 'resolved'
  | 'closed'
  | 'rejected'

export type TriageState = 'pending' | 'done' | 'failed' | 'manual'
export type Channel = 'web' | 'phone' | 'agence' | 'email'
export type Sentiment = 'angry' | 'frustrated' | 'neutral' | 'positive'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  department_id: string | null
  skills: string[]
  max_concurrent: number
  is_active: boolean
  locale: string
  phone: string | null
  last_active_at: string | null
  created_at: string
}

export interface RuleHit {
  code: string
  label: string
  weight: number
  matched: string[]
}

export interface Analysis {
  category: string | null
  category_confidence: number | null
  category_alternatives: [string, number][]
  subcategory: string | null
  priority: number | null
  priority_score: number | null
  rule_hits: RuleHit[]
  sentiment: Sentiment | null
  sentiment_score: number | null
  urgency_score: number | null
  language: string | null
  keywords: string[]
  duplicate_of: string | null
  duplicate_score: number | null
  related_ids: string[]
  needs_human_triage: boolean
  triage_reason: string | null
  engine: string | null
  engine_version: string | null
  latency_ms: number | null
  analyzed_at: string | null
}

export interface Claimant {
  user_id: string | null
  full_name: string
  email: string | null
  phone: string | null
  external_id: string | null
  is_vip: boolean
}

export interface Assignment {
  department_id: string | null
  department_code: string | null
  agent_id: string | null
  assigned_at: string | null
  method: string
}

export interface SLA {
  due_at: string | null
  hours: number | null
  breached: boolean
  warned: boolean
  escalation_level: number
  resolved_at: string | null
}

export interface Message {
  id: string
  at: string
  author_type: 'agent' | 'claimant' | 'system'
  author_id: string | null
  author_name: string | null
  body: string
  internal: boolean
}

export interface TimelineEntry {
  at: string
  actor_type: 'system' | 'agent' | 'user' | 'engine'
  actor_id: string | null
  action: string
  meta: Record<string, unknown>
}

export interface Attachment {
  id: string
  filename: string
  content_type: string
  size: number
}

export interface ComplaintListItem {
  id: string
  ref: string
  subject: string
  channel: Channel
  status: Status
  triage_state: TriageState
  claimant: Claimant
  analysis: Analysis
  assignment: Assignment | null
  sla_due_at: string | null
  sla_breached: boolean
  sla_warned: boolean
  created_at: string
  updated_at: string
}

export interface Complaint {
  id: string
  ref: string
  channel: Channel
  claimant: Claimant
  subject: string
  body: string
  normalized_text: string
  attachments: Attachment[]
  analysis: Analysis
  assignment: Assignment | null
  sla: SLA
  status: Status
  triage_state: TriageState
  messages: Message[]
  timeline: TimelineEntry[]
  satisfaction: { score: number; comment: string | null } | null
  corrected: boolean
  created_at: string
  updated_at: string
}

export interface Page<T> {
  items: T[]
  next_cursor: string | null
  has_more: boolean
}

export interface Department {
  id: string
  code: string
  name: string
  description: string
  keywords: string[]
  categories: string[]
  default_sla_hours: number | null
  escalation_to: string | null
  active: boolean
}

export interface Rule {
  id: string
  code: string
  label: string
  kind: string
  config: Record<string, unknown>
  weight: number
  active: boolean
  order: number
  builtin: boolean
}

export interface SimulationResult {
  priority: number
  priority_score: number
  urgency_score: number
  sentiment: Sentiment
  sentiment_score: number
  language: string
  language_source: string
  subcategory: string | null
  normalized_text: string
  transliterated: string
  hits: RuleHit[]
  features: Record<string, number | boolean>
}

export interface KBArticle {
  id: string
  title: string
  content: string
  category: string | null
  language: string
  tags: string[]
  template: string | null
  slots: string[]
  usage_count: number
  usage_breakdown: Record<string, number>
  active: boolean
  updated_at: string
}

export interface Draft {
  text: string
  source_article_id: string
  score: number
  filled_slots: Record<string, string>
}

export interface SuggestionResponse {
  language: string
  drafts: Draft[]
  cited_articles: string[]
  missing_slots: string[]
}

export interface PublicComplaint {
  ref: string
  subject: string
  body: string
  status: Status
  channel: Channel
  department: string | null
  created_at: string
  updated_at: string
  sla_due_at: string | null
  messages: {
    at: string
    author_type: 'agent' | 'claimant' | 'system'
    author_name: string | null
    body: string
  }[]
  satisfaction_submitted: boolean
}

export interface Overview {
  window_days: number
  total: number
  open: number
  closed: number
  by_status: Record<string, number>
  by_priority: Record<string, number>
  sla: { breached: number; compliance_rate: number }
  avg_resolution_hours: number | null
  resolved_count: number
  needs_human_triage: number
  duplicates_detected: number
  satisfaction: { average: number | null; responses: number }
}
