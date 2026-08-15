import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useT } from '@/i18n'
import { useAuth } from '@/lib/auth'
import { initials } from '@/lib/format'
import { useSSE } from '@/lib/sse'
import type { Role } from '@/lib/types'

import { Button, cx } from './ui'

const THEME_KEY = 'rakib.theme'

/** The console defaults to dark (eight hours in one window); the portal never
 *  changes theme, so this only ever applies inside the shell. */
function useConsoleTheme() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const stored = localStorage.getItem(THEME_KEY)
    if (stored === 'dark' || stored === 'light') return stored
    // Dark unless the agent chooses otherwise. Deferring to the OS meant a
    // light-mode laptop got a light console, which is not the eight-hours-in-
    // one-window surface DESIGN.md commits to. The toggle still wins, and the
    // choice persists.
    return 'dark'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem(THEME_KEY, theme)
    return () => {
      delete document.documentElement.dataset.theme
    }
  }, [theme])

  return [theme, setTheme] as const
}

interface NavItem {
  to: string
  labelKey: Parameters<ReturnType<typeof useT>['t']>[0]
  minimum: Role
}

const PRIMARY: NavItem[] = [
  { to: '/inbox', labelKey: 'nav.inbox', minimum: 'agent' },
  { to: '/supervision', labelKey: 'nav.supervision', minimum: 'supervisor' },
  { to: '/analytics', labelKey: 'nav.analytics', minimum: 'agent' },
]

const ADMIN: NavItem[] = [
  { to: '/admin/rules', labelKey: 'nav.rules', minimum: 'supervisor' },
  { to: '/admin/kb', labelKey: 'nav.kb', minimum: 'supervisor' },
  { to: '/admin/users', labelKey: 'nav.users', minimum: 'admin' },
  { to: '/admin/departments', labelKey: 'nav.departments', minimum: 'admin' },
]

export function AppShell() {
  const { t } = useT()
  const { user, signOut, can } = useAuth()
  const { connected } = useSSE()
  const [theme, setTheme] = useConsoleTheme()
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()

  const visiblePrimary = PRIMARY.filter((item) => can(item.minimum))
  const visibleAdmin = ADMIN.filter((item) => can(item.minimum))

  return (
    <div className="flex min-h-dvh bg-bg text-ink">
      {/* Sidebar collapses to a drawer below lg rather than reflowing content. */}
      <aside
        className={cx(
          'fixed inset-y-0 start-0 z-[var(--z-sticky)] flex w-60 shrink-0 flex-col',
          'border-e border-line bg-surface transition-transform duration-200',
          'ease-[var(--ease-out-quint)] lg:static lg:translate-x-0',
          menuOpen ? 'translate-x-0' : 'ltr:-translate-x-full rtl:translate-x-full',
        )}
      >
        <div className="flex h-14 items-center gap-2 border-b border-line px-4">
          <Mark />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{t('brand')}</p>
            <p className="truncate text-2xs text-ink-muted">{t('brandTagline')}</p>
          </div>
        </div>

        <nav className="scroll-thin flex-1 overflow-y-auto p-2">
          <ul className="flex flex-col gap-0.5">
            {visiblePrimary.map((item) => (
              <li key={item.to}>
                <SideLink to={item.to} onNavigate={() => setMenuOpen(false)}>
                  {t(item.labelKey)}
                </SideLink>
              </li>
            ))}
          </ul>

          {visibleAdmin.length > 0 && (
            <>
              <p className="mt-5 mb-1 px-3 text-2xs tracking-wide text-ink-muted uppercase">
                {t('nav.admin')}
              </p>
              <ul className="flex flex-col gap-0.5">
                {visibleAdmin.map((item) => (
                  <li key={item.to}>
                    <SideLink to={item.to} onNavigate={() => setMenuOpen(false)}>
                      {t(item.labelKey)}
                    </SideLink>
                  </li>
                ))}
              </ul>
            </>
          )}
        </nav>

        <div className="border-t border-line p-3">
          <div className="mb-2 flex items-center gap-2">
            <span
              aria-hidden
              className="grid size-8 shrink-0 place-items-center rounded-full bg-primary-soft text-2xs font-semibold text-primary"
            >
              {initials(user?.full_name ?? '')}
            </span>
            <div className="min-w-0">
              <p className="truncate text-xs font-medium">{user?.full_name}</p>
              <p className="truncate text-2xs text-ink-muted">{user?.role}</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              className="flex-1"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              aria-label={t('nav.theme')}
            >
              {theme === 'dark' ? '☾' : '☀'} {t('nav.theme')}
            </Button>
            <Button
              variant="ghost"
              onClick={async () => {
                await signOut()
                navigate('/login')
              }}
            >
              {t('auth.signOut')}
            </Button>
          </div>
        </div>
      </aside>

      {menuOpen && (
        <button
          type="button"
          aria-label={t('common.close')}
          onClick={() => setMenuOpen(false)}
          className="fixed inset-0 z-[var(--z-backdrop)] bg-black/40 lg:hidden"
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-[var(--z-sticky)] flex h-14 items-center gap-3 border-b border-line bg-bg/85 px-4 backdrop-blur-sm lg:hidden">
          <Button variant="ghost" onClick={() => setMenuOpen(true)} aria-label="Menu">
            ☰
          </Button>
          <span className="text-sm font-semibold">{t('brand')}</span>
          <ConnectionDot connected={connected} />
        </header>

        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>

      <div className="fixed bottom-3 end-3 z-[var(--z-toast)] hidden lg:block">
        <ConnectionDot connected={connected} labelled />
      </div>
    </div>
  )
}

function SideLink({
  to,
  children,
  onNavigate,
}: {
  to: string
  children: React.ReactNode
  onNavigate: () => void
}) {
  return (
    <NavLink
      to={to}
      onClick={onNavigate}
      className={({ isActive }) =>
        cx(
          'block rounded-[var(--radius-control)] px-3 py-2 text-sm transition-colors duration-150',
          isActive
            ? 'bg-primary-soft font-medium text-primary'
            : 'text-ink-muted hover:bg-surface-2 hover:text-ink',
        )
      }
    >
      {children}
    </NavLink>
  )
}

/** Live-ness is a real signal in a console driven by server events: if the
 *  stream is down, the queue silently stops updating. */
function ConnectionDot({
  connected,
  labelled = false,
}: {
  connected: boolean
  labelled?: boolean
}) {
  const title = connected ? 'Flux temps reel actif' : 'Flux temps reel interrompu'
  return (
    <span
      title={title}
      className={cx(
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-2xs',
        connected
          ? 'border-success/30 bg-success-soft text-success'
          : 'border-amber/30 bg-amber-soft text-amber',
      )}
    >
      <span
        aria-hidden
        className={cx(
          'size-1.5 rounded-full',
          connected ? 'bg-success' : 'bg-amber',
        )}
      />
      {labelled && (connected ? 'Direct' : 'Hors ligne')}
      <span className="sr-only">{title}</span>
    </span>
  )
}

function Mark() {
  return (
    <span
      aria-hidden
      className="grid size-8 shrink-0 place-items-center rounded-[var(--radius-control)] bg-primary text-primary-ink"
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
  )
}
