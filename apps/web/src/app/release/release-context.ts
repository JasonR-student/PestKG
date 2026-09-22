import { createContext } from 'react'

import type { Release } from '../../shared/api/models'

export type ReleaseContextValue = {
  releaseId: string | null
  release: Release | null
  releases: Release[]
  isLoading: boolean
  isError: boolean
  selectRelease: (releaseId: string) => void
  buildUrl: (path: string) => string
}

export const ReleaseContext = createContext<ReleaseContextValue | null>(null)
