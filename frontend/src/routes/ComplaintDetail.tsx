import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { AnalysisPanel } from '@/components/AnalysisPanel'
import {
  ChannelBadge,
  PriorityBadge,
  SLABadge,
  StatusBadge,
} from '@/components/badges'
import {
  Badge,
  Button,
  ErrorState,
  Panel,
  Select,
  Skeleton,
  Textarea,
  Toggle,
  cx,
} from '@/components/ui'
import { useToast } from '@/components/Toasts'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { formatDateTime, formatRelative } from '@/lib/format'
import type { User,
  Complaint,
  Status,
  SuggestionResponse,
  TimelineEntry,
} from '@/lib/types'

interface AnalysisResponse {
  ref: string
  triage_state: string
  analysis: Complaint['analysis']
  duplicate_of: { id: string; ref: string; subject: string } | null
  related: { id: string; ref: string; subject: string }[]
  traces: {
    engine: string
    engine_version: string
    outcome: string
    error: string | null
    total_latency_ms: number
    created_at: string
    stages: { name: string; latency_ms: number; output_summary: Record<string, unknown> }[]
  }[]
}

const STATUSES: Status[] = [
  'new',
  'triaged',
  'assigned',
  'in_progress',
  'pending_claimant',
  'resolved',
  'closed',
  'rejected',
]

