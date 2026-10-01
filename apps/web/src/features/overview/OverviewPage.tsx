import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Database, ExternalLink, GitBranch, Network, Rows3 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { api } from '../../shared/api/client'
import { CoverageChart } from './components/CoverageChart'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { WorldMap } from './components/WorldMap'
import { formatCompact, formatDate, formatInteger } from '../../shared/lib/format'
import { statusLabel } from '../../shared/lib/labels'
import { jurisdictionName } from '../../shared/lib/jurisdictions'
import { useRelease } from '../../app/release/useRelease'

export function OverviewPage() {
  const { i18n, t } = useTranslation()
  const navigate = useNavigate()
  const { releaseId, buildUrl } = useRelease()
  const overview = useQuery({ queryKey: ['overview', releaseId], queryFn: ({ signal }) => api.overview(releaseId, signal), enabled: Boolean(releaseId) })
  const countries = useQuery({ queryKey: ['countries', releaseId], queryFn: ({ signal }) => api.countries(releaseId, signal), enabled: Boolean(releaseId) })

  if (overview.isLoading || countries.isLoading) return <LoadingState />
  if (overview.isError || countries.isError || !overview.data || !countries.data) {
    return <ErrorState />
  }

  const data = overview.data.data
  const countryRows = countries.data.data.toSorted((a, b) => b.nodes - a.nodes)
  const language = i18n.language
  const english = language.startsWith('en')
  const distributionBlocked = data.distribution_status !== 'ready'

  const metrics = [
    { label: t('overview.jurisdictions'), value: data.jurisdictions, icon: Database },
    { label: t('overview.officialSources'), value: data.source_records, icon: Rows3 },
    { label: t('overview.jurisdictionNodes'), value: data.country_nodes, icon: Network },
    { label: t('overview.relations'), value: data.country_edges, icon: GitBranch },
    { label: t('overview.reviewedGlobalChemicals'), value: data.shared_nodes, icon: Network },
  ]

  return (
    <div className="page-stack">
      <section className="overview-heading">
        <div>
          <h1>{t('overview.title')}</h1>
          <p>{t('overview.description')}</p>
        </div>
        <div className={distributionBlocked ? 'release-summary release-summary--blocked' : 'release-summary'}>
          <span>{data.version}</span>
          <strong>{distributionBlocked ? t('overview.distributionBlocked') : statusLabel(data.status, language)}</strong>
           <small>{t('common.sourceCutoff')} {formatDate(data.cutoff, language)}</small>
        </div>
      </section>

       <section className="metric-strip" aria-label={t('common.release')}>
        {metrics.map(({ label, value, icon: Icon }) => (
          <div className="metric-item" key={label}>
            <Icon size={17} aria-hidden="true" />
            <span>{label}</span>
            <strong title={formatInteger(value, language)}>{formatCompact(value, language)}</strong>
          </div>
        ))}
      </section>

      <section className="dashboard-grid dashboard-grid--map">
        <div className="section-panel map-panel">
          <div className="section-heading">
            <div>
              <h2>{t('overview.jurisdictionCoverage')}</h2>
              <p>{t('overview.jurisdictionCoverageDescription')}</p>
            </div>
            <span>{formatInteger(data.alignment_edges, language)} {t('overview.reviewedIdentityLinks')}</span>
          </div>
          <WorldMap
            countries={countryRows}
            onSelect={(jurisdiction) => navigate(buildUrl(`/explore?jurisdiction=${jurisdiction}`))}
          />
        </div>

        <div className="section-panel country-panel">
          <div className="section-heading">
            <div>
              <h2>{t('overview.jurisdictionGraphScale')}</h2>
              <p>{t('overview.jurisdictionGraphScaleDescription')}</p>
            </div>
          </div>
          <div className="country-ranking">
            {countryRows.map((country, index) => (
              <button
                type="button"
                key={country.jurisdiction}
                onClick={() => navigate(buildUrl(`/explore?jurisdiction=${country.jurisdiction}`))}
              >
                <span className="rank-number">{String(index + 1).padStart(2, '0')}</span>
                <span className="country-name">
                  <strong>{jurisdictionName(country.jurisdiction, english)}</strong>
                  <small>{country.jurisdiction}</small>
                </span>
                <span className="country-volume" title={formatInteger(country.nodes, language)}>{formatCompact(country.nodes, language)}</span>
                <ArrowRight size={15} aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="section-panel chart-panel">
        <div className="section-heading">
          <div>
            <h2>{t('overview.coverageTitle')}</h2>
            <p>{t('overview.coverageDescription')}</p>
          </div>
          <a href={buildUrl('/methods')}>
            {t('overview.methodDefinition')}
            <ExternalLink size={14} />
          </a>
        </div>
        <CoverageChart coverage={data.coverage} language={i18n.language} />
      </section>
    </div>
  )
}
