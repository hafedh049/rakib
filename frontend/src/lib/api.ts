/**
 * API client.
 *
 * Access tokens live in memory only; the refresh token is the one thing kept in
 * localStorage. A 401 triggers exactly one refresh attempt, and concurrent 401s
 * share it — otherwise a page with six queries fires six refreshes and the
 * rotation policy revokes the whole family as suspected theft.
 */

export const API_BASE = '/api/v1'
const REFRESH_KEY = 'rakib.refresh'

export interface Problem {
  type: string
  title: string
  status: number
  detail: string
  errors?: { field: string; message: string }[]
}

export class ApiError extends Error {
  readonly status: number
  readonly problem: Problem | null

  constructor(status: number, problem: Problem | null, fallback: string) {
    super(problem?.detail || problem?.title || fallback)
    this.status = status
    this.problem = problem
    this.name = 'ApiError'
  }

  fieldErrors(): Record<string, string> {
    const result: Record<string, string> = {}
    for (const entry of this.problem?.errors ?? []) {
      result[entry.field] = entry.message
    }
    return result
  }
}

let accessToken: string | null = null
let refreshInFlight: Promise<boolean> | null = null
const listeners = new Set<(authenticated: boolean) => void>()

export function setTokens(access: string | null, refresh?: string | null) {
  accessToken = access
  if (refresh !== undefined) {
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
    else localStorage.removeItem(REFRESH_KEY)
  }
  listeners.forEach((listener) => listener(Boolean(access)))
}

export const getAccessToken = () => accessToken
export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY)
export function onAuthChange(listener: (authenticated: boolean) => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

async function refreshTokens(): Promise<boolean> {
  const refresh = getRefreshToken()
  if (!refresh) return false

  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!response.ok) {
      setTokens(null, null)
      return false
    }
    const data = await response.json()
    setTokens(data.access_token, data.refresh_token)
    return true
  } catch {
    setTokens(null, null)
    return false
  }
}

function ensureRefresh(): Promise<boolean> {
  refreshInFlight ??= refreshTokens().finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

interface RequestOptions {
  method?: string
  body?: unknown
  params?: Record<string, string | number | boolean | undefined | null>
  formData?: FormData
  retry?: boolean
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, params, formData, retry = true } = options

  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.append(key, String(value))
    }
  }

  const headers: Record<string, string> = {}
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  const response = await fetch(url.toString(), {
    method,
    headers,
    body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
  })

  if (response.status === 401 && retry && getRefreshToken()) {
    if (await ensureRefresh()) {
      return request<T>(path, { ...options, retry: false })
    }
  }

  if (!response.ok) {
    let problem: Problem | null = null
    try {
      problem = (await response.json()) as Problem
    } catch {
      problem = null
    }
    throw new ApiError(response.status, problem, response.statusText)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  get: <T>(path: string, params?: RequestOptions['params']) =>
    request<T>(path, { params }),
  post: <T>(path: string, body?: unknown, params?: RequestOptions['params']) =>
    request<T>(path, { method: 'POST', body, params }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: 'POST', formData }),
}