export function ComplaintDetail() {
  const { id = '' } = useParams()
  const { t, locale } = useT()
  const { notify } = useToast()
  const { can } = useAuth()
  const queryClient = useQueryClient()

  const complaint = useQuery({
    queryKey: ['complaint', id],
    queryFn: () => api.get<Complaint>(`/complaints/${id}`),
  })
  const analysis = useQuery({
    queryKey: ['complaint', id, 'analysis'],
    queryFn: () => api.get<AnalysisResponse>(`/complaints/${id}/analysis`),
    enabled: Boolean(id),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['complaint', id] })
    void queryClient.invalidateQueries({ queryKey: ['complaints'] })
  }

  const correct = useMutation({
    mutationFn: (category: string) =>
      api.patch(`/complaints/${id}`, { category }),
    onSuccess: invalidate,
  })
  const changeStatus = useMutation({
    mutationFn: (status: Status) => api.patch(`/complaints/${id}`, { status }),
    onSuccess: invalidate,
  })
  const retriage = useMutation({
    mutationFn: () => api.post(`/complaints/${id}/retriage`),
    onSuccess: invalidate,
  })

  // Supervisors only — the API enforces the same rule, this just avoids
  // showing a control that would be refused.
  const { data: agents = [] } = useQuery<User[]>({
    queryKey: ['staff'],
    queryFn: () => api.get('/users?role=agent'),
    enabled: can('supervisor'),
    staleTime: 5 * 60 * 1000,
  })

  const reassign = useMutation({
    mutationFn: (agentId: string) =>
      api.patch(`/complaints/${id}`, { agent_id: agentId || null }),
    onSuccess: (_result, agentId) => {
      invalidate()
      const name = agents.find((agent) => agent.id === agentId)?.full_name
      notify(
        name ? t('complaint.reassigned', { name }) : t('complaint.unassignedDone'),
      )
    },
    onError: () => notify(t('complaint.reassignFailed'), 'danger'),
  })

  if (complaint.isLoading) {
    return (
      <div className="grid gap-5 p-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex flex-col gap-4">
          <Skeleton className="h-10 w-2/3" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (complaint.isError || !complaint.data) {
    return (
      <ErrorState
        message={t('common.error')}
        retryLabel={t('common.retry')}
        onRetry={() => complaint.refetch()}
      />
    )
  }

  const data = complaint.data
  const closed = ['resolved', 'closed', 'rejected'].includes(data.status)

  return (
    <div className="flex flex-col">
      <header className="flex flex-col gap-3 border-b border-line px-5 py-4">
        <Link
          to="/inbox"
          className="chevron-parent inline-flex w-fit items-center gap-1 text-xs text-ink-muted hover:text-ink"
        >
          <span className="chevron" aria-hidden>
            ‹
          </span>
          {t('complaint.back')}
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="ltr-isolate text-xs tabular text-ink-muted">{data.ref}</p>
            <h1 className="text-lg font-semibold">{data.subject}</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <PriorityBadge priority={data.analysis.priority} />
            <SLABadge
              dueAt={data.sla.due_at}
              breached={data.sla.breached}
              warned={data.sla.warned}
            />
            <StatusBadge status={data.status} />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-2xs text-ink-muted">
          <ChannelBadge channel={data.channel} />
          <span className="font-medium text-ink">{data.claimant.full_name}</span>
          {data.claimant.is_vip && <Badge tone="primary">{t('complaint.vip')}</Badge>}
          {data.claimant.email && <span>{data.claimant.email}</span>}
          {data.claimant.phone && (
            <span className="ltr-isolate tabular">{data.claimant.phone}</span>
          )}
          {data.claimant.external_id && (
            <span className="ltr-isolate">{data.claimant.external_id}</span>
          )}
          <span className="ms-auto">{formatRelative(data.created_at, locale)}</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select
            className="w-auto min-w-44"
            aria-label={t('complaint.changeStatus')}
            value={data.status}
            onChange={(event) => changeStatus.mutate(event.target.value as Status)}
          >
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {t(`status.${status}` as never)}
              </option>
            ))}
          </Select>

          {can('supervisor') && (
            <Select
              className="w-auto min-w-52"
              aria-label={t('complaint.reassign')}
              value={data.assignment?.agent_id ?? ''}
              disabled={reassign.isPending}
              onChange={(event) => reassign.mutate(event.target.value)}
            >
              <option value="">{t('complaint.unassigned')}</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.full_name}
                </option>
              ))}
            </Select>
          )}

          {can('supervisor') && (
            <Button onClick={() => retriage.mutate()} loading={retriage.isPending}>
              {t('complaint.retriage')}
            </Button>
          )}
        </div>
      </header>

      <div className="grid gap-5 p-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex min-w-0 flex-col gap-5">
          <Panel title={t('complaint.messages')} bodyClassName="flex flex-col gap-4">
            <article className="rounded-[var(--radius-control)] border border-line bg-surface-2 p-4">
              <p className="mb-1 text-2xs text-ink-muted">
                {formatDateTime(data.created_at, locale)}
              </p>
              <p className="text-sm whitespace-pre-wrap">{data.body}</p>
            </article>

            {data.messages.map((message) => (
              <article
                key={message.id}
                className={cx(
                  'rounded-[var(--radius-control)] border p-4',
                  message.internal
                    ? 'border-amber/30 bg-amber-soft/40'
                    : message.author_type === 'agent'
                      ? 'border-primary/25 bg-primary-soft'
                      : 'border-line bg-surface-2',
                )}
              >
                <p className="mb-1 flex flex-wrap items-center gap-2 text-2xs text-ink-muted">
                  <span className="font-medium text-ink">
                    {message.author_name ?? '—'}
                  </span>
                  <span>{formatDateTime(message.at, locale)}</span>
                  {message.internal && (
                    <Badge tone="amber">{t('complaint.internalNote')}</Badge>
                  )}
                </p>
                <p className="text-sm whitespace-pre-wrap">{message.body}</p>
              </article>
            ))}
          </Panel>

          <Attachments complaintId={id} attachments={data.attachments} />

          {!closed && <Composer complaintId={id} onSent={invalidate} />}

          <Timeline entries={data.timeline} />
        </div>

        <aside className="flex flex-col gap-5">
          <AnalysisPanel
            analysis={data.analysis}
            triageState={data.triage_state}
            corrected={data.corrected}
            duplicateOf={analysis.data?.duplicate_of}
            related={analysis.data?.related}
            canCorrect={can('agent')}
            correcting={correct.isPending}
            onCorrect={(category) => correct.mutate(category)}
          />

          {analysis.data?.traces?.[0] && (
            <Panel title={t('analysis.stages')}>
              <ul className="flex flex-col gap-1.5">
                {analysis.data.traces[0].stages.map((stage) => (
                  <li
                    key={stage.name}
                    className="flex items-center justify-between gap-3 text-2xs"
                  >
                    <span className="text-ink-muted">{stage.name}</span>
                    <span className="tabular">{stage.latency_ms} ms</span>
                  </li>
                ))}
                <li className="mt-1 flex items-center justify-between gap-3 border-t border-line pt-1.5 text-2xs font-medium">
                  <span>{t('analysis.latency')}</span>
                  <span className="tabular">
                    {analysis.data.traces[0].total_latency_ms} ms
                  </span>
                </li>
              </ul>
            </Panel>
          )}
        </aside>
      </div>
    </div>
  )
}

