import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import {
  Badge,
  Button,
  EmptyState,
  Field,
  Input,
  Panel,
  Select,
  Skeleton,
  Textarea,
  cx,
} from '@/components/ui'
import { useT } from '@/i18n'
import { api } from '@/lib/api'
import type { KBArticle } from '@/lib/types'

const CATEGORIES = [
  'FACTURATION',
  'PAIEMENT_RECHARGE',
  'RESEAU_MOBILE',
  'INTERNET_FIXE',
  'INTERVENTION_TECHNIQUE',
  'OFFRES_ABONNEMENT',
  'RESILIATION_PORTABILITE',
  'SERVICE_CLIENT_AGENCE',
  'EQUIPEMENT',
  'ROAMING_INTERNATIONAL',
  'APPLICATION_MOBILE',
]

const BLANK = {
  title: '',
  content: '',
  category: '',
  language: 'fr',
  template: '',
}

export function AdminKb() {
  const { t } = useT()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState<typeof BLANK | null>(null)
  const [selected, setSelected] = useState<KBArticle | null>(null)

  const articles = useQuery({
    queryKey: ['kb'],
    queryFn: () => api.get<KBArticle[]>('/kb'),
  })

  const save = useMutation({
    mutationFn: (payload: typeof BLANK & { id?: string }) => {
      const body = {
        title: payload.title,
        content: payload.content,
        category: payload.category || null,
        language: payload.language,
        template: payload.template || null,
      }
      return payload.id
        ? api.patch(`/kb/${payload.id}`, body)
        : api.post('/kb', body)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['kb'] })
      setDraft(null)
      setSelected(null)
    },
  })

  const deactivate = useMutation({
    mutationFn: (id: string) => api.delete(`/kb/${id}`),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['kb'] }),
  })

  const editing = draft ?? (selected
    ? {
        title: selected.title,
        content: selected.content,
        category: selected.category ?? '',
        language: selected.language,
        template: selected.template ?? '',
      }
    : null)

  return (
    <div className="flex flex-col gap-5 p-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold">{t('nav.kb')}</h1>
        <Button
          variant="primary"
          onClick={() => {
            setSelected(null)
            setDraft({ ...BLANK })
          }}
        >
          {t('common.create')}
        </Button>
      </header>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,28rem)]">
        <Panel bodyClassName="p-0">
          {articles.isLoading ? (
            <div className="p-4">
              <Skeleton className="h-64 w-full" />
            </div>
          ) : !articles.data?.length ? (
            <EmptyState
              title="Base de connaissance vide"
              help="Ajoutez un article avec un modele de reponse : il sera propose aux agents sur les reclamations de la meme categorie."
            />
          ) : (
            <ul className="divide-y divide-line">
              {articles.data.map((article) => (
                <li key={article.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setDraft(null)
                      setSelected(article)
                    }}
                    className={cx(
                      'flex w-full flex-col gap-1.5 px-4 py-3 text-start transition-colors',
                      'duration-150 hover:bg-surface-2',
                      selected?.id === article.id && 'bg-primary-soft',
                      !article.active && 'opacity-55',
                    )}
                  >
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="min-w-0 flex-1 truncate text-sm font-medium">
                        {article.title}
                      </span>
                      <Badge tone="neutral">
                        {t(`lang.${article.language}` as never)}
                      </Badge>
                      {article.template && <Badge tone="primary">modele</Badge>}
                    </span>
                    <span className="flex flex-wrap items-center gap-2 text-2xs text-ink-muted">
                      {article.category ? (
                        <span>{t(`category.${article.category}` as never)}</span>
                      ) : (
                        <span>generique</span>
                      )}
                      <span className="ms-auto tabular">
                        {article.usage_count} utilisations
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        {editing && (
          <Panel
            title={selected ? t('common.edit') : t('common.create')}
            bodyClassName="flex flex-col gap-4"
          >
            <Field label="Titre" required>
              <Input
                value={editing.title}
                onChange={(event) =>
                  setDraft({ ...editing, title: event.target.value })
                }
              />
            </Field>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t('inbox.category')}>
                <Select
                  value={editing.category}
                  onChange={(event) =>
                    setDraft({ ...editing, category: event.target.value })
                  }
                >
                  <option value="">generique</option>
                  {CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {t(`category.${category}` as never)}
                    </option>
                  ))}
                </Select>
              </Field>

              <Field label="Langue">
                <Select
                  value={editing.language}
                  onChange={(event) =>
                    setDraft({ ...editing, language: event.target.value })
                  }
                >
                  <option value="fr">{t('lang.fr')}</option>
                  <option value="ar">{t('lang.ar')}</option>
                </Select>
              </Field>
            </div>

            <Field label="Contenu (reference interne)" required>
              <Textarea
                rows={5}
                value={editing.content}
                onChange={(event) =>
                  setDraft({ ...editing, content: event.target.value })
                }
              />
            </Field>

            <Field
              label="Modele de reponse"
              hint="Variables entre doubles accolades : {{claimant_name}}, {{ref}}, {{category}}, {{department}}, {{sla_hours}}, {{created_at}}"
            >
              <Textarea
                rows={7}
                dir={editing.language === 'ar' ? 'rtl' : 'ltr'}
                value={editing.template}
                onChange={(event) =>
                  setDraft({ ...editing, template: event.target.value })
                }
              />
            </Field>

            {save.isError && (
              <p role="alert" className="text-xs font-medium text-danger">
                {(save.error as Error).message}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="primary"
                loading={save.isPending}
                onClick={() => save.mutate({ ...editing, id: selected?.id })}
              >
                {t('common.save')}
              </Button>
              <Button
                onClick={() => {
                  setDraft(null)
                  setSelected(null)
                }}
              >
                {t('common.cancel')}
              </Button>
              {selected?.active && (
                <Button
                  variant="danger"
                  className="ms-auto"
                  loading={deactivate.isPending}
                  onClick={() => deactivate.mutate(selected.id)}
                >
                  {t('common.delete')}
                </Button>
              )}
            </div>
          </Panel>
        )}
      </div>
    </div>
  )
}
