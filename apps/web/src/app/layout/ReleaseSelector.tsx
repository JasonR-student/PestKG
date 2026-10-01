import { Database, ShieldAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { useRelease } from '../release/useRelease'

export function ReleaseSelector() {
  const { t } = useTranslation()
  const { releaseId, release, releases, isLoading, selectRelease } = useRelease()
  const blocked = release?.distribution_status !== 'ready'

  return (
    <label className={blocked ? 'release-selector release-selector--blocked' : 'release-selector'}>
      {blocked ? <ShieldAlert size={16} aria-hidden="true" /> : <Database size={16} aria-hidden="true" />}
      <span>
        <small>{t('common.release')}</small>
        <select
          aria-label={t('common.release')}
          value={releaseId ?? ''}
          disabled={isLoading || !releases.length}
          onChange={(event) => selectRelease(event.target.value)}
        >
          {!releaseId ? <option value="">—</option> : null}
          {releases.map((item) => (
            <option key={item.release_id} value={item.release_id}>
              {item.release_id}{item.is_active ? ` · ${t('status.active')}` : ''}
            </option>
          ))}
        </select>
      </span>
    </label>
  )
}
