import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { Download, ExternalLink, Filter, RotateCcw, Search } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { api } from '../../shared/api/client'
import { GraphCanvas } from './components/GraphCanvas'
import { PageHeader } from '../../shared/ui/PageHeader'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { formatInteger, preferredLabel } from '../../shared/lib/format'
import { jurisdictionName } from '../../shared/lib/jurisdictions'
import { useRelease } from '../../app/release/useRelease'
import type { RegistrationUseFilters } from '../../shared/api/models'

const emptyFilters: RegistrationUseFilters = {
  jurisdictions: [],
  query: '',
  product: '',
  active_ingredient: '',
  crop: '',
  target: '',
  formulation: '',
  registration_status: '',
  pairing_status: '',
}

const PAGE_SIZE = 20

function entityList(
  items: { label_original: string; label_en: string | null }[],
  language: string,
) {
  return items.slice(0, 3).map((item) => preferredLabel(item, language)).join(' · ') || '—'
}

export function ExplorePage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { releaseId, buildUrl } = useRelease()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialJurisdiction = searchParams.get('jurisdiction')
  const [draft, setDraft] = useState<RegistrationUseFilters>({
    ...emptyFilters,
    jurisdictions: initialJurisdiction ? [initialJurisdiction] : [],
  })
  const [filters, setFilters] = useState(draft)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [depth, setDepth] = useState(1)
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string>()
  const countries = useQuery({ queryKey: ['countries', releaseId], queryFn: ({ signal }) => api.countries(releaseId, signal), enabled: Boolean(releaseId) })
  const results = useInfiniteQuery({
    queryKey: ['registration-uses', releaseId, filters],
    queryFn: ({ pageParam, signal }) => api.registrationUses(
      filters,
      pageParam,
      PAGE_SIZE,
      releaseId,
      signal,
    ),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => {
      const nextCursor = lastPage.meta?.next_cursor
      return typeof nextCursor === 'string' ? nextCursor : undefined
    },
    enabled: Boolean(releaseId),
  })
  const resultRows = useMemo(
    () => results.data?.pages.flatMap((page) => page.data) ?? [],
    [results.data],
  )
  const selected = resultRows.find((item) => item.use_id === selectedId) ?? resultRows[0] ?? null
  const graph = useQuery({
    queryKey: ['neighborhood', releaseId, selected?.use_id, depth],
    queryFn: ({ signal }) => api.neighborhood(selected!.use_id, depth, releaseId, signal),
    enabled: Boolean(releaseId && selected),
  })

  const update = (field: keyof RegistrationUseFilters, value: string | string[]) => {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  const applyFilters = () => {
    setFilters(draft)
    setSelectedId(null)
    const params = new URLSearchParams()
    if (draft.jurisdictions[0]) params.set('jurisdiction', draft.jurisdictions[0])
    if (releaseId) params.set('release', releaseId)
    setSearchParams(params)
  }

  const resetFilters = () => {
    setDraft(emptyFilters)
    setFilters(emptyFilters)
    setSelectedId(null)
    const params = new URLSearchParams()
    if (releaseId) params.set('release', releaseId)
    setSearchParams(params)
  }

  const exportRows = async () => {
    setExporting(true)
    setExportError(undefined)
    try {
      const blob = await api.exportRegistrationUses(filters, releaseId)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `registration-uses-${releaseId ?? 'active'}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      setExportError(error instanceof Error ? error.message : t('common.error'))
    } finally {
      setExporting(false)
    }
  }

  const onNodeSelect = useCallback(
    (nodeId: string) => navigate(buildUrl(`/entity/${encodeURIComponent(nodeId)}`)),
    [buildUrl, navigate],
  )

  const total = Number(results.data?.pages[0]?.meta?.total ?? 0)
  const language = i18n.language
  const english = language.startsWith('en')
  const graphData = graph.data?.data ?? { nodes: [], edges: [] }
  const countryOptions = useMemo(
    () => countries.data?.data.toSorted((a, b) => a.jurisdiction.localeCompare(b.jurisdiction)) ?? [],
    [countries.data],
  )

  return (
    <div className="page-stack">
      <PageHeader
        title={t('explore.title')}
        description={t('explore.description')}
        actions={
          <button className="button button--secondary" type="button" onClick={() => void exportRows()} disabled={exporting}>
            <Download size={16} />
            {exporting ? t('explore.exporting') : t('explore.exportFiltered')}
          </button>
        }
      />

      <section className="filter-band" aria-label={t('explore.filtersAria')}>
        <div className="filter-title">
          <Filter size={17} aria-hidden="true" />
          <strong>{t('explore.filters')}</strong>
        </div>
        <label className="field field--wide">
          <span>{t('explore.anyField')}</span>
          <div className="input-with-icon">
            <Search size={15} />
            <input value={draft.query} onChange={(event) => update('query', event.target.value)} placeholder={t('explore.anyFieldPlaceholder')} />
          </div>
        </label>
        <label className="field">
          <span>{t('explore.jurisdiction')}</span>
          <select value={draft.jurisdictions[0] ?? ''} onChange={(event) => update('jurisdictions', event.target.value ? [event.target.value] : [])}>
            <option value="">{t('common.all')}</option>
            {countryOptions.map((country) => (
              <option key={country.jurisdiction} value={country.jurisdiction}>{country.jurisdiction} · {jurisdictionName(country.jurisdiction, english)}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>{t('explore.activeIngredient')}</span>
          <input value={draft.active_ingredient} onChange={(event) => update('active_ingredient', event.target.value)} />
        </label>
        <label className="field">
          <span>{t('explore.crop')}</span>
          <input value={draft.crop} onChange={(event) => update('crop', event.target.value)} />
        </label>
        <label className="field">
          <span>{t('explore.target')}</span>
          <input value={draft.target} onChange={(event) => update('target', event.target.value)} />
        </label>
        <label className="field">
          <span>{t('explore.formulation')}</span>
          <input value={draft.formulation} onChange={(event) => update('formulation', event.target.value)} />
        </label>
        <div className="filter-actions">
          <button className="button button--primary" type="button" onClick={applyFilters}>{t('common.apply')}</button>
          <button className="button button--quiet" type="button" onClick={resetFilters}><RotateCcw size={15} />{t('common.reset')}</button>
        </div>
      </section>

      {exportError ? <ErrorState message={exportError} /> : null}

      <section className="explore-layout">
        <div className="section-panel results-panel">
          <div className="section-heading section-heading--compact">
            <div>
              <h2>{t('explore.registrationUses')}</h2>
              <p>{formatInteger(total, language)} {t('common.rows')}</p>
            </div>
          </div>
          {results.isLoading ? <LoadingState compact /> : null}
          {results.isError ? <ErrorState message={results.error.message} /> : null}
          {resultRows.length ? (
            <>
              <div className="data-table-wrap">
                <table className="data-table">
                  <thead><tr><th>{t('explore.jurisdiction')}</th><th>{t('explore.productIngredient')}</th><th>{t('explore.cropTarget')}</th><th>{t('common.source')}</th></tr></thead>
                  <tbody>
                    {resultRows.map((row) => (
                      <tr key={row.use_id} className={selected?.use_id === row.use_id ? 'is-selected' : ''} onClick={() => setSelectedId(row.use_id)}>
                        <td><span className="jurisdiction-code">{row.jurisdiction}</span></td>
                        <td><strong>{preferredLabel({ label_original: row.product_label_original, label_en: row.product_label_en }, i18n.language)}</strong><small>{entityList(row.active_ingredients, i18n.language)}</small></td>
                        <td><span>{entityList(row.crops, i18n.language)}</span><small>{entityList(row.targets, i18n.language)}</small></td>
                        <td><a href={row.source_url} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()} aria-label={t('common.officialSource')}><ExternalLink size={15} /></a></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {results.hasNextPage ? (
                <div className="results-footer">
                  <span>{formatInteger(resultRows.length, language)} / {formatInteger(total, language)}</span>
                  <button
                    className="button button--secondary"
                    type="button"
                    disabled={results.isFetchingNextPage}
                    onClick={() => void results.fetchNextPage()}
                  >
                    {results.isFetchingNextPage ? t('explore.loadingMore') : t('explore.loadMore')}
                  </button>
                </div>
              ) : null}
            </>
          ) : results.isSuccess ? <div className="empty-table">{t('common.noData')}</div> : null}
        </div>

        <div className="section-panel graph-panel">
          <div className="section-heading section-heading--compact">
            <div>
              <h2>{t('explore.localGraph')}</h2>
              <p>{selected ? selected.use_id : t('explore.selectRow')}</p>
            </div>
            <div className="segmented-control" aria-label={t('explore.graphDepth')}>
              {[1, 2].map((value) => <button key={value} type="button" className={depth === value ? 'is-active' : ''} onClick={() => setDepth(value)}>{t('explore.hop', { count: value })}</button>)}
            </div>
          </div>
          {graph.isLoading ? <LoadingState compact /> : graph.isError ? <ErrorState message={graph.error.message} /> : <GraphCanvas graph={graphData} language={i18n.language} onNodeSelect={onNodeSelect} />}
        </div>
      </section>
    </div>
  )
}
