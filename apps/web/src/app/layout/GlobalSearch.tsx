import { useQuery } from '@tanstack/react-query'
import { Search, X } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { api } from '../../shared/api/client'
import { preferredLabel } from '../../shared/lib/format'
import { useRelease } from '../release/useRelease'

export function GlobalSearch() {
  const { i18n } = useTranslation()
  const navigate = useNavigate()
  const { releaseId, buildUrl } = useRelease()
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query.trim())
  const result = useQuery({
    queryKey: ['global-search', releaseId, deferredQuery],
    queryFn: ({ signal }) => api.search(
      new URLSearchParams({ q: deferredQuery, limit: '8' }),
      releaseId,
      signal,
    ),
    enabled: Boolean(releaseId) && deferredQuery.length >= 2,
  })

  const selectEntity = (nodeId: string) => {
    setQuery('')
    navigate(buildUrl(`/entity/${encodeURIComponent(nodeId)}`))
  }

  return (
    <div className="global-search">
      <Search size={17} aria-hidden="true" />
      <input
        aria-label={i18n.language.startsWith('en') ? 'Search entities' : '搜索实体'}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={i18n.language.startsWith('en') ? 'Search entity or ID' : '搜索实体或 ID'}
      />
      {query ? (
        <button
          className="icon-button icon-button--quiet"
          type="button"
          aria-label={i18n.language.startsWith('en') ? 'Clear search' : '清空搜索'}
          onClick={() => setQuery('')}
        >
          <X size={15} />
        </button>
      ) : null}
      {deferredQuery.length >= 2 ? (
        <div className="search-results" role="listbox">
          {result.isLoading ? (
            <div className="search-result-note">Searching…</div>
          ) : result.data?.data.length ? (
            result.data.data.map((entity) => (
              <button
                key={entity.id}
                type="button"
                className="search-result-row"
                onClick={() => selectEntity(entity.id)}
              >
                <span>
                  <strong>{preferredLabel(entity, i18n.language)}</strong>
                  <small>{entity.id}</small>
                </span>
                <span className="entity-type">{entity.type}</span>
              </button>
            ))
          ) : (
            <div className="search-result-note">No results</div>
          )}
        </div>
      ) : null}
    </div>
  )
}
