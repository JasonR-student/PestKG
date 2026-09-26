import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileArchive,
  FileJson2,
  Quote,
  ShieldCheck,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { api } from '../../shared/api/client'
import { PageHeader } from '../../shared/ui/PageHeader'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { formatBytes, formatInteger } from '../../shared/lib/format'
import { useRelease } from '../../app/release/useRelease'

const inventoryRows: { key: string; name: string; detail: string; format: string }[] = [
  { key: 'canonical_entities', name: 'Canonical entities', detail: 'Deduplicated A-Line entities across the canonical model', format: 'Parquet' },
  { key: 'kg_nodes', name: 'Knowledge graph nodes', detail: 'Typed nodes in the research knowledge graph', format: 'Parquet' },
  { key: 'kg_edges', name: 'Knowledge graph edges', detail: 'Asserted relations with evidence provenance', format: 'Parquet' },
  { key: 'registrations', name: 'Registrations', detail: 'Official registration records', format: 'Parquet' },
  { key: 'registration_uses', name: 'Registration uses', detail: 'Use-level pairs with crop, target and ingredient context', format: 'Parquet' },
  { key: 'global_chemicals', name: 'Global chemicals', detail: 'Evidence-gated global identity rows', format: 'Parquet' },
]

export function DownloadsPage() {
  const { i18n } = useTranslation()
  const english = i18n.language.startsWith('en')
  const { releaseId, release: selectedRelease, buildUrl } = useRelease()
  const releases = useQuery({ queryKey: ['releases'], queryFn: ({ signal }) => api.releases(signal) })
  if (releases.isLoading) return <LoadingState />
  if (releases.isError || !releases.data) return <ErrorState />
  const release = releases.data.data.find((item) => item.release_id === releaseId)
    ?? selectedRelease
    ?? releases.data.data[0]
  if (!release) return <ErrorState />

  const inventory = (release.inventory ?? {}) as Record<string, number>
  const integrity = (release.integrity ?? {}) as { passed?: boolean; checks?: Record<string, boolean> } | undefined
  const knownLimitation = release.known_limitations?.[0] ?? release.distribution_status
  const artifacts = release.artifacts ?? []
  const visibleArtifacts = artifacts.slice(0, 24)
  const artifactSummary = artifacts.length > visibleArtifacts.length
    ? (english ? `Showing the first ${visibleArtifacts.length} of ${artifacts.length} files; the machine-readable index lists every partition.` : `这里展示全部 ${artifacts.length} 个文件中的前 ${visibleArtifacts.length} 个。`)
    : (english ? `${artifacts.length} checksummed files are available in this catalog.` : `当前目录提供 ${artifacts.length} 个带校验值的文件。`)

  return (
    <div className="page-stack">
      <PageHeader title={english ? 'Data releases and citation' : '数据发布与引用'} description={english ? 'Immutable, checksummed research artifacts are separated from the web application.' : '不可变且带校验值的研究数据包与网页应用分离发布。'} />
      <section className="release-band">
        <div><span>{english ? 'Current release' : '当前版本'}</span><h2>{release.release_id}</h2><p>{release.title}</p></div>
        <dl>
          <div><dt>{english ? 'Published' : '发布日期'}</dt><dd>{release.published_at}</dd></div>
          <div><dt>{english ? 'Source cutoff' : '来源截止'}</dt><dd>{release.cutoff}</dd></div>
          <div><dt>{english ? 'License' : '许可证'}</dt><dd>{release.license}</dd></div>
        </dl>
      </section>
      {release.distribution_status !== 'ready' ? (
        <section className="release-warning">
          <AlertTriangle size={19} />
          <div>
            <strong>{english ? 'Public distribution is blocked' : '公开分发暂未放行'}</strong>
            <p>{knownLimitation}</p>
          </div>
        </section>
      ) : null}
      <section className="section-panel artifact-panel">
        <div className="section-heading">
          <div>
            <h2>{english ? 'Release contents' : '发布内容'}</h2>
            <p>{english ? 'Served live by the release-aware Java API (DuckDB over Parquet); no external archive mount is required.' : '由版本感知的 Java API 直接读取 Parquet 提供服务，无需挂载外部归档。'}</p>
          </div>
          <div className="download-actions">
            <a className="button button--secondary" href={buildUrl('/explore')}>
              <Download size={16} />
              {english ? 'Explore registration uses' : '浏览登记使用数据'}
            </a>
          </div>
        </div>
        <div className="artifact-table">
          {inventoryRows.map(({ key, name, detail, format }) => {
            const count = Number(inventory[key] ?? 0)
            return (
              <div className="artifact-row" key={key}>
                <FileArchive size={20} />
                <span><strong>{name}</strong><small>{detail}</small></span>
                <code>{format}</code>
                <span className="artifact-status artifact-status--ready">
                  <CheckCircle2 size={14} />
                  {formatInteger(count)}
                </span>
              </div>
            )
          })}
        </div>
      </section>
      {artifacts.length ? (
        <section className="section-panel artifact-panel">
          <div className="section-heading">
            <div><h2>{english ? 'Direct downloads' : '直接下载'}</h2><p>{artifactSummary}</p></div>
          </div>
          <div className="artifact-table">
            {visibleArtifacts.map((artifact) => (
              <div className="artifact-row direct-download-row" key={artifact.path}>
                <FileArchive size={20} />
                <span><strong title={artifact.path}>{artifact.path}</strong><small>{artifact.category} · {artifact.sha256.slice(0, 12)}…</small></span>
                <code>{formatBytes(Number(artifact.bytes))}</code>
                <a className="icon-button" href={artifact.url} download title={english ? `Download ${artifact.path}` : `下载 ${artifact.path}`} aria-label={english ? `Download ${artifact.path}` : `下载 ${artifact.path}`}><Download size={16} /></a>
              </div>
            ))}
          </div>
        </section>
      ) : null}
      <section className="download-grid">
        <div className="section-panel citation-panel">
          <div className="section-heading section-heading--compact">
            <div><h2>{english ? 'Citation' : '引用信息'}</h2></div>
            <Quote size={18} />
          </div>
          <pre>{`Multicountry Pesticide KG contributors (2026).\nMulticountry Pesticide Registration Knowledge Graph,\nrelease ${release.release_id}.`}</pre>
          <p>{english ? 'The repository includes CITATION.cff; the final DOI is added after Zenodo publication.' : '仓库已包含 CITATION.cff；Zenodo 发布后补充正式 DOI。'}</p>
        </div>
        <div className="section-panel integrity-panel">
          <div className="section-heading section-heading--compact">
            <div><h2>{english ? 'Integrity report' : '完整性报告'}</h2></div>
            <ShieldCheck size={18} />
          </div>
          <strong>{integrity?.passed ? 'PASSED' : 'FAILED'}</strong>
          <dl className="detail-list detail-list--compact">
            <div><dt>Canonical entities</dt><dd>{formatInteger(Number(inventory.canonical_entities ?? 0))}</dd></div>
            <div><dt>KG nodes</dt><dd>{formatInteger(Number(inventory.kg_nodes ?? 0))}</dd></div>
            <div><dt>KG edges</dt><dd>{formatInteger(Number(inventory.kg_edges ?? 0))}</dd></div>
            <div><dt>Registration uses</dt><dd>{formatInteger(Number(inventory.registration_uses ?? 0))}</dd></div>
          </dl>
          <p className="export-note">
            <FileJson2 size={14} />
            {english
              ? 'The API exposes a filtered CSV export of registration uses.'
              : 'API 提供登记使用数据的筛选 CSV 导出。'}
          </p>
        </div>
      </section>
    </div>
  )
}
