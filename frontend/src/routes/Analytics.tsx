import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { EmptyState, Panel, Select, Skeleton, cx } from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import { percent } from '@/lib/format'
import type { Overview } from '@/lib/types'

interface CategoryRow {
  category: string
  count: number
  avg_priority: number
  breached: number
  avg_confidence: number
}
interface VolumeRow {
  date: string
  count: number
  breached: number
}
interface AgentRow {
  agent_id: string
  name: string
  total: number
  resolved: number
  open: number
  breached: number
  satisfaction: number | null
}

const AXIS = {
  stroke: 'var(--ink-muted)',
  fontSize: 11,
  tickLine: false,
  axisLine: false,
}

export function Analytics() {
  const { t } = useT()
  const [days, setDays] = useState(30)

  const overview = useQuery({
    queryKey: ['overview', days],
    queryFn: () => api.get<Overview>('/analytics/overview', { days }),
  })
  const categories = useQuery({
    queryKey: ['analytics-category', days],
    queryFn: () => api.get<CategoryRow[]>('/analytics/by-category', { days }),
  })
  const volume = useQuery({
    queryKey: ['analytics-volume', days],
    queryFn: () => api.get<VolumeRow[]>('/analytics/volume', { days }),
  })
  const agents = useQuery({
    queryKey: ['analytics-agents', days],
    queryFn: () => api.get<AgentRow[]>('/analytics/agents', { days }),
    retry: false,
  })

  const empty = overview.data?.total === 0

  return (
    <div className="flex flex-col gap-5 p-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">{t('analytics.title')}</h1>
        <Select
          aria-label={t('analytics.window')}
          value={days}
          onChange={(event) => setDays(Number(event.target.value))}
          className="w-auto"
        >
          {[7, 30, 90, 365].map((option) => (
            <option key={option} value={option}>
              {option} {t('analytics.days')}
            </option>
          ))}
        </Select>
      </header>

      {overview.isLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(180px,1fr))]">
          <Stat label={t('analytics.total')} value={String(overview.data?.total ?? 0)} />
          <Stat label={t('analytics.open')} value={String(overview.data?.open ?? 0)} />
          <Stat
            label={t('analytics.compliance')}
            value={percent(overview.data?.sla.compliance_rate, 1)}
            tone={
              (overview.data?.sla.compliance_rate ?? 1) < 0.9 ? 'danger' : 'success'
            }
            hint={`${overview.data?.sla.breached ?? 0} ${t('supervision.breached').toLowerCase()}`}
          />
          <Stat
            label={t('analytics.avgResolution')}
            value={
              overview.data?.avg_resolution_hours
                ? `${overview.data.avg_resolution_hours} ${t('analytics.hours')}`
                : '—'
            }
            hint={`${overview.data?.resolved_count ?? 0} resolues`}
          />
          <Stat
            label={t('analytics.satisfaction')}
            value={
              overview.data?.satisfaction.average
                ? `${overview.data.satisfaction.average} / 5`
                : '—'
            }
            hint={`${overview.data?.satisfaction.responses ?? 0} reponses`}
          />
        </div>
      )}

      {empty ? (
        <Panel>
          <EmptyState title={t('analytics.noData')} help={t('analytics.noDataHelp')} />
        </Panel>
      ) : (
        <>
          <Panel title={t('analytics.volume')}>
            {volume.isLoading ? (
              <Skeleton className="h-56 w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={volume.data ?? []}>
                  <CartesianGrid stroke="var(--line)" vertical={false} />
                  <XAxis dataKey="date" {...AXIS} />
                  <YAxis allowDecimals={false} width={28} {...AXIS} />
                  <Tooltip content={<ChartTooltip />} />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="var(--primary)"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="breached"
                    stroke="var(--danger)"
                    strokeWidth={1.5}
                    strokeDasharray="4 3"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Panel>

          <div className="grid gap-5 xl:grid-cols-2">
            <Panel title={t('analytics.byCategory')}>
              {categories.isLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={(categories.data ?? []).map((row) => ({
                      ...row,
                      label: t(`category.${row.category}` as never),
                    }))}
                    layout="vertical"
                    margin={{ left: 8 }}
                  >
                    <CartesianGrid stroke="var(--line)" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} {...AXIS} />
                    <YAxis
                      type="category"
                      dataKey="label"
                      width={140}
                      {...AXIS}
                    />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--surface-2)' }} />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                      {(categories.data ?? []).map((row) => (
                        <Cell
                          key={row.category}
                          // Breaches are the only thing that changes the colour:
                          // eleven category hues would be decoration.
                          fill={row.breached > 0 ? 'var(--danger)' : 'var(--primary)'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Panel>

            <Panel title={t('analytics.agents')} bodyClassName="p-0">
              {agents.isError ? (
                <EmptyState title="Reserve aux superviseurs" />
              ) : agents.isLoading ? (
                <div className="p-4">
                  <Skeleton className="h-56 w-full" />
                </div>
              ) : !agents.data?.length ? (
                <EmptyState
                  title="Aucune affectation sur la periode"
                  help="Les reclamations affectees a un agent apparaissent ici avec leur charge et leur taux de depassement."
                />
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-line text-2xs tracking-wide text-ink-muted uppercase">
                      <th className="px-4 py-2 text-start font-medium">Agent</th>
                      <th className="px-3 py-2 text-end font-medium">Total</th>
                      <th className="px-3 py-2 text-end font-medium">En cours</th>
                      <th className="px-4 py-2 text-end font-medium">SLA</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {agents.data.map((agent) => (
                      <tr key={agent.agent_id}>
                        <td className="px-4 py-2.5">{agent.name}</td>
                        <td className="px-3 py-2.5 text-end tabular">{agent.total}</td>
                        <td className="px-3 py-2.5 text-end tabular">{agent.open}</td>
                        <td
                          className={cx(
                            'px-4 py-2.5 text-end tabular',
                            agent.breached > 0 && 'font-semibold text-danger',
                          )}
                        >
                          {agent.breached}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Panel>
          </div>
        </>
      )}
    </div>
  )
}

function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string
  value: string
  hint?: string
  tone?: 'danger' | 'success'
}) {
  return (
    <div className="flex flex-col gap-0.5 rounded-[var(--radius-panel)] border border-line bg-surface p-4">
      <span className="text-2xs tracking-wide text-ink-muted uppercase">{label}</span>
      <span
        className={cx(
          'text-xl font-semibold tabular',
          tone === 'danger' && 'text-danger',
          tone === 'success' && 'text-success',
        )}
      >
        {value}
      </span>
      {hint && <span className="text-2xs text-ink-muted">{hint}</span>}
    </div>
  )
}

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { name: string; value: number; color: string }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-[var(--radius-control)] border border-line bg-surface px-2.5 py-2 text-2xs shadow-[var(--shadow-panel)]">
      {label && <p className="mb-1 font-medium">{label}</p>}
      {payload.map((entry) => (
        <p key={entry.name} className="flex items-center gap-1.5 tabular">
          <span
            aria-hidden
            className="size-2 rounded-full"
            style={{ background: entry.color }}
          />
          {entry.name} : {entry.value}
        </p>
      ))}
    </div>
  )
}
