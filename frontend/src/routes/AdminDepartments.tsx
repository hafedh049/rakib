import { useQuery } from '@tanstack/react-query'

import { Badge, Panel, Skeleton } from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import type { Department } from '@/lib/types'

/**
 * The routing catalogue, read-only.
 *
 * A department owns a set of categories and a set of keywords: the first routes
 * a complaint the classifier could name, the second catches the ones it could
 * not. Both are seeded from `domain/taxonomy.py`, which is what makes the whole
 * routing table reviewable in one file rather than spread across a database.
 */
export function AdminDepartments() {
  const { t } = useT()

  const departments = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get<Department[]>('/departments'),
  })

  if (departments.isLoading) return <Skeleton className="m-5 h-96" />

  return (
    <div className="flex flex-col gap-5 p-5">
      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold">{t('nav.departments')}</h1>
        <p className="max-w-[70ch] text-sm text-ink-muted">
          Chaque service couvre des catégories et des mots-clés. La catégorie
          route la réclamation quand elle a pu être déterminée ; les mots-clés
          prennent le relais quand elle ne l’a pas été.
        </p>
      </header>

      <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(320px,1fr))]">
        {departments.data?.map((department) => (
          <Panel
            key={department.id}
            title={department.name}
            action={
              department.active ? null : <Badge tone="neutral">inactif</Badge>
            }
            bodyClassName="flex flex-col gap-3"
          >
            <p className="ltr-isolate text-2xs text-ink-muted">{department.code}</p>
            <p className="text-xs text-ink-muted">{department.description}</p>

            <div className="flex flex-wrap gap-1">
              {department.categories.map((category) => (
                <Badge key={category} tone="primary">
                  {t(`category.${category}` as never)}
                </Badge>
              ))}
            </div>

            <details className="text-2xs text-ink-muted">
              <summary className="cursor-pointer select-none">
                {department.keywords.length} mots-clés de routage
              </summary>
              <p className="mt-2 flex flex-wrap gap-1">
                {department.keywords.map((keyword) => (
                  <span
                    key={keyword}
                    className="rounded bg-surface-2 px-1.5 py-0.5"
                  >
                    {keyword}
                  </span>
                ))}
              </p>
            </details>
          </Panel>
        ))}
      </div>
    </div>
  )
}
