import { useContext } from 'react'

import { ReleaseContext } from './release-context'

export function useRelease() {
  const context = useContext(ReleaseContext)
  if (!context) throw new Error('useRelease must be used inside ReleaseProvider')
  return context
}
