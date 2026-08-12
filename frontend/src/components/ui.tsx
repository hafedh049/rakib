import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'

/* Shared shape vocabulary. One button, one input, one panel — used everywhere,
   so "save" never looks different on two screens. */

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(' ')
}

// ------------------------------------------------------------------- button --
type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const BUTTON_VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-primary-ink hover:bg-primary-hover active:brightness-95',
  secondary:
    'bg-surface text-ink border border-line hover:bg-surface-2 active:brightness-95',
  ghost: 'text-ink-muted hover:text-ink hover:bg-surface-2',
  danger: 'bg-danger text-white hover:brightness-110 active:brightness-95',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: 'sm' | 'md'
  loading?: boolean
  icon?: ReactNode
}

export function Button({
  variant = 'secondary',
  size = 'sm',
  loading = false,
  icon,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-[var(--radius-control)]',
        'font-medium whitespace-nowrap transition-[background-color,color,filter]',
        'duration-150 ease-[var(--ease-out-quint)]',
        'disabled:cursor-not-allowed disabled:opacity-55',
        size === 'sm' ? 'h-8 px-3 text-xs' : 'h-10 px-4 text-sm',
        BUTTON_VARIANTS[variant],
        className,
      )}
    >
      {loading ? <Spinner /> : icon}
      {children}
    </button>
  )
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
  )
}

// -------------------------------------------------------------------- panel --
export function Panel({
  title,
  action,
  children,
  className,
  bodyClassName,
}: {
  title?: ReactNode
  action?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}) {
  return (
    <section
      className={cx(
        'rounded-[var(--radius-panel)] border border-line bg-surface',
        className,
      )}
    >
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-2.5">
          <h2 className="text-xs font-semibold tracking-wide text-ink-muted uppercase">
            {title}
          </h2>
          {action}
        </header>
      )}
      <div className={cx('p-4', bodyClassName)}>{children}</div>
    </section>
  )
}

// -------------------------------------------------------------------- field --
export function Field({
  label,
  hint,
  error,
  required,
  optional,
  htmlFor,
  children,
}: {
  label: string
  hint?: string
  error?: string
  required?: boolean
  optional?: string
  htmlFor?: string
  children: ReactNode
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={htmlFor}
        className="flex items-baseline gap-2 text-sm font-medium"
      >
        {label}
        {required && (
          <span aria-hidden className="text-danger">
            *
          </span>
        )}
        {optional && (
          <span className="text-2xs font-normal text-ink-muted">{optional}</span>
        )}
      </label>
      {children}
      {/* Hint stays visible next to the error: removing guidance at the exact
          moment the user got it wrong is the wrong trade. */}
      {hint && !error && <p className="text-2xs text-ink-muted">{hint}</p>}
      {error && (
        <p role="alert" className="text-2xs font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  )
}

const CONTROL =
  'w-full rounded-[var(--radius-control)] border border-line bg-bg px-3 ' +
  'text-ink transition-colors duration-150 ' +
  'hover:border-ink-muted/50 focus:border-primary ' +
  'disabled:cursor-not-allowed disabled:opacity-60 ' +
  'aria-[invalid=true]:border-danger'

export function Input({
  className,
  ...rest
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...rest} className={cx(CONTROL, 'h-10 text-sm', className)} />
}

export function Textarea({
  className,
  ...rest
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...rest}
      className={cx(CONTROL, 'min-h-28 resize-y py-2.5 text-sm', className)}
    />
  )
}

export function Select({
  className,
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select {...rest} className={cx(CONTROL, 'h-9 pe-8 text-sm', className)}>
      {children}
    </select>
  )
}

// -------------------------------------------------------------------- badge --
type Tone = 'neutral' | 'primary' | 'amber' | 'danger' | 'success'

const TONES: Record<Tone, string> = {
  neutral: 'bg-surface-2 text-ink-muted border-line',
  primary: 'bg-primary-soft text-primary border-primary/25',
  amber: 'bg-amber-soft text-amber border-amber/30',
  danger: 'bg-danger-soft text-danger border-danger/30',
  success: 'bg-success-soft text-success border-success/30',
}

export function Badge({
  tone = 'neutral',
  children,
  icon,
  className,
  title,
}: {
  tone?: Tone
  children: ReactNode
  icon?: ReactNode
  className?: string
  title?: string
}) {
  return (
    <span
      title={title}
      className={cx(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5',
        'text-2xs font-medium whitespace-nowrap',
        TONES[tone],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  )
}

// -------------------------------------------------------------- empty/error --
export function EmptyState({
  title,
  help,
  action,
}: {
  title: string
  help?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-14 text-center">
      <p className="text-sm font-medium">{title}</p>
      {/* Empty states teach the interface rather than announcing emptiness. */}
      {help && <p className="max-w-[46ch] text-xs text-ink-muted">{help}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
  retryLabel = 'Reessayer',
}: {
  message: string
  onRetry?: () => void
  retryLabel?: string
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 px-6 py-12 text-center"
    >
      <p className="text-sm font-medium text-danger">{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx('skeleton', className)} aria-hidden />
}

export function SkeletonRows({ rows = 5 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-2 p-4" aria-label="Chargement">
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-14 w-full" />
      ))}
    </div>
  )
}

// ------------------------------------------------------------------ toggles --
export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (value: boolean) => void
  label: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cx(
        'inline-flex items-center gap-2 rounded-[var(--radius-control)] px-2 py-1',
        'text-xs transition-colors duration-150 hover:bg-surface-2',
        checked ? 'text-ink' : 'text-ink-muted',
      )}
    >
      <span
        aria-hidden
        className={cx(
          'relative h-4 w-7 rounded-full transition-colors duration-150',
          checked ? 'bg-primary' : 'bg-line',
        )}
      >
        <span
          className={cx(
            'absolute top-0.5 size-3 rounded-full bg-white transition-[inset-inline-start]',
            'duration-150 ease-[var(--ease-out-quint)]',
            checked ? 'start-3.5' : 'start-0.5',
          )}
        />
      </span>
      {label}
    </button>
  )
}

// ---------------------------------------------------------------- meter bar --
export function Meter({
  value,
  tone = 'primary',
  label,
}: {
  value: number
  tone?: Tone
  label?: string
}) {
  const clamped = Math.max(0, Math.min(1, value))
  const fill: Record<Tone, string> = {
    neutral: 'bg-ink-muted',
    primary: 'bg-primary',
    amber: 'bg-amber',
    danger: 'bg-danger',
    success: 'bg-success',
  }
  return (
    <div
      role="meter"
      aria-valuenow={Math.round(clamped * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2"
    >
      <div
        className={cx('h-full rounded-full transition-[width] duration-300', fill[tone])}
        style={{ inlineSize: `${clamped * 100}%` }}
      />
    </div>
  )
}
