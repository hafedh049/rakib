import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import {
  Badge,
  Button,
  Field,
  Input,
  Panel,
  Select,
  Skeleton,
  Toggle,
} from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import type { Department, Role, User } from '@/lib/types'

const ROLES: Role[] = ['agent', 'supervisor', 'admin']

const BLANK = {
  full_name: '',
  email: '',
  password: '',
  role: 'agent' as Role,
  department_id: '',
  skills: '',
  max_concurrent: 20,
}

export function AdminUsers() {
  const { t } = useT()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<typeof BLANK | null>(null)

  const users = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get<User[]>('/users'),
  })
  const departments = useQuery({
    queryKey: ['departments'],
    queryFn: () => api.get<Department[]>('/departments'),
  })

  const create = useMutation({
    mutationFn: (payload: typeof BLANK) =>
      api.post('/users', {
        ...payload,
        department_id: payload.department_id || null,
        skills: payload.skills
          .split(',')
          .map((skill) => skill.trim())
          .filter(Boolean),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['users'] })
      setDraft(null)
    },
  })

  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<User> }) =>
      api.patch(`/users/${id}`, patch),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['users'] }),
  })

  const byId = new Map(departments.data?.map((d) => [d.id, d]) ?? [])

  return (
    <div className="flex flex-col gap-5 p-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">{t('nav.users')}</h1>
        <Button variant="primary" onClick={() => setDraft({ ...BLANK })}>
          {t('common.create')}
        </Button>
      </header>

      {draft && (
        <Panel title={t('common.create')} bodyClassName="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('auth.fullName')} required>
              <Input
                value={draft.full_name}
                onChange={(event) =>
                  setDraft({ ...draft, full_name: event.target.value })
                }
              />
            </Field>
            <Field label={t('auth.email')} required>
              <Input
                type="email"
                value={draft.email}
                onChange={(event) => setDraft({ ...draft, email: event.target.value })}
              />
            </Field>
            <Field label={t('auth.password')} required hint="8 caracteres minimum">
              <Input
                type="password"
                value={draft.password}
                onChange={(event) =>
                  setDraft({ ...draft, password: event.target.value })
                }
              />
            </Field>
            <Field label="Role">
              <Select
                value={draft.role}
                onChange={(event) =>
                  setDraft({ ...draft, role: event.target.value as Role })
                }
              >
                {ROLES.map((role) => (
                  <option key={role} value={role}>
                    {role}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t('nav.departments')}>
              <Select
                value={draft.department_id}
                onChange={(event) =>
                  setDraft({ ...draft, department_id: event.target.value })
                }
              >
                <option value="">{t('common.none')}</option>
                {departments.data?.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Competences" hint="Separees par des virgules">
              <Input
                value={draft.skills}
                onChange={(event) => setDraft({ ...draft, skills: event.target.value })}
              />
            </Field>
          </div>

          {create.isError && (
            <p role="alert" className="text-xs font-medium text-danger">
              {(create.error as Error).message}
            </p>
          )}

          <div className="flex gap-2">
            <Button
              variant="primary"
              loading={create.isPending}
              onClick={() => create.mutate(draft)}
            >
              {t('common.save')}
            </Button>
            <Button onClick={() => setDraft(null)}>{t('common.cancel')}</Button>
          </div>
        </Panel>
      )}

      <Panel bodyClassName="p-0">
        {users.isLoading ? (
          <div className="p-4">
            <Skeleton className="h-64 w-full" />
          </div>
        ) : (
          <div className="scroll-thin overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-2xs tracking-wide text-ink-muted uppercase">
                  <th className="px-4 py-2 text-start font-medium">Nom</th>
                  <th className="px-3 py-2 text-start font-medium">Role</th>
                  <th className="px-3 py-2 text-start font-medium">
                    {t('nav.departments')}
                  </th>
                  <th className="px-3 py-2 text-end font-medium">Capacite</th>
                  <th className="px-4 py-2 text-end font-medium">Actif</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {users.data?.map((user) => (
                  <tr key={user.id}>
                    <td className="px-4 py-2.5">
                      <p className="font-medium">{user.full_name}</p>
                      <p className="text-2xs text-ink-muted">{user.email}</p>
                    </td>
                    <td className="px-3 py-2.5">
                      <Badge tone={user.role === 'admin' ? 'primary' : 'neutral'}>
                        {user.role}
                      </Badge>
                    </td>
                    <td className="px-3 py-2.5 text-2xs text-ink-muted">
                      {user.department_id
                        ? (byId.get(user.department_id)?.name ?? '—')
                        : '—'}
                    </td>
                    <td className="px-3 py-2.5 text-end tabular">
                      {user.max_concurrent}
                    </td>
                    <td className="px-4 py-2.5 text-end">
                      <Toggle
                        checked={user.is_active}
                        onChange={(is_active) =>
                          update.mutate({ id: user.id, patch: { is_active } })
                        }
                        label=""
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}
