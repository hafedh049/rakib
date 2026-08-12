import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { AppShell } from './components/AppShell'
import { Skeleton } from './components/ui'
import { useAuth } from './lib/auth'
import { SSEProvider } from './lib/sse'
import type { Role } from './lib/types'
import { Login } from './routes/Login'
import { PortalSubmit } from './routes/PortalSubmit'
import { PortalTrack } from './routes/PortalTrack'
import { Register } from './routes/Register'

// Console screens are lazy: a claimant filing a complaint on a poor mobile
// connection should never download the agent console or the charting library.
const Inbox = lazy(() => import('./routes/Inbox').then((m) => ({ default: m.Inbox })))
const ComplaintDetail = lazy(() =>
  import('./routes/ComplaintDetail').then((m) => ({ default: m.ComplaintDetail })),
)
const Supervision = lazy(() =>
  import('./routes/Supervision').then((m) => ({ default: m.Supervision })),
)
const Analytics = lazy(() =>
  import('./routes/Analytics').then((m) => ({ default: m.Analytics })),
)
const AdminRules = lazy(() =>
  import('./routes/AdminRules').then((m) => ({ default: m.AdminRules })),
)
const AdminKb = lazy(() =>
  import('./routes/AdminKb').then((m) => ({ default: m.AdminKb })),
)
const AdminMl = lazy(() =>
  import('./routes/AdminMl').then((m) => ({ default: m.AdminMl })),
)
const AdminUsers = lazy(() =>
  import('./routes/AdminUsers').then((m) => ({ default: m.AdminUsers })),
)
const AdminDepartments = lazy(() =>
  import('./routes/AdminDepartments').then((m) => ({
    default: m.AdminDepartments,
  })),
)

function RouteFallback() {
  return (
    <div className="flex flex-col gap-3 p-6">
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-64 w-full" />
    </div>
  )
}

function Protected({ minimum, children }: { minimum: Role; children: React.ReactNode }) {
  const { user, loading, can } = useAuth()
  const location = useLocation()

  if (loading) return <RouteFallback />
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  if (!can(minimum)) return <Navigate to="/inbox" replace />
  return <>{children}</>
}

export function App() {
  return (
    <SSEProvider>
      <Routes>
        {/* ---- public portal (light, FR + AR RTL) ---- */}
        <Route path="/" element={<Navigate to="/portal" replace />} />
        <Route path="/portal" element={<PortalSubmit />} />
        <Route path="/portal/suivi" element={<PortalTrack />} />
        <Route path="/portal/satisfaction" element={<PortalTrack satisfaction />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* ---- console (dense, FR) ---- */}
        <Route
          element={
            <Protected minimum="agent">
              <AppShell />
            </Protected>
          }
        >
          <Route
            path="/inbox"
            element={
              <Suspense fallback={<RouteFallback />}>
                <Inbox />
              </Suspense>
            }
          />
          <Route
            path="/inbox/:id"
            element={
              <Suspense fallback={<RouteFallback />}>
                <ComplaintDetail />
              </Suspense>
            }
          />
          <Route
            path="/supervision"
            element={
              <Suspense fallback={<RouteFallback />}>
                <Supervision />
              </Suspense>
            }
          />
          <Route
            path="/analytics"
            element={
              <Suspense fallback={<RouteFallback />}>
                <Analytics />
              </Suspense>
            }
          />
          <Route
            path="/admin/rules"
            element={
              <Protected minimum="supervisor">
                <Suspense fallback={<RouteFallback />}>
                  <AdminRules />
                </Suspense>
              </Protected>
            }
          />
          <Route
            path="/admin/kb"
            element={
              <Protected minimum="supervisor">
                <Suspense fallback={<RouteFallback />}>
                  <AdminKb />
                </Suspense>
              </Protected>
            }
          />
          <Route
            path="/admin/ml"
            element={
              <Protected minimum="supervisor">
                <Suspense fallback={<RouteFallback />}>
                  <AdminMl />
                </Suspense>
              </Protected>
            }
          />
          <Route
            path="/admin/users"
            element={
              <Protected minimum="admin">
                <Suspense fallback={<RouteFallback />}>
                  <AdminUsers />
                </Suspense>
              </Protected>
            }
          />
          <Route
            path="/admin/departments"
            element={
              <Protected minimum="admin">
                <Suspense fallback={<RouteFallback />}>
                  <AdminDepartments />
                </Suspense>
              </Protected>
            }
          />
        </Route>

        <Route path="*" element={<Navigate to="/portal" replace />} />
      </Routes>
    </SSEProvider>
  )
}
