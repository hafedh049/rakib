import { useId, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { PortalLayout } from '@/components/PortalLayout'
import { Button, Field, Input, Panel } from '@/components/ui'
import { useT } from '@/i18n'
import { ApiError } from '@/lib/api'
import { useAuth } from '@/lib/auth'

export function Login() {
  const { t } = useT()
  const { user, signIn, isStaff, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const ids = { email: useId(), password: useId() }

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  // An already-authenticated visitor gets sent somewhere that shows they ARE
  // signed in. Sending a claimant back to the anonymous submission form made
  // the login link look broken, because that page gave no sign of a session.
  if (!loading && user) {
    const from = (location.state as { from?: Location } | null)?.from
    return (
      <Navigate
        to={isStaff ? (from?.pathname ?? '/inbox') : '/portal/mes-reclamations'}
        replace
      />
    )
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setPending(true)
    try {
      await signIn(email, password)
      navigate('/inbox')
    } catch (caught) {
      // The API deliberately returns the same problem for a wrong password and
      // an unknown account; the UI must not invent a distinction either.
      setError(
        caught instanceof ApiError && caught.status === 401
          ? t('auth.invalid')
          : t('common.error'),
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <PortalLayout>
      <div className="anim-in flex flex-col gap-6">
        <header className="flex flex-col gap-1.5">
          <h1 className="text-2xl">{t('auth.signIn')}</h1>
          <p className="text-sm text-ink-muted">{t('auth.signInLead')}</p>
        </header>

        <Panel>
          <form onSubmit={submit} className="flex flex-col gap-5" noValidate>
            <Field label={t('auth.email')} htmlFor={ids.email} required>
              <Input
                id={ids.email}
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>

            <Field label={t('auth.password')} htmlFor={ids.password} required>
              <Input
                id={ids.password}
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>

            {error && (
              <p role="alert" className="text-sm font-medium text-danger">
                {error}
              </p>
            )}

            <Button type="submit" variant="primary" size="md" loading={pending}>
              {pending ? t('auth.submitting') : t('auth.submit')}
            </Button>
          </form>
        </Panel>

        <div className="flex flex-wrap gap-4 text-xs text-ink-muted">
          <Link to="/register" className="underline-offset-2 hover:text-ink hover:underline">
            {t('auth.createAccount')}
          </Link>
          <Link to="/portal" className="underline-offset-2 hover:text-ink hover:underline">
            {t('auth.backToPortal')}
          </Link>
        </div>
      </div>
    </PortalLayout>
  )
}
