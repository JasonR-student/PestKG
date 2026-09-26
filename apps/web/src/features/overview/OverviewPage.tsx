import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Database, ExternalLink, GitBranch, Network, Rows3 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { api } from '../../shared/api/client'
import { CoverageChart } from './components/CoverageChart'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { WorldMap } from './components/WorldMap'
import { formatCompact, formatInteger } from '../../shared/lib/format'
import { useRelease } from '../../app/release/useRelease'

export function OverviewPage() {
  const { i18n } = useTranslation()
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
  const english = i18n.language.startsWith('en')
  const distributionBlocked = data.distribution_status !== 'ready'

  const metrics = [
    { label: english ? 'Jurisdictions' : '司法辖区', value: data.jurisdictions, icon: Database },
    { label: english ? 'Source records' : '源记录', value: data.source_records, icon: Rows3 },
    { label: english ? 'Country nodes' : '国家图谱节点', value: data.country_nodes, icon: Network },
    { label: english ? 'Relations' : '登记关系', value: data.country_edges, icon: GitBranch },
    { label: english ? 'Shared semantic nodes' : '共享语义节点', value: data.shared_nodes, icon: Network },
  ]

  return (
    <div className="page-stack">
      <section className="overview-heading">
        <div>
          <h1>{english ? 'Multicountry pesticide registration knowledge graph' : '多国农药登记知识图谱'}</h1>
          <p>
            {english
              ? 'A traceable, federated research resource for cross-jurisdiction registration comparison.'
              : '面向跨司法辖区登记比较的可追溯联邦知识图谱研究资源。'}
          </p>
        </div>
        <div className={distributionBlocked ? 'release-summary release-summary--blocked' : 'release-summary'}>
          <span>{data.version}</span>
          <strong>{distributionBlocked ? (english ? 'Distribution blocked' : '暂未公开发布') : data.status.replaceAll('_', ' ')}</strong>
          <small>{english ? `Source cutoff ${data.cutoff}` : `来源截止 ${data.cutoff}`}</small>
        </div>
      </section>

      <section className="metric-strip" aria-label="Release metrics">
        {metrics.map(({ label, value, icon: Icon }) => (
          <div className="metric-item" key={label}>
            <Icon size={17} aria-hidden="true" />
            <span>{label}</span>
            <strong title={formatInteger(value)}>{formatCompact(value)}</strong>
          </div>
        ))}
      </section>

      <section className="dashboard-grid dashboard-grid--map">
        <div className="section-panel map-panel">
          <div className="section-heading">
            <div>
              <h2>{english ? 'Jurisdiction coverage' : '司法辖区覆盖'}</h2>
              <p>{english ? 'Select a country to open filtered registration uses.' : '点击国家进入对应登记使用数据。'}</p>
            </div>
            <span>{formatInteger(data.alignment_edges)} alignments</span>
          </div>
          <WorldMap
            countries={countryRows}
            onSelect={(jurisdiction) => navigate(buildUrl(`/explore?jurisdiction=${jurisdiction}`))}
          />
        </div>

        <div className="section-panel country-panel">
          <div className="section-heading">
            <div>
              <h2>{english ? 'Country graph scale' : '国家图谱规模'}</h2>
              <p>{english ? 'Independent regulatory graphs, ranked by nodes.' : '按节点量排列的独立监管图谱。'}</p>
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
                  <strong>{country.jurisdiction_name}</strong>
                  <small>{formatInteger(country.source_rows)} source records</small>
                </span>
                <span className="country-volume">{formatCompact(country.nodes)}</span>
                <ArrowRight size={15} aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="section-panel chart-panel">
        <div className="section-heading">
          <div>
            <h2>{english ? 'English completion conditional on source availability' : '基于源字段存在性的英文完成度'}</h2>
            <p>
              {english
                ? 'Missing official fields are excluded from translation-completion denominators.'
                : '官方源字段缺失不计入英文增强失败。'}
            </p>
          </div>
          <a href={buildUrl('/methods')}>
            {english ? 'Method definition' : '查看方法定义'}
            <ExternalLink size={14} />
          </a>
        </div>
        <CoverageChart coverage={data.coverage} language={i18n.language} />
      </section>
    </div>
  )
}
