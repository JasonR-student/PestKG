import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, Fingerprint } from 'lucide-react'
import { useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api } from '../../shared/api/client'
import { GraphCanvas } from '../explore/components/GraphCanvas'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { humanize, preferredLabel } from '../../shared/lib/format'
import { useRelease } from '../../app/release/useRelease'

export function EntityPage() {
  const { nodeId = '' } = useParams()
  const navigate = useNavigate()
  const { i18n } = useTranslation()
  const { releaseId, buildUrl } = useRelease()
  const english = i18n.language.startsWith('en')
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
        {english ? 'Back' : '返回'}
      </button>
      <section className="entity-heading">
        <div className="entity-heading-main">
          <span className="entity-symbol"><Fingerprint size={24} /></span>
          <div>
            <span className="entity-type-label">{record.type} · {record.jurisdiction || 'Shared'}</span>
            <h1>{preferredLabel(record, i18n.language)}</h1>
            {record.label_en && record.label_en !== record.label_original ? <p>{record.label_en}</p> : null}
          </div>
        </div>
        {record.source_url ? <a className="button button--secondary" href={record.source_url} target="_blank" rel="noreferrer"><ExternalLink size={16} />{english ? 'Official source' : '官方来源'}</a> : null}
      </section>

      <section className="entity-layout">
        <div className="section-panel entity-details">
          <div className="section-heading section-heading--compact"><div><h2>{english ? 'Identity and provenance' : '实体标识与来源'}</h2></div></div>
          <dl className="detail-list">
            <div><dt>ID</dt><dd>{record.id}</dd></div>
            <div><dt>{english ? 'Original label' : '原始名称'}</dt><dd>{record.label_original || '—'}</dd></div>
            <div><dt>{english ? 'English label' : '英文名称'}</dt><dd>{record.label_en || '—'}</dd></div>
            <div><dt>{english ? 'Jurisdiction' : '司法辖区'}</dt><dd>{record.jurisdiction || 'Shared graph'}</dd></div>
            <div><dt>source_record_id</dt><dd>{record.source_record_id || '—'}</dd></div>
          </dl>
          <div className="property-block">
            <h3>{english ? 'Typed properties' : '类型化属性'}</h3>
            {Object.keys(record.properties).length ? <dl className="detail-list detail-list--compact">{Object.entries(record.properties).map(([key, value]) => <div key={key}><dt>{humanize(key)}</dt><dd>{String(value)}</dd></div>)}</dl> : <p>{english ? 'No additional properties.' : '没有额外属性。'}</p>}
          </div>
        </div>
        <div className="section-panel entity-graph">
          <div className="section-heading section-heading--compact"><div><h2>{english ? 'Immediate neighborhood' : '一阶邻域'}</h2><p>{graph.data ? `${graph.data.data.nodes.length} nodes · ${graph.data.data.edges.length} relations` : ''}</p></div></div>
          {graph.isLoading ? <LoadingState compact /> : graph.isError ? <ErrorState message={graph.error.message} /> : <GraphCanvas graph={graph.data?.data ?? { nodes: [], edges: [] }} language={i18n.language} onNodeSelect={onNodeSelect} />}
        </div>
      </section>
    </div>
  )
}
