import { useQuery } from '@tanstack/react-query'
import { Database, Download, Expand, ExternalLink, Focus, ListFilter, Maximize2, Minus, Network, Pin, Plus, RotateCcw, Search, Tag, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'

import { useRelease } from '../../app/release/useRelease'
import { api } from '../../shared/api/client'
import type { GraphBrowserQuery, GraphData } from '../../shared/api/models'
import { formatInteger, preferredLabel } from '../../shared/lib/format'
import { fieldLabel, nodeTypeLabel, relationLabel } from '../../shared/lib/labels'
import { jurisdictionName } from '../../shared/lib/jurisdictions'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { GraphCanvas, type GraphCanvasHandle } from '../explore/components/GraphCanvas'
import { nodeColors } from '../explore/components/node-colors'
import { categoryFromQuery, categoryMatches } from './graph-categories'

const emptyGraph: GraphData = { nodes: [], edges: [] }

export function GraphBrowserPage() {
  const { i18n, t } = useTranslation()
  const english = i18n.language.startsWith('en')
  const { releaseId } = useRelease()
  const [params, setParams] = useSearchParams()
  const initialScope = params.get('scope') ?? 'jurisdiction:AU'
  const [draft, setDraft] = useState<GraphBrowserQuery>({ scope: initialScope, query: '', type: '', limit: 120, provenance: true })
  const [applied, setApplied] = useState(draft)
  const [loaded, setLoaded] = useState<{ key: string; graph: GraphData }>({ key: '', graph: emptyGraph })
  const [selection, setSelection] = useState<{ key: string; kind: 'node' | 'edge'; id: string } | null>(null)
  const [relation, setRelation] = useState('')
  const [showLabels, setShowLabels] = useState(false)
  const [catalogOpen, setCatalogOpen] = useState(false)
  const [categorySearch, setCategorySearch] = useState('')
  const [pinned, setPinned] = useState<string[]>([])
  const [error, setError] = useState('')
  const [expanding, setExpanding] = useState(false)
  const canvas = useRef<GraphCanvasHandle | null>(null)
  const canvasPanel = useRef<HTMLDivElement>(null)
  const expansion = useRef<AbortController | null>(null)
  const key = JSON.stringify([releaseId, applied])
  const currentKey = useRef(key)
  const catalog = useQuery({ queryKey: ['graph-catalog', releaseId], queryFn: ({ signal }) => api.graphCatalog(releaseId, signal), enabled: Boolean(releaseId) })
  const result = useQuery({ queryKey: ['graph-browser', releaseId, applied], queryFn: ({ signal }) => api.graphQuery(applied, releaseId, signal), enabled: Boolean(releaseId) })

  useEffect(() => {
    currentKey.current = key
    expansion.current?.abort()
    return () => expansion.current?.abort()
  }, [key])

  const graph = loaded.key === key ? loaded.graph : result.data?.data ?? emptyGraph
  const selected = selection?.key === key ? selection : null
  const visibleGraph = useMemo(() => relation ? { ...graph, edges: graph.edges.filter((edge) => edge.predicate === relation) } : graph, [graph, relation])
  const scope = catalog.data?.data.scopes.find((item) => item.id === applied.scope)
  const categories = useMemo(() => {
    if (scope) return Object.entries(scope.node_types).sort((a, b) => b[1] - a[1])
    return [...new Set(catalog.data?.data.scopes.flatMap((item) => Object.keys(item.node_types)) ?? [])]
      .sort().map((type): [string, number | undefined] => [type, undefined])
  }, [scope, catalog.data])
  const filteredCategories = categories.filter(([type]) => categoryMatches(type, categorySearch))
  const node = selected?.kind === 'node' ? graph.nodes.find((item) => item.id === selected.id) : undefined
  const edge = selected?.kind === 'edge' ? graph.edges.find((item) => item.id === selected.id) : undefined
  const selectNode = useCallback((id: string) => setSelection({ key, kind: 'node', id }), [key])
  const selectEdge = useCallback((id: string) => setSelection({ key, kind: 'edge', id }), [key])

  const expand = useCallback(async (id: string) => {
    const requestKey = key
    expansion.current?.abort()
    const controller = new AbortController()
    expansion.current = controller
    setExpanding(true)
    setError('')
    try {
      const response = await api.graphExpand(id, applied, releaseId, controller.signal)
      if (currentKey.current !== requestKey || controller.signal.aborted) return
      setPinned([])
      setLoaded((previous) => {
        const baseline = previous.key === requestKey ? previous.graph : result.data?.data ?? emptyGraph
        const nodes = [...new Map([...baseline.nodes, ...response.data.nodes].map((item) => [item.id, item])).values()].slice(0, applied.limit)
        const ids = new Set(nodes.map((item) => item.id))
        const edges = [...new Map([...baseline.edges, ...response.data.edges].map((item) => [item.id, item])).values()]
          .filter((item) => ids.has(item.start_id) && ids.has(item.end_id)).slice(0, 2000)
        return { key: requestKey, graph: { nodes, edges } }
      })
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : String(failure))
    } finally {
      if (currentKey.current === requestKey && !controller.signal.aborted) setExpanding(false)
    }
  }, [applied, releaseId, key, result.data])

  const run = (event?: FormEvent, query = draft) => {
    event?.preventDefault()
    setLoaded({ key: '', graph: emptyGraph })
    setSelection(null)
    setPinned([])
    setRelation('')
    setError('')
    setExpanding(false)
    setApplied({ ...query })
    setParams((previous) => { const next = new URLSearchParams(previous); next.set('scope', query.scope); return next }, { replace: true })
    if (JSON.stringify(query) === JSON.stringify(applied)) void result.refetch()
  }
  const changeScope = (value: string) => {
    const query = { ...draft, scope: value, type: '', query: '' }
    setDraft(query)
    setCategorySearch('')
    run(undefined, query)
  }
  const search = (event: FormEvent) => {
    const type = categoryFromQuery(draft.query ?? '', categories.map(([name]) => name))
    const query = type ? { ...draft, type, query: '' } : draft
    setDraft(query)
    run(event, query)
  }
  const chooseCategory = (type: string) => {
    const query = { ...draft, type, query: '' }
    setDraft(query)
    run(undefined, query)
  }
  const downloadPng = () => {
    const url = canvas.current?.png()
    if (!url) return
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `PestKG-${applied.scope.replace(':', '-')}.png`
    anchor.click()
  }
  const fullscreen = async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen()
      else await canvasPanel.current?.requestFullscreen()
    } catch (failure) { setError(failure instanceof Error ? failure.message : String(failure)) }
  }
  const remove = () => {
    if (!selected) return
    setPinned([])
    setLoaded({ key, graph: {
      nodes: selected.kind === 'node' ? graph.nodes.filter((item) => item.id !== selected.id) : graph.nodes,
      edges: graph.edges.filter((item) => selected.kind === 'edge' ? item.id !== selected.id : item.start_id !== selected.id && item.end_id !== selected.id),
    } })
    setSelection(null)
  }
  const properties = node?.properties ?? edge?.properties ?? {}
  const label = node ? preferredLabel(node, i18n.language) : edge?.predicate
  return (
    <div className="graph-browser">
       <header className="graph-browser-heading">
        <div><span className="eyebrow">PESTKG / GRAPH</span><h1>{t('graph.title')}</h1></div>
        <div className="graph-release-note"><span title={releaseId ?? undefined}>{releaseId}</span><small>{t('graph.referencePack')} · <span title={catalog.data?.data.reference_pack_id || undefined}>{catalog.data?.data.reference_pack_id || '—'}</span></small></div>
      </header>
      <form className="graph-query" onSubmit={search}>
        <Search size={18} aria-hidden="true" />
        <input aria-label={t('graph.graphQuery')} value={draft.query} onChange={(event) => setDraft({ ...draft, query: event.target.value })} placeholder={t('graph.queryPlaceholder')} />
        <button type="submit" disabled={result.isFetching || catalog.isLoading}><Search size={15} />{t('common.search')}</button>
      </form>
      <div className="graph-query-options">
        <label>{t('graph.category')}<select aria-label={t('graph.category')} value={draft.type} onChange={(event) => chooseCategory(event.target.value)} disabled={catalog.isLoading}><option value="">{t('graph.allCategories')}</option>{categories.map(([type]) => <option key={type} value={type}>{nodeTypeLabel(type, i18n.language)}</option>)}</select></label>
        <label>{t('graph.nodeLimit')}<select aria-label={t('graph.nodeLimit')} value={draft.limit} onChange={(event) => setDraft({ ...draft, limit: Number(event.target.value) })}>{[60, 120, 240, 300].map((value) => <option key={value}>{value}</option>)}</select></label>
        <label className="graph-check"><input type="checkbox" checked={draft.provenance} onChange={(event) => { const next = { ...draft, provenance: event.target.checked }; setDraft(next); run(undefined, next) }} />{t('graph.provenanceProjection')}</label>
        <span>{t('graph.readOnlyBounded')}</span>
      </div>
      {error || catalog.isError || result.isError ? <ErrorState message={error || catalog.error?.message || result.error?.message} /> : null}
      <div className="graph-workspace">
        <aside className="graph-database">
          <div className="graph-database-heading"><Database size={34} /><div><h2>{t('graph.graphScope')}</h2><span>{t('graph.scope')}</span></div><button className="icon-button graph-catalog-toggle" type="button" title={t('graph.labelsAndRelationships')} aria-label={t('graph.labelsAndRelationships')} aria-controls="graph-catalog" aria-expanded={catalogOpen} onClick={() => setCatalogOpen((value) => !value)}><ListFilter size={18} /></button></div>
          <label className="graph-scope-label">{t('graph.scope')}
            <select aria-label={t('graph.graphScope')} value={draft.scope} onChange={(event) => changeScope(event.target.value)} disabled={catalog.isLoading}>
              <option value="all">{t('graph.allLoadedScopes')}</option>
              {draft.scope !== 'all' && !catalog.data?.data.scopes.some((item) => item.id === draft.scope) ? <option value={draft.scope}>{draft.scope}</option> : null}
              {(['jurisdiction', 'source', 'reference'] as const).map((kind) => <optgroup key={kind} label={kind === 'jurisdiction' ? t('graph.jurisdictions') : kind === 'source' ? t('graph.officialWebsites') : t('graph.independentWebsites')}>
                {catalog.data?.data.scopes.filter((item) => item.kind === kind).map((item) => <option value={item.id} key={item.id}>{item.kind === 'jurisdiction' ? `${item.name} · ${jurisdictionName(item.name, english)}` : item.name}</option>)}
              </optgroup>)}
            </select>
          </label>
          <dl className="graph-scope-counts"><div><dt>{t('graph.nodes')}</dt><dd title={scope ? formatInteger(scope.nodes, i18n.language) : undefined}>{scope ? formatInteger(scope.nodes, i18n.language) : '—'}</dd></div><div><dt>{t('graph.storedRelations')}</dt><dd title={scope ? formatInteger(scope.edges, i18n.language) : undefined}>{scope ? formatInteger(scope.edges, i18n.language) : '—'}</dd></div></dl>
          {scope?.kind === 'reference' ? <p className="graph-scope-status">{scope.coverage_status === 'BOUNDED_OFFICIAL_API_SUBGRAPH' ? t('graph.boundedOfficialApiSubgraph') : scope.coverage_status === 'LEGACY_DERIVED_REFERENCE_UNREVIEWED' ? t('graph.legacyReferenceImport') : t('graph.officialOntologySnapshot')}<br />{t('graph.regulatoryIdentityLinks')}{english ? ': 0' : '：0'}</p> : null}
          <div id="graph-catalog" className={`graph-catalog-scroll${catalogOpen ? ' is-open' : ''}`}>
            <h3>{t('graph.categories')}<small>CATEGORIES</small></h3>
            <label className="graph-category-search"><Search size={14} aria-hidden="true" /><input aria-label={t('graph.searchCategories')} placeholder={t('graph.searchCategories')} value={categorySearch} onChange={(event) => setCategorySearch(event.target.value)} /></label>
            <button className="graph-label-row" type="button" aria-pressed={!applied.type} onClick={() => chooseCategory('')}><span>{t('graph.allCategories')}</span></button>
            {filteredCategories.map(([type, count]) => <button key={type} className="graph-label-row" type="button" title={type} aria-pressed={applied.type === type} onClick={() => chooseCategory(type)}><i style={{ background: nodeColors[type] ?? '#87958b' }} /><span>{nodeTypeLabel(type, i18n.language)}</span>{count !== undefined ? <small title={formatInteger(count, i18n.language)}>{formatInteger(count, i18n.language)}</small> : null}</button>)}
            {!filteredCategories.length && categorySearch ? <p className="graph-category-empty" role="status">{t('graph.noMatchingCategories')}</p> : null}
            <h3>{t('graph.relationshipTypes')}<small>RELATIONSHIP TYPES</small></h3>
            {Object.entries(scope?.relation_types ?? {}).sort((a, b) => b[1] - a[1]).map(([predicate, count]) => <button key={predicate} className="graph-label-row" type="button" aria-pressed={relation === predicate} onClick={() => setRelation((previous) => previous === predicate ? '' : predicate)}><i className="relation-swatch" /><span title={predicate}>{relationLabel(predicate, i18n.language)}</span><small title={formatInteger(count, i18n.language)}>{formatInteger(count, i18n.language)}</small></button>)}
            <details className="graph-loaded-nodes"><summary>{t('graph.loadedNodes')} · {formatInteger(graph.nodes.length, i18n.language)}</summary><div>{graph.nodes.map((item) => <button key={item.id} type="button" onClick={() => selectNode(item.id)} title={item.id}>{preferredLabel(item, i18n.language)}</button>)}</div></details>
          </div>
        </aside>
        <div className="graph-main-canvas" ref={canvasPanel}>
          <div className="graph-toolbar" role="toolbar" aria-label={t('graph.tools')}>
            <button className="icon-button" type="button" title={t('graph.zoomIn')} aria-label={t('graph.zoomIn')} disabled={!graph.nodes.length} onClick={() => canvas.current?.zoom(1.25)}><Plus size={17} /></button>
            <button className="icon-button" type="button" title={t('graph.zoomOut')} aria-label={t('graph.zoomOut')} disabled={!graph.nodes.length} onClick={() => canvas.current?.zoom(0.8)}><Minus size={17} /></button>
            <button className="icon-button" type="button" title={t('graph.fitGraph')} aria-label={t('graph.fitGraph')} disabled={!graph.nodes.length} onClick={() => canvas.current?.fit()}><Focus size={17} /></button>
            <button className="icon-button" type="button" title={t('graph.relayout')} aria-label={t('graph.relayout')} disabled={!graph.nodes.length} onClick={() => { canvas.current?.relayout(); setPinned([]) }}><RotateCcw size={17} /></button>
            <button className="icon-button" type="button" title={t('graph.relationshipLabels')} aria-label={t('graph.relationshipLabels')} aria-pressed={showLabels} disabled={!graph.nodes.length} onClick={() => setShowLabels((value) => !value)}><Tag size={17} /></button>
            <button className="icon-button" type="button" title={t('graph.exportPng')} aria-label={t('graph.exportPng')} disabled={!graph.nodes.length} onClick={downloadPng}><Download size={17} /></button>
            <button className="icon-button" type="button" title={t('graph.fullscreen')} aria-label={t('graph.fullscreen')} disabled={!graph.nodes.length} onClick={() => void fullscreen()}><Maximize2 size={17} /></button>
          </div>
          {result.isFetching || catalog.isLoading ? <LoadingState /> : graph.nodes.length ? <GraphCanvas key={key} graph={visibleGraph} language={i18n.language} browser showLabels={showLabels} canvasRef={canvas} onNodeSelect={selectNode} onEdgeSelect={selectEdge} onExpand={expand} /> : <div className="graph-no-results"><Network size={32} /><span>{t('graph.noMatchingNodes')}</span></div>}
          <footer className="graph-view-status"><span>{formatInteger(graph.nodes.length, i18n.language)} {t('graph.nodes').toLowerCase()} · {formatInteger(visibleGraph.edges.length, i18n.language)} {t('graph.relationship').toLowerCase()}</span><span>{expanding ? t('graph.expanding') : result.data?.data.truncated ? t('graph.boundedSample') : t('graph.queryResults')}</span></footer>
        </div>
        <aside className="graph-inspector">
          {!selected ? <div className="graph-inspector-empty"><Network size={32} /><span>{t('graph.noSelection')}</span></div> : <>
            <header><span>{node ? t('graph.nodeLabel').toUpperCase() : t('graph.relationshipLabel').toUpperCase()}</span><h2>{label}</h2><small title={node ? node.type : edge?.predicate}>{node ? nodeTypeLabel(node.type, i18n.language) : relationLabel(edge?.predicate ?? '', i18n.language)}</small>{node ? <small>{node.type}</small> : <small title={edge?.predicate}>{edge?.predicate}</small>}</header>
            <dl><div><dt>ID</dt><dd>{selected.id}</dd></div>{node?.jurisdiction ? <div><dt>{t('fieldLabels.jurisdiction')}</dt><dd>{node.jurisdiction} · {jurisdictionName(node.jurisdiction, english)}</dd></div> : null}{Object.entries(properties).map(([name, value]) => <div key={name}><dt title={name}>{fieldLabel(name, i18n.language)}</dt><dd>{typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—')}</dd></div>)}</dl>
            <div className="graph-inspector-actions">
              {node ? <><button type="button" className="button button--primary" disabled={expanding} onClick={() => void expand(node.id)}><Expand size={15} />{t('graph.expand')}</button><button type="button" className="icon-button" title={t('graph.pinNode')} aria-label={t('graph.pinNode')} aria-pressed={pinned.includes(node.id)} onClick={() => { canvas.current?.pin(node.id); setPinned((previous) => previous.includes(node.id) ? previous.filter((id) => id !== node.id) : [...previous, node.id]) }}><Pin size={16} /></button></> : null}
              <button type="button" className="icon-button" title={t('graph.removeFromView')} aria-label={t('graph.removeFromView')} onClick={remove}><Trash2 size={16} /></button>
              {node?.source_url && /^https?:\/\//.test(node.source_url) ? <a className="icon-button" href={node.source_url} target="_blank" rel="noreferrer" title={t('graph.source')}><ExternalLink size={16} /></a> : null}
            </div>
          </>}
        </aside>
      </div>
    </div>
  )
}
