import { Database, ShieldAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { useRelease } from '../release/useRelease'

export function ReleaseSelector() {
  const { i18n } = useTranslation()
  const { releaseId, release, releases, isLoading, selectRelease } = useRelease()
  const english = i18n.language.startsWith('en')
  const blocked = release?.distribution_status !== 'ready'

  return (
    <label className={blocked ? 'release-selector release-selector--blocked' : 'release-selector'}>
      {blocked ? <ShieldAlert size={16} aria-hidden="true" /> : <Database size={16} aria-hidden="true" />}
      <span>
        <small>{english ? 'Data release' : '数据版本'}</small>
        <select
          aria-label={english ? 'Data release' : '数据版本'}
          value={releaseId ?? ''}
          disabled={isLoading || !releases.length}
          onChange={(event) => selectRelease(event.target.value)}
        >
          {!releaseId ? <option value="">—</option> : null}
          {releases.map((item) => (
            <option key={item.release_id} value={item.release_id}>
              {item.release_id}{item.is_active ? (english ? ' · active' : ' · 当前') : ''}
            </option>
          ))}
        </select>
      </span>
    </label>
  )
}
