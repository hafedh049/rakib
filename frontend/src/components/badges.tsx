import { useEffect, useState } from 'react'

import { useT } from '@/i18n'
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


const SENTIMENT_TONE: Record<Sentiment, 'danger' | 'amber' | 'neutral' | 'success'> = {
  angry: 'danger',
  frustrated: 'amber',
  neutral: 'neutral',
  positive: 'success',
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
