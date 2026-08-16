import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import { cx } from './ui'

/**
 * Transient notifications.
 *
 * The console updates itself from a live stream, which until now happened in
 * total silence: a complaint appeared in the queue and nothing said so. An
 * agent watching a different part of the screen simply missed it.
 *
 * Three deliberate constraints:
 *
 * - **Never used for errors that need a decision.** Those stay inline, next to
 *   the control that caused them, where they cannot be dismissed by a timer.
 * - **Assertive only when the agent acted.** A toast confirming their own click
 *   interrupts usefully; one announcing background traffic must not, so stream
 *   notices are polite and let a screen reader finish its sentence.
 * - **Capped and de-duplicated.** A burst of stream events must not become a
 *   column of identical cards covering the queue underneath.
 */

export type ToastKind = 'success' | 'info' | 'warning' | 'danger'

interface Toast {
  id: number
  kind: ToastKind
  message: string
  /** Stream notices are polite; direct results of a click are assertive. */
  assertive: boolean
}

interface ToastApi {
  /** Confirms something the agent just did. Announced assertively. */
  notify: (message: string, kind?: ToastKind) => void
  /** Reports something that happened on its own. Announced politely. */
  announce: (message: string, kind?: ToastKind) => void
}

const ToastContext = createContext<ToastApi | null>(null)

const DURATION_MS = 4500
const MAX_VISIBLE = 3

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
  }, [])

  const push = useCallback(
    (message: string, kind: ToastKind, assertive: boolean) => {
      setToasts((current) => {
        // Same message already on screen: refresh it rather than stack a copy.
        if (current.some((toast) => toast.message === message)) return current
        const id = nextId.current++
        const timer = setTimeout(() => dismiss(id), DURATION_MS)
        timers.current.set(id, timer)
        return [...current, { id, kind, message, assertive }].slice(-MAX_VISIBLE)
      })
    },
    [dismiss],
  )

  // Clear pending timers on unmount so a dismissed provider cannot set state.
  useEffect(() => {
    const pending = timers.current
    return () => {
      pending.forEach(clearTimeout)
      pending.clear()
    }
  }, [])

  const api = useMemo<ToastApi>(
    () => ({
      notify: (message, kind = 'success') => push(message, kind, true),
      announce: (message, kind = 'info') => push(message, kind, false),
    }),
    [push],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const context = useContext(ToastContext)
  // A missing provider must not crash a page; it just means no toasts.
  return context ?? { notify: () => {}, announce: () => {} }
}

const TONE: Record<ToastKind, string> = {
  success: 'border-success text-success',
  info: 'border-line text-ink',
  warning: 'border-amber text-amber',
  danger: 'border-danger text-danger',
}

function ToastViewport({
  toasts,
  onDismiss,
}: {
  toasts: Toast[]
  onDismiss: (id: number) => void
}) {
  return (
    <div
      className="pointer-events-none fixed bottom-3 end-3 z-[var(--z-toast)]
                 flex w-[min(22rem,calc(100vw-1.5rem))] flex-col gap-2"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          aria-live={toast.assertive ? 'assertive' : 'polite'}
          className={cx(
            'pointer-events-auto flex items-start gap-2 rounded-[var(--radius-panel)]',
            'border bg-surface px-3 py-2 text-sm shadow-[var(--shadow-panel)]',
            'motion-safe:animate-[toast-in_200ms_var(--ease-out-quint)]',
            TONE[toast.kind],
          )}
        >
          <span className="min-w-0 flex-1 text-ink">{toast.message}</span>
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            aria-label="Fermer"
            className="shrink-0 rounded px-1 text-ink-muted hover:text-ink"
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  )
}
