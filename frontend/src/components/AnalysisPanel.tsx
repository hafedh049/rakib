import { Link } from 'react-router-dom'

import { useT } from '@/i18n'
import { percent } from '@/lib/format'
import type { Analysis, RuleHit } from '@/lib/types'

import { CategoryLabel, LanguageBadge, PriorityBadge, SentimentBadge } from './badges'
import { Badge, Button, Meter, Panel, cx } from './ui'

/**
 * The explainability surface.
 *
 * PRODUCT.md principle 1: every automated decision carries its evidence. A
 * priority badge with no visible reason is a bug, so the rule hits and the
 * tokens that fired them are the largest thing in this panel — not a footnote.
 */
export function AnalysisPanel({
  analysis,
  triageState,
  corrected,
  duplicateOf,
  related,
  onCorrect,
  correcting,
  canCorrect,
}: {
  analysis: Analysis
  triageState: string
  corrected: boolean
  duplicateOf?: { id: string; ref: string; subject: string } | null
  related?: { id: string; ref: string; subject: string }[]
  onCorrect?: (category: string) => void
  correcting?: boolean
  canCorrect: boolean
}) {
  const { t } = useT()

  if (triageState === 'pending') {
    return (
      <Panel title={t('analysis.title')}>
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">{t('analysis.pending')}</p>
          <p className="text-xs text-ink-muted">{t('analysis.pendingHelp')}</p>
          <div className="skeleton mt-2 h-24 w-full" />
        </div>
      </Panel>
    )
  }

  const confidence = analysis.category_confidence ?? 0
  const confidenceTone =
    confidence >= 0.75 ? 'success' : confidence >= 0.55 ? 'primary' : 'amber'

  // The winner is already the first alternative; offering it as a "correction"
  // to itself would be noise.
  const alternatives = analysis.category_alternatives.filter(
    ([name]) => name !== analysis.category,
  )

  return (
    <Panel
      title={t('analysis.title')}
      action={
        corrected ? (
          <Badge tone="primary">{t('analysis.corrected')}</Badge>
        ) : undefined
      }
      bodyClassName="flex flex-col gap-5"
    >
      {analysis.needs_human_triage && (
        <div className="rounded-[var(--radius-control)] border border-amber/40 bg-amber-soft px-3 py-2.5">
          <p className="text-xs font-semibold text-amber">
            {t('analysis.needsTriage')}
          </p>
          {analysis.triage_reason && (
            <p className="mt-0.5 text-2xs text-ink">
              {t(`reason.${analysis.triage_reason}` as never)}
            </p>
          )}
        </div>
      )}

      {/* ---- category + confidence ---- */}
      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-2xs tracking-wide text-ink-muted uppercase">
            {t('analysis.category')}
          </span>
          <span className="text-2xs tabular text-ink-muted">
            {percent(analysis.category_confidence, 1)}
          </span>
        </div>
        <p className="text-sm font-semibold">
          <CategoryLabel category={analysis.category} />
          {analysis.subcategory && (
            <span className="ms-2 font-normal text-ink-muted">
              · {analysis.subcategory.replaceAll('_', ' ')}
            </span>
          )}
        </p>
        <Meter
          value={confidence}
          tone={confidenceTone}
          label={t('analysis.confidence')}
        />
      </div>

      {/* ---- one-click correction ---- */}
      {canCorrect && alternatives.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-2xs tracking-wide text-ink-muted uppercase">
            {t('analysis.alternatives')}
            <span className="ms-2 normal-case">{t('analysis.alternativesHelp')}</span>
          </span>
          <div className="flex flex-wrap gap-1.5">
            {alternatives.map(([name, score]) => (
              <Button
                key={name}
                variant="secondary"
                disabled={correcting}
                onClick={() => onCorrect?.(name)}
                className="h-7"
              >
                <CategoryLabel category={name} />
                <span className="tabular text-ink-muted">
                  {percent(score, 0)}
                </span>
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* ---- priority + score ---- */}
      <div className="flex flex-wrap items-center gap-2 border-t border-line pt-4">
        <PriorityBadge priority={analysis.priority} />
        {analysis.priority_score !== null && (
          <span className="text-2xs tabular text-ink-muted">
            {t('analysis.score')} {analysis.priority_score}
          </span>
        )}
        <SentimentBadge sentiment={analysis.sentiment} />
        <LanguageBadge language={analysis.language} />
      </div>

      {/* ---- rule hits: the reason the priority is what it is ---- */}
      <div className="flex flex-col gap-2">
        <span className="text-2xs tracking-wide text-ink-muted uppercase">
          {t('analysis.rules')}
        </span>
        {analysis.rule_hits.length === 0 ? (
          <p className="text-xs text-ink-muted">{t('analysis.rulesEmpty')}</p>
        ) : (
          <ul className="flex flex-col divide-y divide-line">
            {analysis.rule_hits.map((hit) => (
              <RuleHitRow key={hit.code} hit={hit} />
            ))}
          </ul>
        )}
      </div>

      {/* ---- duplicate / related ---- */}
      {duplicateOf && (
        <div className="flex flex-col gap-1 border-t border-line pt-4">
          <span className="text-2xs tracking-wide text-ink-muted uppercase">
            {t('analysis.duplicate')}
            {analysis.duplicate_score !== null && (
              <span className="ms-2 tabular normal-case">
                {percent(analysis.duplicate_score, 0)}
              </span>
            )}
          </span>
          <Link
            to={`/inbox/${duplicateOf.id}`}
            className="text-xs text-primary underline-offset-2 hover:underline"
          >
            <span className="ltr-isolate tabular">{duplicateOf.ref}</span> ·{' '}
            {duplicateOf.subject}
          </Link>
        </div>
      )}

      {related && related.length > 0 && (
        <div className="flex flex-col gap-1 border-t border-line pt-4">
          <span className="text-2xs tracking-wide text-ink-muted uppercase">
            {t('analysis.related')}
          </span>
          <p className="text-2xs text-ink-muted">{t('analysis.relatedHelp')}</p>
          <ul className="mt-1 flex flex-col gap-1">
            {related.map((item) => (
              <li key={item.id}>
                <Link
                  to={`/inbox/${item.id}`}
                  className="text-xs text-primary underline-offset-2 hover:underline"
                >
                  <span className="ltr-isolate tabular">{item.ref}</span> ·{' '}
                  {item.subject}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ---- provenance ---- */}
      <footer className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line pt-3 text-2xs text-ink-muted">
        <span>
          {t('analysis.engine')}{' '}
          <span className="font-medium text-ink">{analysis.engine ?? '—'}</span>
        </span>
        <span>
          {t('analysis.engineVersion')}{' '}
          <span className="ltr-isolate font-medium text-ink">
            {analysis.engine_version ?? '—'}
          </span>
        </span>
        {analysis.latency_ms !== null && (
          <span className="tabular">
            {t('analysis.latency')} {analysis.latency_ms} ms
          </span>
        )}
      </footer>
    </Panel>
  )
}

function RuleHitRow({ hit }: { hit: RuleHit }) {
  const negative = hit.weight < 0
  return (
    <li className="flex items-start justify-between gap-3 py-2">
      <div className="min-w-0">
        <p className="text-xs font-medium">{hit.label}</p>
        {/* The matched tokens are the whole point: without them the weight is
            an assertion the agent has to take on faith. */}
        {hit.matched.length > 0 && (
          <p className="mt-0.5 flex flex-wrap gap-1">
            {hit.matched.slice(0, 6).map((token) => (
              <span
                key={token}
                className="rounded bg-surface-2 px-1.5 py-0.5 text-2xs text-ink-muted"
              >
                {token}
              </span>
            ))}
          </p>
        )}
      </div>
      <span
        className={cx(
          'shrink-0 text-xs font-semibold tabular',
          negative ? 'text-success' : 'text-ink',
        )}
      >
        {negative ? '' : '+'}
        {hit.weight}
      </span>
    </li>
  )
}
