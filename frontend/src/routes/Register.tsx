import { useMutation } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { PortalLayout } from '@/components/PortalLayout'
import { Button, Field, Input, Panel } from '@/components/ui'
import { useT } from '@/i18n'
import { ApiError, api } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export function Register() {
  const { t } = useT()
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const ids = {
    name: useId(),
    email: useId(),
    phone: useId(),
    password: useId(),
  }

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: '',
  })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  const register = useMutation({
    mutationFn: async () => {
      await api.post('/auth/register', {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        phone: form.phone || null,
      })
      // Straight into the session: making someone type the password twice in a
      // row for no reason is friction with no security benefit.
      await signIn(form.email, form.password)
    },
    // Land on the signed-in surface, not the anonymous form: the account was
    // just created, so the very next screen should prove it exists.
    onSuccess: () => navigate('/portal/mes-reclamations'),
    onError: (caught) => {
      if (caught instanceof ApiError) {
        setFieldErrors(caught.fieldErrors())
        setError(caught.status === 409 ? caught.message : null)
      } else {
        setError(t('common.error'))
      }
    },
  })

  return (
    <PortalLayout>
      <div className="anim-in flex flex-col gap-6">
        <header className="flex flex-col gap-1.5">
          <h1 className="text-2xl">{t('auth.register')}</h1>
          <p className="text-sm text-ink-muted">{t('auth.registerLead')}</p>
        </header>

        <Panel>
          <form
            noValidate
            onSubmit={(event) => {
              event.preventDefault()
              setFieldErrors({})
              setError(null)
              register.mutate()
            }}
            className="flex flex-col gap-5"
          >
            <Field
              label={t('auth.fullName')}
              htmlFor={ids.name}
              required
              error={fieldErrors.full_name}
            >
              <Input
                id={ids.name}
                autoComplete="name"
                required
                value={form.full_name}
                onChange={(event) =>
                  setForm({ ...form, full_name: event.target.value })
                }
              />
            </Field>

            <Field
              label={t('auth.email')}
              htmlFor={ids.email}
              required
              error={fieldErrors.email}
            >
              <Input
                id={ids.email}
                type="email"
                autoComplete="username"
                required
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
              />
            </Field>

            <Field
              label={t('portal.phone')}
              htmlFor={ids.phone}
              optional={t('portal.optional')}
              error={fieldErrors.phone}
            >
              <Input
                id={ids.phone}
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                placeholder="+216 20 145 879"
                value={form.phone}
                onChange={(event) => setForm({ ...form, phone: event.target.value })}
              />
            </Field>

            <Field
              label={t('auth.password')}
              htmlFor={ids.password}
              required
              hint="8 caracteres minimum"
              error={fieldErrors.password}
            >
              <Input
                id={ids.password}
                type="password"
                autoComplete="new-password"
                minLength={8}
                required
                value={form.password}
                onChange={(event) =>
                  setForm({ ...form, password: event.target.value })
                }
              />
            </Field>

            {error && (
              <p role="alert" className="text-sm font-medium text-danger">
                {error}
              </p>
            )}

            <Button
              type="submit"
              variant="primary"
              size="md"
              loading={register.isPending}
            >
              {t('auth.register')}
            </Button>
          </form>
        </Panel>

        <div className="flex flex-wrap gap-4 text-xs text-ink-muted">
          <Link to="/login" className="underline-offset-2 hover:text-ink hover:underline">
            {t('auth.haveAccount')}
          </Link>
          <Link to="/portal" className="underline-offset-2 hover:text-ink hover:underline">
            {t('auth.backToPortal')}
          </Link>
        </div>
      </div>
    </PortalLayout>
  )
}
