import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { useT, type Locale } from '@/i18n'

import { cx } from './ui'

/**
 * The public shell. Always light, generous spacing, one thing at a time —
 * the person here is stressed and infrequent, unlike the agent in the console.
 */
export function PortalLayout({
  children,
  wide = false,
}: {
  children: ReactNode
  wide?: boolean
}) {
  const { t, locale, setLocale } = useT()

  // The portal is deliberately immune to the console's dark preference.
  useEffect(() => {
    const previous = document.documentElement.dataset.theme
    delete document.documentElement.dataset.theme
    return () => {
      if (previous) document.documentElement.dataset.theme = previous
    }
  }, [])

  return (
    <div className="flex min-h-dvh flex-col bg-bg text-ink">
      <header className="border-b border-line">
        <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-4 px-5">
          <Link to="/portal" className="flex items-center gap-2.5">
            <span
              aria-hidden
              className="grid size-8 place-items-center rounded-[var(--radius-control)] bg-primary text-primary-ink"
            >
              <svg viewBox="0 0 24 24" className="size-4" fill="none" strokeWidth="2.2">
                <path
                  d="M12 3.5 4.5 7v5.5c0 4.2 3 7.5 7.5 8.5 4.5-1 7.5-4.3 7.5-8.5V7L12 3.5Z"
                  stroke="currentColor"
                  strokeLinejoin="round"
                />
                <circle cx="12" cy="11.5" r="2.4" stroke="currentColor" />
              </svg>
            </span>
            <span>
              <span className="block text-sm leading-tight font-semibold">
                {t('brand')}
              </span>
              <span className="block text-2xs leading-tight text-ink-muted">
                {t('brandTagline')}
              </span>
            </span>
          </Link>

          <div className="flex items-center gap-3">
            <LocaleSwitch locale={locale} onChange={setLocale} />
            <Link
              to="/login"
              className="text-xs text-ink-muted underline-offset-2 hover:text-ink hover:underline"
            >
              {t('auth.signIn')}
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1 px-5 py-10 sm:py-14">
        <div className={cx('mx-auto w-full', wide ? 'max-w-3xl' : 'max-w-xl')}>
          {children}
        </div>
      </main>

      <footer className="border-t border-line py-6">
        <p className="mx-auto max-w-5xl px-5 text-2xs text-ink-muted">
          {t('brand')} — {t('brandTagline')}
        </p>
      </footer>
    </div>
  )
}

function LocaleSwitch({
  locale,
  onChange,
}: {
  locale: Locale
  onChange: (next: Locale) => void
}) {
  const options: { value: Locale; label: string }[] = [
    { value: 'fr', label: 'Francais' },
    { value: 'ar', label: 'العربية' },
  ]

  return (
    <div
      role="group"
      aria-label="Langue"
      className="flex items-center rounded-full border border-line p-0.5"
    >
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          aria-pressed={locale === option.value}
          className={cx(
            'rounded-full px-2.5 py-1 text-2xs transition-colors duration-150',
            locale === option.value
              ? 'bg-primary text-primary-ink'
              : 'text-ink-muted hover:text-ink',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