function Attachments({
  complaintId,
  attachments,
}: {
  complaintId: string
  attachments: Complaint['attachments']
}) {
  const { t } = useT()

  // Presigned URLs are minted on click rather than up front: they expire, and
  // pre-fetching one per row would hand out credentials nobody uses.
  async function open(attachmentId: string) {
    const { url } = await api.get<{ url: string }>(
      `/complaints/${complaintId}/attachments/${attachmentId}`,
    )
    window.open(url, '_blank', 'noopener')
  }

  return (
    <Panel title={t('complaint.attachments')} bodyClassName="p-0">
      {attachments.length === 0 ? (
        <p className="px-4 py-3 text-xs text-ink-muted">
          {t('complaint.noAttachments')}
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {attachments.map((attachment) => (
            <li
              key={attachment.id}
              className="flex items-center gap-3 px-4 py-2.5"
            >
              <span className="min-w-0 flex-1 truncate text-xs">
                {attachment.filename}
              </span>
              <span className="text-2xs tabular text-ink-muted">
                {(attachment.size / 1024).toFixed(0)} Ko
              </span>
              <Button onClick={() => open(attachment.id)}>
                {t('complaint.download')}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}

function Composer({
  complaintId,
  onSent,
}: {
  complaintId: string
  onSent: () => void
}) {
  const { t } = useT()
  const [body, setBody] = useState('')
  const [internal, setInternal] = useState(false)
  const [usedArticle, setUsedArticle] = useState<string | null>(null)

  const suggestions = useMutation({
    mutationFn: () =>
      api.get<SuggestionResponse>(`/complaints/${complaintId}/suggest`),
  })

  const send = useMutation({
    mutationFn: async () => {
      await api.post(`/complaints/${complaintId}/messages`, { body, internal })
      // Usage is only meaningful once the reply is actually sent.
      if (usedArticle && !internal) {
        await api.post(`/complaints/${complaintId}/suggest/used`, {
          article_id: usedArticle,
          outcome: 'edited',
        })
      }
    },
    onSuccess: () => {
      setBody('')
      setUsedArticle(null)
      suggestions.reset()
      onSent()
    },
  })

  const resolve = useMutation({
    mutationFn: () =>
      api.post(`/complaints/${complaintId}/resolve`, { resolution: body }),
    onSuccess: () => {
      setBody('')
      onSent()
    },
  })

  return (
    <Panel
      title={internal ? t('complaint.internalNote') : t('complaint.reply')}
      action={
        <Toggle
          checked={internal}
          onChange={setInternal}
          label={t('complaint.internalNote')}
        />
      }
      bodyClassName="flex flex-col gap-3"
    >
      <Textarea
        rows={5}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        placeholder={
          internal ? t('complaint.internalOnly') : t('complaint.reply')
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="primary"
          disabled={!body.trim()}
          loading={send.isPending}
          onClick={() => send.mutate()}
        >
          {send.isPending ? t('complaint.sending') : t('complaint.send')}
        </Button>

        {!internal && (
          <Button
            onClick={() => suggestions.mutate()}
            loading={suggestions.isPending}
          >
            {suggestions.isPending
              ? t('complaint.suggesting')
              : t('complaint.suggest')}
          </Button>
        )}

        {!internal && (
          <Button
            variant="secondary"
            className="ms-auto"
            disabled={!body.trim()}
            loading={resolve.isPending}
            onClick={() => resolve.mutate()}
          >
            {t('complaint.resolve')}
          </Button>
        )}
      </div>

      {suggestions.data && (
        <div className="flex flex-col gap-2 border-t border-line pt-3">
          <p className="text-2xs tracking-wide text-ink-muted uppercase">
            {t('complaint.suggestions')}
          </p>

          {suggestions.data.missing_slots.length > 0 && (
            <p className="text-2xs text-amber">
              {t('complaint.missingSlots')} :{' '}
              {suggestions.data.missing_slots.join(', ')}
            </p>
          )}

          {suggestions.data.drafts.map((draft) => (
            <article
              key={draft.source_article_id}
              className="rounded-[var(--radius-control)] border border-line p-3"
            >
              <p className="mb-2 max-h-40 overflow-y-auto text-xs whitespace-pre-wrap text-ink-muted">
                {draft.text}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => {
                    setBody(draft.text)
                    setUsedArticle(draft.source_article_id)
                  }}
                >
                  {t('complaint.useDraft')}
                </Button>
                <span className="text-2xs tabular text-ink-muted">
                  {t('rules.resultScore')} {draft.score.toFixed(2)}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}
    </Panel>
  )
}

function Timeline({ entries }: { entries: TimelineEntry[] }) {
  const { t, locale } = useT()

  return (
    <Panel title={t('complaint.timeline')}>
      <ol className="flex flex-col gap-3">
        {entries.map((entry, index) => (
          <li key={index} className="flex gap-3">
            {/* Engine actions read visually distinct from human ones — an agent
                must be able to tell at a glance what the system did alone. */}
            <span
              aria-hidden
              className={cx(
                'mt-1.5 size-2 shrink-0 rounded-full',
                entry.actor_type === 'engine'
                  ? 'bg-primary'
                  : entry.actor_type === 'system'
                    ? 'bg-line'
                    : 'bg-ink-muted',
              )}
            />
            <div className="min-w-0 flex-1">
              <p className="text-xs">
                {/* Fall back to the raw code rather than a blank line if a new
                    action ships before its translation does. */}
                <span className="font-medium">
                  {t(`action.${entry.action}` as never) === `action.${entry.action}`
                    ? entry.action
                    : t(`action.${entry.action}` as never)}
                </span>
                {entry.actor_type === 'engine' && (
                  <span className="ms-2 text-2xs text-primary">auto</span>
                )}
              </p>
              <p className="text-2xs text-ink-muted">
                {formatDateTime(entry.at, locale)}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </Panel>
  )
}
