import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { PriorityBadge, SLABadge, StatusBadge } from '@/components/badges'
import { EmptyState, Panel, Skeleton, cx } from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import { formatRelative } from '@/lib/format'
import type { ComplaintListItem, Page } from '@/lib/types'

interface Board {
  breached: number
  at_risk: number
  unassigned: number
  needs_triage: number
  new: number
}

/** The four queues a supervisor actually watches, each linking straight into a
 *  pre-filtered inbox rather than duplicating the list here. */
const QUEUES = [
  { key: 'breached', to: '/inbox?sla_breached=1', tone: 'danger' },
  { key: 'at_risk', to: '/inbox?status=in_progress', tone: 'amber' },
  { key: 'needs_triage', to: '/inbox?needs_human_triage=1', tone: 'amber' },
  { key: 'unassigned', to: '/inbox?unassigned=1', tone: 'neutral' },
] as const

const LABELS: Record<string, string> = {
  breached: 'supervision.breached',
  at_risk: 'supervision.atRisk',
  needs_triage: 'supervision.needsTriage',
  unassigned: 'supervision.unassigned',
}

export function Supervision() {
  const { t, locale } = useT()

  const board = useQuery({
    queryKey: ['supervision'],
    queryFn: () => api.get<Board>('/analytics/supervision'),
  })

  const urgent = useQuery({
    queryKey: ['complaints', { supervision: true }],
    queryFn: () =>
      api.get<Page<ComplaintListItem>>('/complaints', {
        sla_breached: true,
        limit: 12,
      }),
  })

  return (
    <div className="flex flex-col gap-5 p-5">
      <h1 className="text-lg font-semibold">{t('supervision.title')}</h1>

      <section aria-label={t('supervision.queues')}>
        <ul className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(180px,1fr))]">
          {QUEUES.map((queue) => (
            <li key={queue.key}>
              <Link
                to={queue.to}
                className={cx(
                  'flex flex-col gap-1 rounded-[var(--radius-panel)] border p-4',
                  'transition-colors duration-150 hover:bg-surface',
                  queue.tone === 'danger'
                    ? 'border-danger/30 bg-danger-soft'
                    : queue.tone === 'amber'
                      ? 'border-amber/30 bg-amber-soft'
                      : 'border-line bg-surface',
                )}
              >
                <span className="text-2xs tracking-wide text-ink-muted uppercase">
                  {t(LABELS[queue.key] as never)}
                </span>
                {board.isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <span className="text-2xl font-semibold tabular">
                    {board.data?.[queue.key] ?? 0}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <Panel title={t('supervision.breached')} bodyClassName="p-0">
        {urgent.isLoading ? (
          <div className="p-4">
            <Skeleton className="h-40 w-full" />
          </div>
        ) : !urgent.data?.items.length ? (
          <EmptyState
            title="Aucun depassement de delai"
            help="Toutes les reclamations ouvertes sont dans les temps. Cette liste se remplit automatiquement des qu une echeance est franchie."
          />
        ) : (
          <ul className="divide-y divide-line">
            {urgent.data.items.map((item) => (
              <li key={item.id}>
                <Link
                  to={`/inbox/${item.id}`}
                  className="flex flex-wrap items-center gap-2 px-4 py-3 hover:bg-surface-2"
                >
                  <PriorityBadge priority={item.analysis.priority} compact />
                  <span className="ltr-isolate text-xs tabular text-ink-muted">
                    {item.ref}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm">
                    {item.subject}
                  </span>
                  <StatusBadge status={item.status} />
                  <SLABadge
                    dueAt={item.sla_due_at}
                    breached={item.sla_breached}
                    warned={item.sla_warned}
                  />
                  <span className="text-2xs text-ink-muted">
                    {formatRelative(item.created_at, locale)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  )
}
