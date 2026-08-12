import { useQuery } from '@tanstack/react-query'
import { Link, Navigate, useParams } from 'react-router-dom'

import { StatusBadge } from '@/components/badges'
import { PortalLayout } from '@/components/PortalLayout'
import { EmptyState, Panel, Skeleton, cx } from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDate, formatDateTime } from '@/lib/format'
import type { Complaint, ComplaintListItem, Page } from '@/lib/types'

/**
 * The signed-in claimant's own complaints.
 *
 * Scoping is the server's job: GET /complaints injects `claimant.user_id` into
 * the query for a claimant role, so this page cannot show anyone else's rows
 * even if it asked for them.
 */
export function PortalMine() {
  const { t, locale } = useT()
  const { user, loading, isStaff } = useAuth()

  const complaints = useQuery({
    queryKey: ['my-complaints'],
    queryFn: () => api.get<Page<ComplaintListItem>>('/complaints', { limit: 50 }),
    enabled: Boolean(user),
  })

  if (loading) {
    return (
      <PortalLayout>
        <Skeleton className="h-40 w-full" />
      </PortalLayout>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  if (isStaff) return <Navigate to="/inbox" replace />

  return (
    <PortalLayout>
      <div className="anim-in flex flex-col gap-6">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl">{t('portal.myComplaints')}</h1>
            <p className="text-sm text-ink-muted">{t('portal.myComplaintsLead')}</p>
          </div>
          <Link
            to="/portal"
            className="inline-flex h-10 items-center rounded-[var(--radius-control)] bg-primary px-4 text-sm font-medium text-primary-ink transition-colors duration-150 hover:bg-primary-hover"
          >
            {t('portal.newOne')}
          </Link>
        </header>

        {complaints.isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : !complaints.data?.items.length ? (
          <Panel>
            <EmptyState
              title={t('portal.noComplaints')}
              help={t('portal.noComplaintsHelp')}
            />
          </Panel>
        ) : (
          <ul className="flex flex-col gap-2">
            {complaints.data.items.map((item) => (
              <li key={item.id}>
                <Link
                  to={`/portal/reclamation/${item.id}`}
                  className={cx(
                    'flex flex-col gap-1.5 rounded-[var(--radius-panel)] border border-line',
                    'p-4 transition-colors duration-150 hover:bg-surface',
                  )}
                >
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="ltr-isolate text-2xs tabular text-ink-muted">
                      {item.ref}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm font-medium">
                      {item.subject}
                    </span>
                    <StatusBadge status={item.status} />
                  </span>
                  <span className="text-2xs text-ink-muted">
                    {t('portal.deposited')} {formatDate(item.created_at, locale)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </PortalLayout>
  )
}

/** Read-only detail for a complaint the signed-in claimant owns. */
export function PortalComplaint() {
  const { id = '' } = useParams()
  const { t, locale } = useT()
  const { user, loading } = useAuth()

  const complaint = useQuery({
    queryKey: ['my-complaint', id],
    queryFn: () => api.get<Complaint>(`/complaints/${id}`),
    enabled: Boolean(user && id),
    retry: false,
  })

  if (loading) {
    return (
      <PortalLayout>
        <Skeleton className="h-64 w-full" />
      </PortalLayout>
    )
  }
  if (!user) return <Navigate to="/login" replace />

  if (complaint.isError) {
    return (
      <PortalLayout>
        <EmptyState
          title={t('portal.trackInvalid')}
          help={t('portal.trackInvalidHelp')}
          action={
            <Link
              to="/portal/mes-reclamations"
              className="inline-flex h-8 items-center rounded-[var(--radius-control)] border border-line bg-surface px-3 text-xs font-medium hover:bg-surface-2"
            >
              {t('portal.backToList')}
            </Link>
          }
        />
      </PortalLayout>
    )
  }

  if (complaint.isLoading || !complaint.data) {
    return (
      <PortalLayout>
        <Skeleton className="h-64 w-full" />
      </PortalLayout>
    )
  }

  const data = complaint.data
  // Internal notes are already stripped server-side for a non-staff caller;
  // filtering here as well means a future API change cannot leak them.
  const messages = data.messages.filter((message) => !message.internal)

  return (
    <PortalLayout>
      <div className="anim-in flex flex-col gap-7">
        <Link
          to="/portal/mes-reclamations"
          className="inline-flex w-fit items-center gap-1 text-xs text-ink-muted hover:text-ink"
        >
          <span className="chevron" aria-hidden>
            ‹
          </span>
          {t('portal.backToList')}
        </Link>

        <header className="flex flex-col gap-2">
          <p className="ltr-isolate text-xs tabular text-ink-muted">{data.ref}</p>
          <h1 className="text-2xl">{data.subject}</h1>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={data.status} />
            <span className="text-2xs text-ink-muted">
              {t('portal.deposited')} {formatDate(data.created_at, locale)}
            </span>
          </div>
        </header>

        <Panel>
          <p className="text-sm whitespace-pre-wrap">{data.body}</p>
        </Panel>

        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold">{t('portal.exchanges')}</h2>
          {messages.length === 0 ? (
            <Panel>
              <p className="text-sm">{t('portal.noExchanges')}</p>
              <p className="mt-1 text-xs text-ink-muted">
                {t('portal.noExchangesHelp')}
              </p>
            </Panel>
          ) : (
            <ul className="flex flex-col gap-3">
              {messages.map((message) => (
                <li
                  key={message.id}
                  className={cx(
                    'rounded-[var(--radius-panel)] border p-4',
                    message.author_type === 'claimant'
                      ? 'border-line bg-surface-2'
                      : 'border-primary/25 bg-primary-soft',
                  )}
                >
                  <p className="mb-1 text-2xs text-ink-muted">
                    {formatDateTime(message.at, locale)}
                  </p>
                  <p className="text-sm whitespace-pre-wrap">{message.body}</p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </PortalLayout>
  )
}
