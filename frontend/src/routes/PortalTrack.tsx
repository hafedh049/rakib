import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { StatusBadge } from '@/components/badges'
import { PortalLayout } from '@/components/PortalLayout'
import { EmptyState, Panel, Skeleton, cx } from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import { formatDate, formatDateTime } from '@/lib/format'
import type { PublicComplaint } from '@/lib/types'

export function PortalTrack() {
  const { t, locale } = useT()
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''

  const query = useQuery({
    queryKey: ['portal-track', token],
    queryFn: () => api.get<PublicComplaint>('/complaints/track', { token }),
    enabled: Boolean(token),
    retry: false,
  })

  if (!token || query.isError) {
    return (
      <PortalLayout>
        <EmptyState
          title={t('portal.trackInvalid')}
          help={t('portal.trackInvalidHelp')}
        />
      </PortalLayout>
    )
  }

  if (query.isLoading || !query.data) {
    return (
      <PortalLayout>
        <div className="flex flex-col gap-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </PortalLayout>
    )
  }

  const complaint = query.data

  return (
    <PortalLayout>
      <div className="anim-in flex flex-col gap-7">
        <header className="flex flex-col gap-2">
          <p className="ltr-isolate text-xs tabular text-ink-muted">
            {complaint.ref}
          </p>
          <h1 className="text-2xl">{complaint.subject}</h1>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={complaint.status} />
            <span className="text-2xs text-ink-muted">
              {t('portal.deposited')} {formatDate(complaint.created_at, locale)}
            </span>
          </div>
        </header>

        <Panel>
          <p className="text-sm whitespace-pre-wrap">{complaint.body}</p>
        </Panel>

        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold">{t('portal.exchanges')}</h2>
          {complaint.messages.length === 0 ? (
            <Panel>
              <p className="text-sm">{t('portal.noExchanges')}</p>
              <p className="mt-1 text-xs text-ink-muted">
                {t('portal.noExchangesHelp')}
              </p>
            </Panel>
          ) : (
            <ul className="flex flex-col gap-3">
              {complaint.messages.map((message, index) => (
                <li
                  key={index}
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

