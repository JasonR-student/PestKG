import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { AppShell } from './layout/AppShell'
import { LoadingState } from '../shared/ui/QueryState'
import { ReleaseProvider } from './release/ReleaseProvider'

const OverviewPage = lazy(() =>
  import('../features/overview/OverviewPage').then((module) => ({ default: module.OverviewPage })),
)
const ExplorePage = lazy(() =>
  import('../features/explore/ExplorePage').then((module) => ({ default: module.ExplorePage })),
)
const ComparePage = lazy(() =>
  import('../features/compare/ComparePage').then((module) => ({ default: module.ComparePage })),
)
const EntityPage = lazy(() =>
  import('../features/entity/EntityPage').then((module) => ({ default: module.EntityPage })),
)
const DownloadsPage = lazy(() =>
  import('../features/downloads/DownloadsPage').then((module) => ({ default: module.DownloadsPage })),
)
const MethodsPage = lazy(() =>
  import('../features/methods/MethodsPage').then((module) => ({ default: module.MethodsPage })),
)

export default function App() {
  return (
    <ReleaseProvider>
      <AppShell>
        <Suspense fallback={<LoadingState />}>
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/entity/:nodeId" element={<EntityPage />} />
            <Route path="/downloads" element={<DownloadsPage />} />
            <Route path="/methods" element={<MethodsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </AppShell>
    </ReleaseProvider>
  )
}
