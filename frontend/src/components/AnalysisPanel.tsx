import { CategoryLabel, LanguageBadge } from './badges'
import { Panel, cx } from './ui'
import { useT } from '@/i18n'
import type { Analysis } from '@/lib/types'

/**
 * Why the system chose this category.
 *
 * The share is an evidence ratio, not a probability, so it is presented as a
 * proportion of the matched terms rather than as a confidence percentage. The
 * terms themselves are shown underneath: an agent who disagrees can see exactly
 * which word caused it and correct the category in one click.
 */
export function AnalysisPanel({
  analysis,
  onCorrect,
}: {
  analysis: Analysis
  onCorrect?: (category: string) => void
}) {
  const { t } = useT()

  if (!analysis.analyzed_at) {
    return (
      <Panel title={t('analysis.title')}>
        <p className="text-sm text-ink-muted">{t('analysis.pending')}</p>
      </Panel>
    )
  }

  const share = Math.round((analysis.category_confidence ?? 0) * 100)
  const firedTerms = analysis.category
    ? (analysis.evidence?.[analysis.category] ?? [])
    : []

  return (
    <Panel title={t('analysis.title')} bodyClassName="flex flex-col gap-4">
      <div>
        <div className="flex items-baseline justify-between gap-3">
          <h4 className="text-2xs font-semibold uppercase tracking-wider text-ink-faint">
            {t('analysis.category')}
          </h4>
          {analysis.category && (
            <span className="tabular text-xs text-ink-muted">{share}&nbsp;%</span>
          )}
        </div>

        {analysis.category ? (
          <>
            <p className="mt-1 font-medium">
              <CategoryLabel category={analysis.category} />
            </p>
            <div
              className="mt-2 h-1 w-full overflow-hidden rounded-full bg-surface-2"
              role="presentation"
            >
              <div
                className="h-full bg-primary"
                style={{ width: `${Math.max(share, 4)}%` }}
              />
            </div>
          </>
        ) : (
          <p className="mt-1 text-sm text-amber">
            {t('analysis.needsTriage')}
            {analysis.triage_reason && (
              <span className="ms-1 text-2xs text-ink-muted">
                ({t(`triage.${analysis.triage_reason}` as never)})
              </span>
            )}
          </p>
        )}
      </div>

      {firedTerms.length > 0 && (
        <div>
          <h4 className="text-2xs font-semibold uppercase tracking-wider text-ink-faint">
            {t('analysis.terms')}
          </h4>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {firedTerms.map((term) => (
              <span
                key={term}
                className="rounded border border-line bg-surface-2 px-1.5 py-0.5
                           text-2xs text-ink-muted"
              >
                {term}
              </span>
            ))}
          </div>
        </div>
      )}

      {analysis.category_alternatives.length > 1 && (
        <div>
          <h4 className="text-2xs font-semibold uppercase tracking-wider text-ink-faint">
            {t('analysis.alternatives')}{' '}
            {onCorrect && (
              <span className="font-normal normal-case text-ink-faint">
                {t('analysis.clickToCorrect')}
              </span>
            )}
          </h4>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {analysis.category_alternatives
              .filter(([code]) => code !== analysis.category)
              .slice(0, 3)
              .map(([code, value]) => (
                <button
                  key={code}
                  type="button"
                  disabled={!onCorrect}
                  onClick={() => onCorrect?.(code)}
                  className={cx(
                    'rounded-[var(--radius-control)] border border-line px-2 py-1 text-xs',
                    onCorrect && 'hover:border-primary hover:text-primary',
                  )}
                >
                  <CategoryLabel category={code} />
                  <span className="ms-1.5 tabular text-ink-faint">
                    {Math.round(value * 100)}&nbsp;%
                  </span>
                </button>
              ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <LanguageBadge language={analysis.language} />
        {analysis.keywords.slice(0, 5).map((word) => (
          <span key={word} className="text-2xs text-ink-muted">
            {word}
          </span>
        ))}
      </div>

      <footer
        className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line
                   pt-3 text-2xs text-ink-muted"
      >
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
            {t('analysis.latency')}{' '}
            <span className="font-medium text-ink">{analysis.latency_ms}&nbsp;ms</span>
          </span>
        )}
      </footer>
    </Panel>
  )
}
