import { useInfiniteQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import {
  CategoryLabel,
  ChannelBadge,
  StatusBadge,
} from '@/components/badges'
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Input,
  Select,
  SkeletonRows,
  Toggle,
  cx,
} from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import { formatRelative } from '@/lib/format'
import { CATEGORIES } from '@/lib/types'
import type { ComplaintListItem, Page } from '@/lib/types'


const STATUSES = [
  'new',
  'triaged',
  'assigned',
  'in_progress',
  'pending_claimant',
  'resolved',
  'closed',
  'rejected',
]

export function Inbox() {
  const { t, locale } = useT()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('q') ?? '')

  const filters = {
    q: params.get('q') ?? '',
    status: params.get('status') ?? '',
    category: params.get('category') ?? '',
    needs_human_triage: params.get('needs_human_triage') === '1',
    unassigned: params.get('unassigned') === '1',
  }
  const hasFilters = Object.values(filters).some(Boolean)

  function setFilter(key: string, value: string | boolean) {
    const next = new URLSearchParams(params)
    if (!value) next.delete(key)
    else next.set(key, value === true ? '1' : String(value))
    setParams(next, { replace: true })
  }

  const query = useInfiniteQuery({
    queryKey: ['complaints', filters],
    initialPageParam: '' as string,
    queryFn: ({ pageParam }) =>
      api.get<Page<ComplaintListItem>>('/complaints', {
        q: filters.q || undefined,
        status: filters.status || undefined,
        category: filters.category || undefined,
        needs_human_triage: filters.needs_human_triage || undefined,
        unassigned: filters.unassigned || undefined,
        cursor: pageParam || undefined,
        limit: 25,
      }),
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  })

  const items = query.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <div className="flex flex-col">
      <header className="sticky top-0 z-[var(--z-sticky)] flex flex-col gap-3 border-b border-line bg-bg/90 px-5 py-4 backdrop-blur-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-lg font-semibold">{t('inbox.title')}</h1>
          {items.length > 0 && (
            <span className="text-xs tabular text-ink-muted">
              {items.length} {t('inbox.count')}
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <form
            onSubmit={(event) => {
              event.preventDefault()
              setFilter('q', search)
            }}
            className="flex min-w-52 flex-1 items-center gap-2"
          >
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={t('inbox.searchPlaceholder')}
              aria-label={t('inbox.search')}
              className="h-9"
            />
          </form>

          <Select
            aria-label={t('inbox.status')}
            value={filters.status}
            onChange={(event) => setFilter('status', event.target.value)}
          >
            <option value="">{t('inbox.status')} — {t('inbox.all')}</option>
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {t(`status.${status}` as never)}
              </option>
            ))}
          </Select>

          <Select
            aria-label={t('inbox.category')}
            value={filters.category}
            onChange={(event) => setFilter('category', event.target.value)}
          >
            <option value="">{t('inbox.category')} — {t('inbox.all')}</option>
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {t(`category.${category}` as never)}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex flex-wrap items-center gap-1">
          <Toggle
            checked={filters.needs_human_triage}
            onChange={(value) => setFilter('needs_human_triage', value)}
            label={t('inbox.onlyTriage')}
          />
          <Toggle
            checked={filters.unassigned}
            onChange={(value) => setFilter('unassigned', value)}
            label={t('inbox.onlyUnassigned')}
          />
          {hasFilters && (
            <Button
              variant="ghost"
              onClick={() => {
                setSearch('')
                setParams(new URLSearchParams(), { replace: true })
              }}
            >
              {t('inbox.clear')}
            </Button>
          )}
        </div>
      </header>

      {query.isLoading ? (
        <SkeletonRows rows={8} />
      ) : query.isError ? (
        <ErrorState
          message={t('common.error')}
          retryLabel={t('common.retry')}
          onRetry={() => query.refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title={hasFilters ? t('inbox.emptyFiltered') : t('inbox.empty')}
          help={t('inbox.emptyHelp')}
          action={
            hasFilters ? (
              <Button onClick={() => setParams(new URLSearchParams())}>
                {t('inbox.clear')}
              </Button>
            ) : undefined
          }
        />
      ) : (
        <>
          <ul className="divide-y divide-line">
            {items.map((item) => (
              <li key={item.id} className="anim-row">
                <Row item={item} locale={locale} />
              </li>
            ))}
          </ul>

          {query.hasNextPage && (
            <div className="flex justify-center p-5">
              <Button
                onClick={() => query.fetchNextPage()}
                loading={query.isFetchingNextPage}
              >
                {t('inbox.loadMore')}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function Row({
  item,
  locale,
}: {
  item: ComplaintListItem
  locale: 'fr' | 'ar'
}) {
  const { t } = useT()
  const attention =
    item.analysis.needs_human_triage || item.triage_state === 'failed'

  return (
    <Link
      to={`/inbox/${item.id}`}
      className={cx(
        'flex flex-col gap-2 px-5 py-3.5 transition-colors duration-150 hover:bg-surface',
        attention && 'border-s-2 border-s-transparent bg-amber-soft/25',
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="ltr-isolate text-xs tabular text-ink-muted">
          {item.ref}
        </span>
        <span className="min-w-0 flex-1 truncate text-sm font-medium">
          {item.subject}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-2xs text-ink-muted">
        <StatusBadge status={item.status} />
        <ChannelBadge channel={item.channel} />
        <span>
          <CategoryLabel category={item.analysis.category} />
        </span>
        <span>·</span>
        <span className="truncate">{item.claimant.full_name}</span>
        {item.claimant.is_vip && <Badge tone="primary">VIP</Badge>}
        {attention && <Badge tone="amber">{t('inbox.onlyTriage')}</Badge>}
        <span className="ms-auto">{formatRelative(item.created_at, locale)}</span>
      </div>
    </Link>
  )
}
