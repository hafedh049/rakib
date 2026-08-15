import { useEffect, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { AcademicNotice } from '@/components/AcademicNotice'
import { Brandmark } from '@/components/Brandmark'
import { useT, type Locale } from '@/i18n'
import { useAuth } from '@/lib/auth'

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
      <AcademicNotice />
      {/* The one place brand red is allowed to run edge to edge. */}
      <div aria-hidden className="h-1 w-full bg-brand" />
      <header className="border-b border-line">
        <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-4 px-5">
          <Link to="/portal" className="flex items-center gap-3">
            <Brandmark size="md" />
            <span className="hidden border-s border-line ps-3 sm:block">
              <span className="block text-sm leading-tight font-semibold">
                {t('brandTagline')}
              </span>
              <span className="block text-2xs leading-tight text-ink-muted">
                {t('brandSubtitle')}
              </span>
            </span>
          </Link>

          <div className="flex items-center gap-3">
            <LocaleSwitch locale={locale} onChange={setLocale} />
            <AccountControls />
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

/**
 * A signed-in claimant must be able to see that they are signed in, reach their
 * own complaints, and sign out. Without this the portal looks logged-out while
 * /login silently bounces an authenticated user back here — which reads as
 * "login is broken".
 */
function AccountControls() {
  const { t } = useT()
  const { user, isStaff, signOut } = useAuth()
  const navigate = useNavigate()

  if (!user) {
    return (
      <Link
        to="/login"
        className="text-xs text-ink-muted underline-offset-2 hover:text-ink hover:underline"
      >
        {t('auth.signIn')}
      </Link>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <Link
        to={isStaff ? '/inbox' : '/portal/mes-reclamations'}
        className="max-w-[16ch] truncate text-xs font-medium underline-offset-2 hover:underline"
      >
        {isStaff ? t('nav.inbox') : t('portal.myComplaints')}
      </Link>
      <span className="hidden text-2xs text-ink-muted sm:inline">
        {user.full_name}
      </span>
      <button
        type="button"
        onClick={async () => {
          await signOut()
          navigate('/portal')
        }}
        className="text-xs text-ink-muted underline-offset-2 hover:text-ink hover:underline"
      >
        {t('auth.signOut')}
      </button>
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
