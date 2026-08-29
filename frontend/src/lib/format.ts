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
