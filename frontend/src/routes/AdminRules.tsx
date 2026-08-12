import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { PriorityBadge, SentimentBadge } from '@/components/badges'
import {
  Badge,
  Button,
  Field,
  Input,
  Meter,
  Panel,
  Skeleton,
  Textarea,
  Toggle,
  cx,
} from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import { percent } from '@/lib/format'
import { useAuth } from '@/lib/auth'
import type { Rule, SimulationResult } from '@/lib/types'

const SAMPLE =
  "C'est inacceptable ! Ma facture de janvier est de 340 dinars alors que mon " +
  'forfait est a 45 dinars. Depuis des semaines aucune reponse. Si rien ne bouge ' +
  'cette semaine je resilie et mon avocat deposera plainte.'

export function AdminRules() {
  const { t } = useT()

  return (
    <div className="flex flex-col gap-5 p-5">
      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold">{t('rules.title')}</h1>
        <p className="max-w-[70ch] text-sm text-ink-muted">{t('rules.lead')}</p>
      </header>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
        <RuleTable />
        <Simulator />
      </div>
    </div>
  )
}

function RuleTable() {
  const { t } = useT()
  const { can } = useAuth()
  const queryClient = useQueryClient()

  const rules = useQuery({
    queryKey: ['rules'],
    queryFn: () => api.get<Rule[]>('/rules'),
  })

  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<Rule> }) =>
      api.patch(`/rules/${id}`, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['rules'] })
      // The simulator must reflect the new weight immediately — that feedback
      // loop is the entire point of this screen.
      void queryClient.invalidateQueries({ queryKey: ['simulation'] })
    },
  })

  if (rules.isLoading) return <Skeleton className="h-96 w-full" />

  return (
    <Panel title={t('rules.title')} bodyClassName="p-0">
      <div className="scroll-thin overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line text-2xs tracking-wide text-ink-muted uppercase">
              <th className="px-4 py-2 text-start font-medium">Regle</th>
              <th className="px-3 py-2 text-start font-medium">{t('rules.kind')}</th>
              <th className="px-3 py-2 text-end font-medium">{t('rules.weight')}</th>
              <th className="px-4 py-2 text-end font-medium">{t('rules.active')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rules.data?.map((rule) => (
              <tr key={rule.id} className={cx(!rule.active && 'opacity-55')}>
                <td className="px-4 py-2.5">
                  <p className="font-medium">{rule.label}</p>
                  <p className="ltr-isolate text-2xs text-ink-muted">{rule.code}</p>
                </td>
                <td className="px-3 py-2.5">
                  <Badge tone="neutral">{rule.kind}</Badge>
                </td>
                <td className="px-3 py-2.5 text-end">
                  <input
                    type="number"
                    aria-label={`${t('rules.weight')} ${rule.label}`}
                    defaultValue={rule.weight}
                    disabled={!can('admin')}
                    min={-100}
                    max={100}
                    onBlur={(event) => {
                      const weight = Number(event.target.value)
                      if (weight !== rule.weight) {
                        update.mutate({ id: rule.id, patch: { weight } })
                      }
                    }}
                    className="h-8 w-16 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-end text-sm tabular disabled:opacity-60"
                  />
                </td>
                <td className="px-4 py-2.5 text-end">
                  <Toggle
                    checked={rule.active}
                    onChange={(active) =>
                      can('admin') && update.mutate({ id: rule.id, patch: { active } })
                    }
                    label=""
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

/**
 * The tuning loop, and the clearest demonstration of how priority is decided:
 * paste text, see exactly which rules fire on which tokens, change a weight,
 * run it again. Nothing is persisted.
 */
function Simulator() {
  const { t } = useT()
  const [text, setText] = useState(SAMPLE)
  const [vip, setVip] = useState(false)
  const [prior, setPrior] = useState(0)

  const run = useMutation({
    mutationFn: () =>
      api.post<SimulationResult>('/rules/simulate', {
        subject: '',
        body: text,
        claimant_is_vip: vip,
        prior_count_30d: prior,
      }),
  })

  const result = run.data

  return (
    <div className="flex flex-col gap-4">
      <Panel title={t('rules.simulator')} bodyClassName="flex flex-col gap-3">
        <p className="text-xs text-ink-muted">{t('rules.simulatorLead')}</p>

        <Textarea
          rows={6}
          value={text}
          onChange={(event) => setText(event.target.value)}
          aria-label={t('rules.simulator')}
        />

        <div className="flex flex-wrap items-end gap-3">
          <Toggle checked={vip} onChange={setVip} label={t('rules.vipContext')} />
          <div className="w-40">
            <Field label={t('rules.priorContext')} htmlFor="prior-count">
              <Input
                id="prior-count"
                type="number"
                min={0}
                max={50}
                value={prior}
                className="h-9"
                onChange={(event) => setPrior(Number(event.target.value))}
              />
            </Field>
          </div>
          <Button
            variant="primary"
            className="ms-auto"
            disabled={!text.trim()}
            loading={run.isPending}
            onClick={() => run.mutate()}
          >
            {run.isPending ? t('rules.running') : t('rules.run')}
          </Button>
        </div>
      </Panel>

      {result && (
        <Panel bodyClassName="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <PriorityBadge priority={result.priority} />
            <span className="text-xs tabular text-ink-muted">
              {t('rules.resultScore')}{' '}
              <span className="font-semibold text-ink">{result.priority_score}</span>
            </span>
            <SentimentBadge sentiment={result.sentiment} />
            <Badge tone="neutral">
              {t(`lang.${result.language}` as never)}
              <span className="ms-1 opacity-70">({result.language_source})</span>
            </Badge>
          </div>

          <Meter
            value={result.urgency_score}
            tone={result.priority <= 2 ? 'danger' : 'primary'}
            label="urgence"
          />

          {result.hits.length === 0 ? (
            <p className="text-xs text-ink-muted">{t('rules.noHits')}</p>
          ) : (
            <ul className="flex flex-col divide-y divide-line">
              {result.hits.map((hit) => (
                <li
                  key={hit.code}
                  className="flex items-start justify-between gap-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="text-xs font-medium">{hit.label}</p>
                    <p className="mt-0.5 flex flex-wrap gap-1">
                      {hit.matched.slice(0, 8).map((token) => (
                        <span
                          key={token}
                          className="rounded bg-surface-2 px-1.5 py-0.5 text-2xs text-ink-muted"
                        >
                          {token}
                        </span>
                      ))}
                    </p>
                  </div>
                  <span
                    className={cx(
                      'shrink-0 text-xs font-semibold tabular',
                      hit.weight < 0 ? 'text-success' : 'text-ink',
                    )}
                  >
                    {hit.weight < 0 ? '' : '+'}
                    {hit.weight}
                  </span>
                </li>
              ))}
            </ul>
          )}

          <details className="text-2xs text-ink-muted">
            <summary className="cursor-pointer select-none">
              {t('rules.normalized')}
            </summary>
            <p className="mt-2 rounded bg-surface-2 p-2 break-words">
              {result.normalized_text}
            </p>
            {result.transliterated && (
              <>
                <p className="mt-2 font-medium">{t('rules.transliterated')}</p>
                <p dir="rtl" className="mt-1 rounded bg-surface-2 p-2 break-words">
                  {result.transliterated}
                </p>
              </>
            )}
            <p className="mt-2 tabular">
              majuscules {percent(Number(result.features.uppercase_ratio))} · mots{' '}
              {String(result.features.word_count)}
            </p>
          </details>
        </Panel>
      )}
    </div>
  )
}
