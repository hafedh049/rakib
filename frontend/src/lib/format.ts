import type { Locale } from '@/i18n'

const LOCALE_TAG: Record<Locale, string> = { fr: 'fr-TN', ar: 'ar-TN' }

export function formatDate(value: string | null, locale: Locale = 'fr') {
  if (!value) return '—'
  return new Date(value).toLocaleDateString(LOCALE_TAG[locale], {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export function formatDateTime(value: string | null, locale: Locale = 'fr') {
  if (!value) return '—'
  return new Date(value).toLocaleString(LOCALE_TAG[locale], {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** "il y a 4 h" / "dans 2 j" — Intl handles the plural and the language. */
export function formatRelative(value: string | null, locale: Locale = 'fr') {
  if (!value) return '—'
  const deltaSeconds = (new Date(value).getTime() - Date.now()) / 1000
  const formatter = new Intl.RelativeTimeFormat(LOCALE_TAG[locale], {
    numeric: 'auto',
  })

  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31_536_000],
    ['month', 2_592_000],
    ['day', 86_400],
    ['hour', 3600],
    ['minute', 60],
  ]
  for (const [unit, seconds] of units) {
    if (Math.abs(deltaSeconds) >= seconds) {
      return formatter.format(Math.round(deltaSeconds / seconds), unit)
    }
  }
  return formatter.format(Math.round(deltaSeconds), 'second')
}

/** Compact countdown for the SLA badge: "3 h 12" / "-1 j 4 h". */
export function countdown(value: string | null): string {
  if (!value) return '—'
  const delta = new Date(value).getTime() - Date.now()
  const overdue = delta < 0
  const total = Math.abs(delta)

  const days = Math.floor(total / 86_400_000)
  const hours = Math.floor((total % 86_400_000) / 3_600_000)
  const minutes = Math.floor((total % 3_600_000) / 60_000)

  const body =
    days > 0 ? `${days} j ${hours} h` : hours > 0 ? `${hours} h ${minutes}` : `${minutes} min`
  return overdue ? `-${body}` : body
}

export function slaState(
  dueAt: string | null,
  breached: boolean,
  warned: boolean,
): 'ok' | 'warning' | 'breached' | 'none' {
  if (breached) return 'breached'
  if (!dueAt) return 'none'
  if (new Date(dueAt).getTime() < Date.now()) return 'breached'
  return warned ? 'warning' : 'ok'
}

export function percent(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toFixed(digits)} %`
}

export function initials(name: string) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
