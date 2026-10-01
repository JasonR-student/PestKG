import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Download, FileArchive, FileJson2, Quote, ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { api } from '../../shared/api/client'
import { PageHeader } from '../../shared/ui/PageHeader'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { formatBytes, formatInteger } from '../../shared/lib/format'
import { formatDate } from '../../shared/lib/format'
import { artifactCategoryLabel, statusLabel } from '../../shared/lib/labels'
import { useRelease } from '../../app/release/useRelease'

export function DownloadsPage() {
  const { i18n, t } = useTranslation()
  const { releaseId, release: selectedRelease } = useRelease()
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
    ? t('downloads.showingFiles', { visible: formatInteger(visibleArtifacts.length, i18n.language), total: formatInteger(release.artifacts.length, i18n.language) })
    : t('downloads.filesAvailable', { count: formatInteger(release.artifacts.length, i18n.language) })

  return (
    <div className="page-stack">
      <PageHeader title={t('downloads.title')} description={t('downloads.description')} />
      <section className="release-band">
        <div><span>{t('downloads.currentRelease')}</span><h2 title={release.release_id}>{release.release_id}</h2><p>{release.title}</p></div>
        <dl><div><dt>{t('common.published')}</dt><dd>{formatDate(release.published_at, i18n.language)}</dd></div><div><dt>{t('common.sourceCutoff')}</dt><dd>{formatDate(release.cutoff, i18n.language)}</dd></div><div><dt>{t('common.license')}</dt><dd>{release.license}</dd></div></dl>
      </section>
      {release.distribution_status !== 'ready' ? <section className="release-warning"><AlertTriangle size={19} /><div><strong>{t('downloads.publicDistributionBlocked')}</strong><p>{t('downloads.publicDistributionBlockedDescription')}</p><small>{statusLabel(release.distribution_status, i18n.language)}</small></div></section> : null}
      <section className="section-panel artifact-panel">
        <div className="section-heading"><div><h2>{t('downloads.releaseArtifacts')}</h2><p>{t('downloads.releaseArtifactsDescription')}</p></div><div className="download-actions"><a className="button button--secondary" href={`${downloadRoot}/README.md`} target="_blank"><Download size={16} />{t('downloads.readme')}</a><a className="button button--secondary" href={`${downloadRoot}/index.json`} target="_blank"><FileJson2 size={16} />{t('downloads.index')}</a><a className="button button--secondary" href={`${downloadRoot}/SHA256SUMS`} target="_blank"><ShieldCheck size={16} />{t('downloads.sha256')}</a></div></div>
      </section>
      {release.artifacts.length ? (
        <section className="section-panel artifact-panel">
          <div className="section-heading"><div><h2>{t('downloads.directDownloads')}</h2><p>{artifactSummary}</p></div></div>
          <div className="artifact-table">
            {visibleArtifacts.map((artifact) => <div className="artifact-row direct-download-row" key={artifact.path}><FileArchive size={20} /><span><strong title={artifact.path}>{artifact.path}</strong><small>{artifactCategoryLabel(artifact.category, i18n.language)} · <code title={artifact.sha256}>{artifact.sha256.slice(0, 12)}…</code></small></span><code>{formatBytes(artifact.bytes)}</code><a className="icon-button" href={artifact.url} download title={t('downloads.downloadFile', { path: artifact.path })} aria-label={t('downloads.downloadFile', { path: artifact.path })}><Download size={16} /></a></div>)}
          </div>
        </section>
      ) : null}
      <section className="download-grid">
        <div className="section-panel citation-panel"><div className="section-heading section-heading--compact"><div><h2>{t('downloads.citation')}</h2></div><Quote size={18} /></div><pre>{`Multicountry Pesticide KG contributors (2026).\nMulticountry Pesticide Registration Knowledge Graph,\nrelease ${release.release_id}.`}</pre><p>{t('downloads.citationNote')}</p></div>
        <div className="section-panel integrity-panel"><div className="section-heading section-heading--compact"><div><h2>{t('downloads.integrityReport')}</h2></div><CheckCircle2 size={18} /></div><strong>{statusLabel(release.integrity.passed ? 'PASSED' : 'FAILED', i18n.language)}</strong><dl className="detail-list detail-list--compact"><div><dt>{t('downloads.kgNodes')}</dt><dd title={formatInteger(release.inventory.kg_nodes, i18n.language)}>{formatInteger(release.inventory.kg_nodes, i18n.language)}</dd></div><div><dt>{t('downloads.kgEdges')}</dt><dd title={formatInteger(release.inventory.kg_edges, i18n.language)}>{formatInteger(release.inventory.kg_edges, i18n.language)}</dd></div><div><dt>{t('downloads.reviewedGlobalChemicals')}</dt><dd title={formatInteger(release.inventory.global_chemicals, i18n.language)}>{formatInteger(release.inventory.global_chemicals, i18n.language)}</dd></div></dl></div>
      </section>
    </div>
  )
}
