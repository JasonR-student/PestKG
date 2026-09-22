import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Download, FileArchive, FileJson2, FileSpreadsheet, Quote, ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { api } from '../../shared/api/client'
import { PageHeader } from '../../shared/ui/PageHeader'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { formatBytes, formatInteger } from '../../shared/lib/format'
import { useRelease } from '../../app/release/useRelease'

const artifacts = [
  { name: 'Country graph CSV.gz', detail: 'Nodes, relations and alignment edges by jurisdiction', format: 'CSV.gz', icon: FileSpreadsheet, status: 'production' },
  { name: 'Analytical tables', detail: 'Partitioned registration-use search and aggregate tables', format: 'Parquet', icon: FileArchive, status: 'production' },
  { name: 'Neo4j bulk import', detail: 'Typed nodes, relationships, indexes and validation queries', format: 'CSV.gz', icon: FileArchive, status: 'production' },
  { name: 'RDF release', detail: 'Streaming-friendly semantic graph export with relationship provenance', format: 'N-Triples.gz', icon: FileJson2, status: 'production' },
]

export function DownloadsPage() {
  const { i18n } = useTranslation()
  const { releaseId, release: selectedRelease } = useRelease()
  const english = i18n.language.startsWith('en')
  const releases = useQuery({ queryKey: ['releases'], queryFn: ({ signal }) => api.releases(signal) })
  if (releases.isLoading) return <LoadingState />
  if (releases.isError || !releases.data) return <ErrorState />
  const release = releases.data.data.find((item) => item.release_id === releaseId)
    ?? selectedRelease
    ?? releases.data.data[0]
  if (!release) return <ErrorState />
  const downloadRoot = `/downloads/${release.release_id}`
  const visibleArtifacts = release.artifacts.slice(0, 24)
  const artifactSummary = release.artifacts.length > visibleArtifacts.length
    ? (english ? `Showing the first ${visibleArtifacts.length} of ${release.artifacts.length} files; the machine-readable index lists every partition.` : `这里展示全部 ${release.artifacts.length} 个文件中的前 ${visibleArtifacts.length} 个；机器可读索引包含全部分区。`)
    : (english ? `${release.artifacts.length} checksummed files are available in this catalog.` : `当前目录提供 ${release.artifacts.length} 个带校验值的文件。`)

  return (
    <div className="page-stack">
      <PageHeader title={english ? 'Data releases and citation' : '数据发布与引用'} description={english ? 'Immutable, checksummed research artifacts are separated from the web application.' : '不可变且带校验值的研究数据包与网页应用分离发布。'} />
      <section className="release-band">
        <div><span>{english ? 'Current release' : '当前版本'}</span><h2>{release.release_id}</h2><p>{release.title}</p></div>
        <dl><div><dt>{english ? 'Published' : '发布日期'}</dt><dd>{release.published_at}</dd></div><div><dt>{english ? 'Source cutoff' : '来源截止'}</dt><dd>{release.cutoff}</dd></div><div><dt>{english ? 'License' : '许可证'}</dt><dd>{release.license}</dd></div></dl>
      </section>
      {release.distribution_status !== 'ready' ? <section className="release-warning"><AlertTriangle size={19} /><div><strong>{english ? 'Public distribution is blocked' : '公开分发暂未放行'}</strong><p>{english ? release.known_limitations[0] : '当前 RAR 的 Neo4j 与 Q1–Q5 机器数据哈希正确，但多份文本文件与顶层 SHA-256 清单不一致；必须重建归档与清单后再公开发布。'}</p></div></section> : null}
      <section className="section-panel artifact-panel">
        <div className="section-heading"><div><h2>{english ? 'Release artifacts' : '发布数据包'}</h2><p>{english ? 'The local repository exposes a real-data sample; production mounts the complete bundles.' : '本地仓库提供真实数据样例，生产服务器挂载完整数据包。'}</p></div><div className="download-actions"><a className="button button--secondary" href={`${downloadRoot}/README.md`} target="_blank"><Download size={16} />README</a><a className="button button--secondary" href={`${downloadRoot}/index.json`} target="_blank"><FileJson2 size={16} />INDEX</a><a className="button button--secondary" href={`${downloadRoot}/SHA256SUMS`} target="_blank"><ShieldCheck size={16} />SHA-256</a></div></div>
        <div className="artifact-table">
          {artifacts.map(({ name, detail, format, icon: Icon, status }) => <div className="artifact-row" key={name}><Icon size={20} /><span><strong>{name}</strong><small>{detail}</small></span><code>{format}</code><span className={status === 'production' ? 'artifact-status artifact-status--ready' : 'artifact-status'}>{status === 'production' ? <CheckCircle2 size={14} /> : null}{status === 'production' ? (english ? 'Prepared by pipeline' : '流水线已支持') : (english ? 'Next release' : '下一版本')}</span></div>)}
        </div>
      </section>
      {release.artifacts.length ? (
        <section className="section-panel artifact-panel">
          <div className="section-heading"><div><h2>{english ? 'Direct downloads' : '直接下载'}</h2><p>{artifactSummary}</p></div></div>
          <div className="artifact-table">
            {visibleArtifacts.map((artifact) => <div className="artifact-row direct-download-row" key={artifact.path}><FileArchive size={20} /><span><strong title={artifact.path}>{artifact.path}</strong><small>{artifact.category} · {artifact.sha256.slice(0, 12)}…</small></span><code>{formatBytes(artifact.bytes)}</code><a className="icon-button" href={artifact.url} download title={english ? `Download ${artifact.path}` : `下载 ${artifact.path}`} aria-label={english ? `Download ${artifact.path}` : `下载 ${artifact.path}`}><Download size={16} /></a></div>)}
          </div>
        </section>
      ) : null}
      <section className="download-grid">
        <div className="section-panel citation-panel"><div className="section-heading section-heading--compact"><div><h2>{english ? 'Citation' : '引用信息'}</h2></div><Quote size={18} /></div><pre>{`Multicountry Pesticide KG contributors (2026).\nMulticountry Pesticide Registration Knowledge Graph,\nrelease ${release.release_id}.`}</pre><p>{english ? 'The repository includes CITATION.cff; the final DOI is added after Zenodo publication.' : '仓库已包含 CITATION.cff；Zenodo 发布后补充正式 DOI。'}</p></div>
        <div className="section-panel integrity-panel"><div className="section-heading section-heading--compact"><div><h2>{english ? 'Integrity report' : '完整性报告'}</h2></div><CheckCircle2 size={18} /></div><strong>{release.integrity.passed ? 'PASSED' : 'FAILED'}</strong><dl className="detail-list detail-list--compact"><div><dt>Country nodes</dt><dd>{formatInteger(release.inventory.country_nodes)}</dd></div><div><dt>Country edges</dt><dd>{formatInteger(release.inventory.country_edges)}</dd></div><div><dt>Alignment edges</dt><dd>{formatInteger(release.inventory.alignment_edges)}</dd></div></dl></div>
      </section>
    </div>
  )
}
