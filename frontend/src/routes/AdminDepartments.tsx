import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { Badge, Input, Panel, Select, Skeleton } from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import type { Department, User } from '@/lib/types'

export function AdminDepartments() {
  const { t } = useT()
  const queryClient = useQueryClient()

  const departments = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get<Department[]>('/departments'),
  })
  const supervisors = useQuery({
    queryKey: ['users', 'supervisors'],
    queryFn: () => api.get<User[]>('/users', { role: 'supervisor' }),
  })

  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<Department> }) =>
      api.patch(`/departments/${id}`, patch),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ['departments'] }),
  })

  if (departments.isLoading) return <Skeleton className="m-5 h-96" />

  return (
    <div className="flex flex-col gap-5 p-5">
      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold">{t('nav.departments')}</h1>
        <p className="max-w-[70ch] text-sm text-ink-muted">
          Les mots-cles servent au routage quand aucun modele n est charge. Le
          contact d escalade recoit les alertes de depassement de delai.
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

            <label className="flex flex-col gap-1 text-2xs text-ink-muted">
              Contact d escalade
              <Select
                value={department.escalation_to ?? ''}
                onChange={(event) =>
                  update.mutate({
                    id: department.id,
                    patch: {
                      escalation_to: event.target.value || null,
                    } as Partial<Department>,
                  })
                }
              >
                <option value="">{t('common.none')}</option>
                {supervisors.data?.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </Select>
            </label>

            <label className="flex flex-col gap-1 text-2xs text-ink-muted">
              Delai specifique (heures) — vide = delai par priorite
              <Input
                type="number"
                min={1}
                className="h-9"
                defaultValue={department.default_sla_hours ?? ''}
                onBlur={(event) => {
                  const raw = event.target.value
                  const hours = raw ? Number(raw) : null
                  if (hours !== department.default_sla_hours) {
                    update.mutate({
                      id: department.id,
                      patch: { default_sla_hours: hours } as Partial<Department>,
                    })
                  }
                }}
              />
            </label>

            <details className="text-2xs text-ink-muted">
              <summary className="cursor-pointer select-none">
                {department.keywords.length} mots-cles de routage
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
