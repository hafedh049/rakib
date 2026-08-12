import { useEffect, useState } from 'react'

import { useT } from '@/i18n'
import { countdown, slaState } from '@/lib/format'
import type { Sentiment, Status } from '@/lib/types'

import { Badge, cx } from './ui'

/* Every one of these carries a text label as well as a colour. Priority and SLA
   must be readable without colour vision — DESIGN.md treats hue as
   reinforcement, never as the signal. */

const STATUS_TONE: Record<Status, 'neutral' | 'primary' | 'success' | 'danger'> = {
  new: 'primary',
  triaged: 'primary',
  assigned: 'neutral',
  in_progress: 'neutral',
  pending_claimant: 'neutral',
  resolved: 'success',
  closed: 'neutral',
  rejected: 'danger',
}

export function StatusBadge({ status }: { status: Status }) {
  const { t } = useT()
  return <Badge tone={STATUS_TONE[status]}>{t(`status.${status}` as never)}</Badge>
}

/** Priority walks one hue from saturated danger to neutral — not a rainbow. */
export function PriorityBadge({
  priority,
  compact = false,
}: {
  priority: number | null
  compact?: boolean
}) {
  const { t } = useT()
  if (!priority) {
    return (
      <Badge tone="neutral" title="Priorite non encore determinee">
        P?
      </Badge>
    )
  }

  const styles: Record<number, string> = {
    1: 'bg-danger text-white border-danger',
    2: 'bg-danger-soft text-danger border-danger/40',
    3: 'bg-surface-2 text-ink border-line',
    4: 'bg-surface-2 text-ink-muted border-line',
  }
  const label = t(`priority.${priority}` as never)

  return (
    <span
      title={label}
      className={cx(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5',
        'text-2xs font-semibold whitespace-nowrap tabular',
        styles[priority] ?? styles[3],
      )}
    >
      P{priority}
      {!compact && <span className="font-normal">· {label}</span>}
    </span>
  )
}

/**
 * Live countdown. Ticks once a minute rather than once a second: an SLA
 * measured in hours does not need a per-second re-render on every open row.
 */
export function SLABadge({
  dueAt,
  breached,
  warned,
}: {
  dueAt: string | null
  breached: boolean
  warned: boolean
}) {
  const { t } = useT()
  const [, setTick] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => setTick((value) => value + 1), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  const state = slaState(dueAt, breached, warned)
  if (state === 'none') {
    return <Badge tone="neutral">{t('sla.none')}</Badge>
  }

  const tone = state === 'breached' ? 'danger' : state === 'warning' ? 'amber' : 'success'
  return (
    <Badge tone={tone} title={t(`sla.${state}` as never)}>
      <span className="tabular">{countdown(dueAt)}</span>
    </Badge>
  )
}

const SENTIMENT_TONE: Record<Sentiment, 'danger' | 'amber' | 'neutral' | 'success'> = {
  angry: 'danger',
  frustrated: 'amber',
  neutral: 'neutral',
  positive: 'success',
}

export function SentimentBadge({ sentiment }: { sentiment: Sentiment | null }) {
  const { t } = useT()
  if (!sentiment) return null
  return (
    <Badge tone={SENTIMENT_TONE[sentiment]}>
      {t(`sentiment.${sentiment}` as never)}
    </Badge>
  )
}

export function LanguageBadge({ language }: { language: string | null }) {
  const { t } = useT()
  if (!language) return null
  return <Badge tone="neutral">{t(`lang.${language}` as never)}</Badge>
}

export function CategoryLabel({ category }: { category: string | null }) {
  const { t } = useT()
  if (!category) return <span className="text-ink-muted">—</span>
  return <>{t(`category.${category}` as never)}</>
}

export function ChannelBadge({ channel }: { channel: string }) {
  const { t } = useT()
  return <Badge tone="neutral">{t(`channel.${channel}` as never)}</Badge>
}
