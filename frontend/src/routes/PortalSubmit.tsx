import { useMutation } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { Link } from 'react-router-dom'

import { PortalLayout } from '@/components/PortalLayout'
import { Button, Field, Input, Panel, Textarea } from '@/components/ui'
import { useT } from '@/i18n'
import { ApiError, api } from '@/lib/api'

interface Created {
  id: string
  ref: string
  status: string
  tracking_url: string
  created_at: string
}

// Mirrors storage.ALLOWED_CONTENT_TYPES and MAX_ATTACHMENT_MB on the server;
// checking here too turns a 422 round trip into instant feedback.
const ACCEPTED_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/heic',
  'application/pdf',
  'text/plain',
]
const MAX_FILE_BYTES = 10 * 1024 * 1024
const MAX_FILES = 5

export function PortalSubmit() {
  const { t } = useT()
  const ids = {
    subject: useId(),
    body: useId(),
    name: useId(),
    email: useId(),
    phone: useId(),
    external: useId(),
  }

  const [form, setForm] = useState({
    subject: '',
    body: '',
    full_name: '',
    email: '',
    phone: '',
    external_id: '',
  })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [files, setFiles] = useState<File[]>([])
  const [fileError, setFileError] = useState<string | null>(null)
  const [uploadFailed, setUploadFailed] = useState(false)

  const submit = useMutation({
    mutationFn: async () => {
      const created = await api.post<Created>('/complaints', {
        subject: form.subject,
        body: form.body,
        channel: 'web',
        claimant: {
          full_name: form.full_name,
          email: form.email || null,
          phone: form.phone || null,
          external_id: form.external_id || null,
        },
      })

      // Attachments go up after creation, authorised by the tracking token the
      // API just minted — an anonymous claimant has no session to use instead.
      if (files.length) {
        const token = created.tracking_url.split('token=')[1] ?? ''
        for (const file of files) {
          const body = new FormData()
          body.append('file', file)
          try {
            await api.upload(
              `/complaints/${created.id}/attachments?token=${encodeURIComponent(token)}`,
              body,
            )
          } catch {
            // The complaint itself is already saved; a failed attachment must
            // not throw that away, so it is reported rather than raised.
            setUploadFailed(true)
          }
        }
      }
      return created
    },
    onError: (error) => {
      setFieldErrors(error instanceof ApiError ? error.fieldErrors() : {})
    },
  })

  function addFiles(selected: FileList | null) {
    if (!selected) return
    setFileError(null)
    const accepted: File[] = []
    for (const file of Array.from(selected)) {
      if (file.size > MAX_FILE_BYTES) {
        setFileError(t('portal.attachmentTooBig'))
        continue
      }
      if (!ACCEPTED_TYPES.includes(file.type)) {
        setFileError(t('portal.attachmentBadType'))
        continue
      }
      accepted.push(file)
    }
    setFiles((current) => [...current, ...accepted].slice(0, MAX_FILES))
  }

  if (submit.isSuccess) {
    return (
      <Confirmation
        created={submit.data}
        uploadFailed={uploadFailed}
        onReset={() => {
          submit.reset()
          setFiles([])
          setUploadFailed(false)
        }}
      />
    )
  }

  const contactMissing =
    !form.email && !form.phone && Boolean(fieldErrors.claimant || fieldErrors[''])

  return (
    <PortalLayout>
      <div className="anim-in flex flex-col gap-8">
        <header className="flex flex-col gap-2">
          <h1 className="text-2xl">{t('portal.title')}</h1>
          <p className="text-sm text-ink-muted">{t('portal.lead')}</p>
        </header>

        <form
          noValidate
          onSubmit={(event) => {
            event.preventDefault()
            setFieldErrors({})
            submit.mutate()
          }}
          className="flex flex-col gap-6"
        >
          <Field
            label={t('portal.subject')}
            hint={t('portal.subjectHint')}
            required
            htmlFor={ids.subject}
            error={fieldErrors.subject}
          >
            <Input
              id={ids.subject}
              value={form.subject}
              maxLength={200}
              required
              aria-invalid={Boolean(fieldErrors.subject)}
              onChange={(event) =>
                setForm({ ...form, subject: event.target.value })
              }
            />
          </Field>

          <Field
            label={t('portal.body')}
            hint={t('portal.bodyHint')}
            required
            htmlFor={ids.body}
            error={fieldErrors.body}
          >
            <Textarea
              id={ids.body}
              rows={7}
              value={form.body}
              maxLength={10_000}
              required
              aria-invalid={Boolean(fieldErrors.body)}
              onChange={(event) => setForm({ ...form, body: event.target.value })}
            />
          </Field>

          <div className="flex flex-col gap-6 border-t border-line pt-6">
            <Field
              label={t('portal.name')}
              required
              htmlFor={ids.name}
              error={fieldErrors['claimant.full_name']}
            >
              <Input
                id={ids.name}
                value={form.full_name}
                required
                autoComplete="name"
                onChange={(event) =>
                  setForm({ ...form, full_name: event.target.value })
                }
              />
            </Field>

            <div className="grid gap-6 sm:grid-cols-2">
              <Field
                label={t('portal.email')}
                htmlFor={ids.email}
                optional={t('portal.optional')}
                error={fieldErrors['claimant.email']}
              >
                <Input
                  id={ids.email}
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={(event) =>
                    setForm({ ...form, email: event.target.value })
                  }
                />
              </Field>

              <Field
                label={t('portal.phone')}
                htmlFor={ids.phone}
                optional={t('portal.optional')}
                error={fieldErrors['claimant.phone']}
              >
                <Input
                  id={ids.phone}
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="+216 20 145 879"
                  value={form.phone}
                  onChange={(event) =>
                    setForm({ ...form, phone: event.target.value })
                  }
                />
              </Field>
            </div>

            <p
              className={
                contactMissing
                  ? 'text-2xs font-medium text-danger'
                  : 'text-2xs text-ink-muted'
              }
              role={contactMissing ? 'alert' : undefined}
            >
              {t('portal.contactHint')}
            </p>

            <Field
              label={t('portal.externalId')}
              htmlFor={ids.external}
              optional={t('portal.optional')}
            >
              <Input
                id={ids.external}
                value={form.external_id}
                onChange={(event) =>
                  setForm({ ...form, external_id: event.target.value })
                }
              />
            </Field>

            <Field
              label={t('portal.attachments')}
              hint={t('portal.attachmentsHint')}
              optional={t('portal.optional')}
              error={fileError ?? undefined}
            >
              <div className="flex flex-col gap-2">
                <label className="inline-flex w-fit cursor-pointer items-center gap-2 rounded-[var(--radius-control)] border border-line bg-surface px-3 py-2 text-sm transition-colors duration-150 hover:bg-surface-2">
                  <svg
                    viewBox="0 0 24 24"
                    className="size-4"
                    fill="none"
                    strokeWidth="2"
                    aria-hidden
                  >
                    <path
                      d="M12 5v14M5 12h14"
                      stroke="currentColor"
                      strokeLinecap="round"
                    />
                  </svg>
                  {t('portal.addFiles')}
                  <input
                    type="file"
                    multiple
                    className="sr-only"
                    accept={ACCEPTED_TYPES.join(',')}
                    onChange={(event) => {
                      addFiles(event.target.files)
                      event.target.value = ''
                    }}
                  />
                </label>

                {files.length > 0 && (
                  <ul className="flex flex-col gap-1">
                    {files.map((file, index) => (
                      <li
                        key={`${file.name}-${index}`}
                        className="flex items-center gap-2 rounded-[var(--radius-control)] border border-line px-3 py-2 text-xs"
                      >
                        <span className="min-w-0 flex-1 truncate">{file.name}</span>
                        <span className="tabular text-ink-muted">
                          {(file.size / 1024).toFixed(0)} Ko
                        </span>
                        <button
                          type="button"
                          onClick={() =>
                            setFiles(files.filter((_, i) => i !== index))
                          }
                          className="text-ink-muted underline-offset-2 hover:text-danger hover:underline"
                        >
                          {t('portal.removeFile')}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </Field>
          </div>

          {submit.isError && !Object.keys(fieldErrors).length && (
            <p role="alert" className="text-sm font-medium text-danger">
              {(submit.error as Error).message}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-4">
            <Button
              type="submit"
              variant="primary"
              size="md"
              loading={submit.isPending}
            >
              {submit.isPending
                ? files.length
                  ? t('portal.uploading')
                  : t('portal.submitting')
                : t('portal.submit')}
            </Button>
            <Link
              to="/portal/suivi"
              className="text-xs text-ink-muted underline-offset-2 hover:text-ink hover:underline"
            >
              {t('portal.track')}
            </Link>
          </div>
        </form>
      </div>
    </PortalLayout>
  )
}

function Confirmation({
  created,
  uploadFailed,
  onReset,
}: {
  created: Created
  uploadFailed: boolean
  onReset: () => void
}) {
  const { t } = useT()
  const [copied, setCopied] = useState(false)

  return (
    <PortalLayout>
      <div className="anim-in flex flex-col gap-7">
        <div className="flex flex-col gap-2">
          <span
            aria-hidden
            className="grid size-11 place-items-center rounded-full bg-success-soft text-success"
          >
            <svg viewBox="0 0 24 24" className="size-5" fill="none" strokeWidth="2.4">
              <path
                d="m5 12.5 4.5 4.5L19 7.5"
                stroke="currentColor"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <h1 className="text-2xl">{t('portal.received')}</h1>
          <p className="text-sm text-ink-muted">{t('portal.receivedLead')}</p>
        </div>

        {uploadFailed && (
          <Panel className="border-amber/40 bg-amber-soft">
            <p className="text-xs text-ink">{t('portal.attachmentsFailed')}</p>
          </Panel>
        )}

        <Panel>
          <p className="text-2xs tracking-wide text-ink-muted uppercase">
            {t('portal.yourRef')}
          </p>
          <p className="ltr-isolate mt-1 text-xl font-semibold tabular">
            {created.ref}
          </p>
        </Panel>

        {/* A phone-only claimant never receives this by email, so it has to be
            impossible to miss here. */}
        <Panel className="border-primary/30 bg-primary-soft">
          <p className="text-sm font-semibold text-primary">
            {t('portal.keepLink')}
          </p>
          <p className="mt-1 text-xs text-ink">{t('portal.keepLinkHelp')}</p>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <code className="ltr-isolate max-w-full flex-1 truncate rounded-[var(--radius-control)] border border-line bg-bg px-2.5 py-2 text-2xs">
              {created.tracking_url}
            </code>
            <Button
              variant="secondary"
              onClick={async () => {
                await navigator.clipboard.writeText(created.tracking_url)
                setCopied(true)
                window.setTimeout(() => setCopied(false), 2000)
              }}
            >
              {copied ? t('portal.copied') : t('portal.copyLink')}
            </Button>
          </div>

          <div className="mt-3">
            <a
              href={created.tracking_url}
              className="text-xs font-medium text-primary underline-offset-2 hover:underline"
            >
              {t('portal.openTracking')}
            </a>
          </div>
        </Panel>

        <div>
          <Button variant="ghost" onClick={onReset}>
            {t('portal.newComplaint')}
          </Button>
        </div>
      </div>
    </PortalLayout>
  )
}
