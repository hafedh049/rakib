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

export interface Analysis {
  category: string | null
  /** Evidence ratio, not a calibrated probability. */
  category_confidence: number | null
  category_alternatives: [string, number][]
  language: string | null
  keywords: string[]
  /** Terms that fired, per category — the explainability payload. */
  evidence: Record<string, string[]>
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

/**
 * The bank's categories, in the order they are declared in
 * `backend/app/domain/taxonomy.py`. Kept here rather than fetched: it is a
 * closed set that changes only with a deployment, and a filter that has to wait
 * on a request is a filter that flickers.
 *
 * The previous revision of this file still listed the telecom categories the
 * project started with, so the console offered eleven filters that matched
 * nothing. If this list and the backend enum ever disagree again, the symptom
 * is the same: a filter that silently returns an empty page.
 */
export const CATEGORIES = [
  'CARTE_BANCAIRE',
  'DAB_GAB',
  'PAIEMENT_TPE_ECOMMERCE',
  'VIREMENT_PRELEVEMENT',
  'CHEQUE_EFFET',
  'COMPTE_GESTION',
  'CREDIT_FINANCEMENT',
  'FRAIS_COMMISSIONS',
  'BANQUE_DIGITALE',
  'OPERATIONS_INTERNATIONALES',
  'FRAUDE_OPERATION_NON_AUTORISEE',
  'AGENCE_QUALITE_SERVICE',
] as const

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
  analysis: Analysis
  assignment: Assignment | null
  status: Status
  triage_state: TriageState
  messages: Message[]
  timeline: TimelineEntry[]
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
  active: boolean
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
  messages: {
    at: string
    author_type: 'agent' | 'claimant' | 'system'
    author_name: string | null
    body: string
  }[]
}

