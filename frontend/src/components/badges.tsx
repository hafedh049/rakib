import { useT } from '@/i18n'
import type { Status } from '@/lib/types'

import { Badge } from './ui'

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
