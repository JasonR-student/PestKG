import { useQuery } from '@tanstack/react-query'
import {
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { api } from '../../shared/api/client'
import { ReleaseContext } from './release-context'

function pathWithRelease(path: string, releaseId: string | null) {
  const [pathname, rawSearch = ''] = path.split('?')
  const params = new URLSearchParams(rawSearch)
  if (releaseId) params.set('release', releaseId)
  const search = params.toString()
  return search ? `${pathname}?${search}` : pathname
}

export function ReleaseProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const releasesQuery = useQuery({
    queryKey: ['releases'],
    queryFn: ({ signal }) => api.releases(signal),
  })
  const releases = useMemo(() => releasesQuery.data?.data ?? [], [releasesQuery.data])
  const requestedRelease = new URLSearchParams(location.search).get('release')
  const storedRelease = window.localStorage.getItem('pestkg-release')
  const validStoredRelease = releases.some((item) => item.release_id === storedRelease)
    ? storedRelease
    : null
  const fallbackRelease = releases.find((item) => item.is_active)?.release_id ?? releases[0]?.release_id
  const releaseId = requestedRelease || validStoredRelease || fallbackRelease || null
  const release = releases.find((item) => item.release_id === releaseId) ?? null

  useEffect(() => {
    if (!releaseId || requestedRelease === releaseId) return
    const params = new URLSearchParams(location.search)
    params.set('release', releaseId)
    navigate({ pathname: location.pathname, search: params.toString() }, { replace: true })
  }, [location.pathname, location.search, navigate, releaseId, requestedRelease])

  useEffect(() => {
    if (releaseId) window.localStorage.setItem('pestkg-release', releaseId)
  }, [releaseId])

  const selectRelease = useCallback(
    (nextRelease: string) => {
      const params = new URLSearchParams(location.search)
      params.set('release', nextRelease)
      navigate({ pathname: location.pathname, search: params.toString() })
    },
    [location.pathname, location.search, navigate],
  )

  const buildUrl = useCallback(
    (path: string) => pathWithRelease(path, releaseId),
    [releaseId],
  )

  const value = useMemo(
    () => ({
      releaseId,
      release,
      releases,
      isLoading: releasesQuery.isLoading,
      isError: releasesQuery.isError,
      selectRelease,
      buildUrl,
    }),
    [buildUrl, release, releaseId, releases, releasesQuery.isError, releasesQuery.isLoading, selectRelease],
  )

  return <ReleaseContext.Provider value={value}>{children}</ReleaseContext.Provider>
}
