import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, Fingerprint } from 'lucide-react'
import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../../shared/api/client'
import { GraphCanvas } from '../explore/components/GraphCanvas'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { formatInteger, preferredLabel } from '../../shared/lib/format'
import { fieldLabel, nodeTypeLabel } from '../../shared/lib/labels'
import { useRelease } from '../../app/release/useRelease'

export function EntityPage() {
  const { nodeId = '' } = useParams()
  const navigate = useNavigate()
  const { i18n, t } = useTranslation()
  const { releaseId, buildUrl } = useRelease()
  const entity = useQuery({
    queryKey: ['entity', releaseId, nodeId],
    queryFn: ({ signal }) => api.entity(nodeId, releaseId, signal),
    enabled: Boolean(nodeId && releaseId),
  })
  const graph = useQuery({
    queryKey: ['neighborhood', releaseId, nodeId, 1],
    queryFn: ({ signal }) => api.neighborhood(nodeId, 1, releaseId, signal),
    enabled: Boolean(nodeId && releaseId),
  })
  const onNodeSelect = useCallback(
    (selectedId: string) => navigate(buildUrl(`/entity/${encodeURIComponent(selectedId)}`)),
    [buildUrl, navigate],
  )

  if (entity.isLoading) return <LoadingState />
  if (entity.isError || !entity.data) return <ErrorState message={entity.error?.message} />
  const record = entity.data.data

  return (
    <div className="page-stack">
      <button className="back-link" type="button" onClick={() => navigate(-1)}>
        <ArrowLeft size={16} />
         {t('common.back')}
      </button>
      <section className="entity-heading">
        <div className="entity-heading-main">
          <span className="entity-symbol"><Fingerprint size={24} /></span>
          <div>
            <span className="entity-type-label">{nodeTypeLabel(record.type, i18n.language)} · {record.jurisdiction || t('entity.releaseMetadata')} <small title={record.type}>({record.type})</small></span>
            <h1>{preferredLabel(record, i18n.language)}</h1>
            {record.label_en && record.label_en !== record.label_original ? <p>{record.label_en}</p> : null}
          </div>
        </div>
        {record.source_url ? <a className="button button--secondary" href={record.source_url} target="_blank" rel="noreferrer"><ExternalLink size={16} />{t('common.officialSource')}</a> : null}
      </section>

      <section className="entity-layout">
        <div className="section-panel entity-details">
           <div className="section-heading section-heading--compact"><div><h2>{t('entity.identityAndProvenance')}</h2></div></div>
           <dl className="detail-list">
             <div><dt>{t('entity.technicalIdentifier')}</dt><dd title={record.id}>{record.id}</dd></div>
             <div><dt>{t('entity.preferredLabel')}</dt><dd>{preferredLabel(record, i18n.language)}</dd></div>
             <div><dt>{t('entity.originalLabel')}</dt><dd>{record.label_original || '—'}</dd></div>
             <div><dt>{t('entity.englishLabel')}</dt><dd>{record.label_en || '—'}</dd></div>
             <div><dt>{t('entity.jurisdiction')}</dt><dd>{record.jurisdiction || t('entity.releaseMetadata')}</dd></div>
             <div><dt>source_record_id</dt><dd>{record.source_record_id || '—'}</dd></div>
             <div><dt>{t('entity.provenanceUrl')}</dt><dd>{record.source_url || '—'}</dd></div>
           </dl>
           <div className="property-block">
             <h3>{t('entity.typedProperties')}</h3>
             {Object.keys(record.properties).length ? <dl className="detail-list detail-list--compact">{Object.entries(record.properties).map(([key, value]) => <div key={key}><dt title={key}>{fieldLabel(key, i18n.language)}</dt><dd>{String(value)}</dd></div>)}</dl> : <p>{t('entity.noAdditionalProperties')}</p>}
          </div>
        </div>
        <div className="section-panel entity-graph">
           <div className="section-heading section-heading--compact"><div><h2>{t('entity.immediateNeighborhood')}</h2><p>{graph.data ? `${formatInteger(graph.data.data.nodes.length, i18n.language)} ${t('common.nodes')} · ${formatInteger(graph.data.data.edges.length, i18n.language)} ${t('common.relations')}` : ''}</p></div></div>
          {graph.isLoading ? <LoadingState compact /> : graph.isError ? <ErrorState message={graph.error.message} /> : <GraphCanvas graph={graph.data?.data ?? { nodes: [], edges: [] }} language={i18n.language} onNodeSelect={onNodeSelect} />}
        </div>
      </section>
    </div>
  )
}
