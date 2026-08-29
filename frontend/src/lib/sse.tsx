import { useQueryClient } from '@tanstack/react-query'
import { createContext, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'

import { useToast, type ToastKind } from '../components/Toasts'
import { API_BASE, getAccessToken } from './api'
import { useAuth } from './auth'

/**
 * One event stream for the whole console.
 *
 * Built on fetch + a stream reader rather than EventSource, because EventSource
 * cannot send headers — the token would have to go in the query string, and
 * from there into every nginx access log. This keeps it in Authorization.
 *
 * Incoming events invalidate query keys rather than patching caches by hand:
 * the server is the authority on what a complaint now looks like, and merging
 * partial event payloads into a list would drift. No polling anywhere.
 */

interface SSEValue {
  connected: boolean
  lastEvent: string | null
}

const SSEContext = createContext<SSEValue>({ connected: false, lastEvent: null })

const INVALIDATES: Record<string, string[]> = {
  'complaint.created': ['complaints'],
  'complaint.triaged': ['complaints', 'complaint'],
  'complaint.assigned': ['complaints', 'complaint'],
  'complaint.updated': ['complaints', 'complaint'],
  'complaint.replied': ['complaint'],
  'complaint.resolved': ['complaints', 'complaint'],
  'triage.corrected': ['complaints', 'complaint'],
}

/**
 * Stream events worth interrupting an agent for, and how they read.
 *
 * Deliberately not every event: the queue already refreshes itself, so a toast
 * per arrival would be noise. Only the two that change what someone should do
 * next — a deadline about to expire, and one already missed — plus escalation.
 */
const ANNOUNCE: Record<string, { message: string; kind: ToastKind }> = {
  'complaint.created': { message: 'Nouvelle réclamation reçue', kind: 'info' },
}

const RECONNECT_MIN_MS = 1_000
const RECONNECT_MAX_MS = 30_000

export function SSEProvider({ children }: { children: ReactNode }) {
  const { isStaff } = useAuth()
  const { announce } = useToast()
  const queryClient = useQueryClient()
  const [connected, setConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState<string | null>(null)
  const backoffRef = useRef(RECONNECT_MIN_MS)

  useEffect(() => {
    if (!isStaff) return

    const controller = new AbortController()
    let stopped = false
    let timer: number | undefined

    async function consume() {
      const token = getAccessToken()
      if (!token) return

      const response = await fetch(`${API_BASE}/events/stream`, {
        headers: { Authorization: `Bearer ${token}`, Accept: 'text/event-stream' },
        signal: controller.signal,
      })
      if (!response.ok || !response.body) throw new Error('stream refused')

      setConnected(true)
      backoffRef.current = RECONNECT_MIN_MS

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (!stopped) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // Frames are separated by a blank line; keep any partial tail.
        const frames = buffer.split('\n\n')
        buffer = frames.pop() ?? ''

        for (const frame of frames) {
          const name = frame
            .split('\n')
            .find((line) => line.startsWith('event: '))
            ?.slice(7)
            .trim()
          if (!name) continue // heartbeat or comment

          setLastEvent(name)
          const notice = ANNOUNCE[name]
          if (notice) announce(notice.message, notice.kind)
          for (const key of INVALIDATES[name] ?? []) {
            void queryClient.invalidateQueries({ queryKey: [key] })
          }
        }
      }
    }

    function run() {
      consume().catch(() => {
        if (stopped) return
        setConnected(false)
        // Exponential backoff: a restarting API must not be hammered by every
        // open console tab at once.
        timer = window.setTimeout(run, backoffRef.current)
        backoffRef.current = Math.min(backoffRef.current * 2, RECONNECT_MAX_MS)
      })
    }

    run()

    return () => {
      stopped = true
      controller.abort()
      if (timer) window.clearTimeout(timer)
      setConnected(false)
    }
  }, [isStaff, queryClient, announce])

  return (
    <SSEContext.Provider value={{ connected, lastEvent }}>
      {children}
    </SSEContext.Provider>
  )
}

export const useSSE = () => useContext(SSEContext)
