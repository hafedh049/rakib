import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { StatusBadge } from '@/components/badges'
import { PortalLayout } from '@/components/PortalLayout'
import { Button, EmptyState, Panel, Skeleton, Textarea, cx } from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import { formatDate, formatDateTime } from '@/lib/format'
import type { PublicComplaint } from '@/lib/types'

export function PortalTrack({ satisfaction = false }: { satisfaction?: boolean }) {
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
            {complaint.sla_due_at && (
              <span className="text-2xs text-ink-muted">
                · {t('portal.dueBy')} {formatDate(complaint.sla_due_at, locale)}
              </span>
            )}
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

        {satisfaction && !complaint.satisfaction_submitted && (
          <SatisfactionForm token={token} onDone={() => query.refetch()} />
        )}

        {complaint.satisfaction_submitted && (
          <Panel className="border-success/30 bg-success-soft">
            <p className="text-sm font-medium text-success">
              {t('portal.rateThanks')}
            </p>
          </Panel>
        )}
      </div>
    </PortalLayout>
  )
}

function SatisfactionForm({
  token,
  onDone,
}: {
  token: string
  onDone: () => void
}) {
  const { t } = useT()
  const [score, setScore] = useState<number | null>(null)
  const [comment, setComment] = useState('')

  const submit = useMutation({
    mutationFn: () =>
      api.post('/complaints/satisfaction', { score, comment: comment || null }, { token }),
    onSuccess: onDone,
  })

  return (
    <Panel title={t('portal.rate')}>
      <p className="mb-4 text-sm text-ink-muted">{t('portal.rateLead')}</p>

      <div
        role="radiogroup"
        aria-label={t('portal.rate')}
        className="flex flex-wrap gap-2"
      >
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={score === value}
            onClick={() => setScore(value)}
            className={cx(
              'size-11 rounded-[var(--radius-control)] border text-sm font-semibold',
              'transition-colors duration-150 tabular',
              score === value
                ? 'border-primary bg-primary text-primary-ink'
                : 'border-line hover:border-primary/40 hover:bg-surface-2',
            )}
          >
            {value}
          </button>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <label htmlFor="satisfaction-comment" className="text-sm font-medium">
          {t('portal.rateComment')}
        </label>
        <Textarea
          id="satisfaction-comment"
          rows={3}
          value={comment}
          maxLength={2000}
          onChange={(event) => setComment(event.target.value)}
        />
      </div>

      <Button
        variant="primary"
        size="md"
        className="mt-4"
        disabled={!score}
        loading={submit.isPending}
        onClick={() => submit.mutate()}
      >
        {t('portal.rateSubmit')}
      </Button>
    </Panel>
  )
}
