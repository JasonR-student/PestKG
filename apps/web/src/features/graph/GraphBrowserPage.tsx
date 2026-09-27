import { useQuery } from '@tanstack/react-query'
import { Database, Download, Expand, ExternalLink, Focus, ListFilter, Maximize2, Minus, Network, Pin, Play, Plus, RotateCcw, Search, Tag, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'

import { useRelease } from '../../app/release/useRelease'
import { api } from '../../shared/api/client'
import type { GraphBrowserQuery, GraphData } from '../../shared/api/models'
import { formatInteger, preferredLabel } from '../../shared/lib/format'
import { jurisdictionName } from '../../shared/lib/jurisdictions'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { GraphCanvas, type GraphCanvasHandle } from '../explore/components/GraphCanvas'
import { nodeColors } from '../explore/components/node-colors'

const emptyGraph: GraphData = { nodes: [], edges: [] }
const typeNames: Record<string, string> = {
  Jurisdiction: '辖区', CountryOrTerritory: '国家／地区', Source: '来源', SourceSnapshot: '来源快照',
  RegistrationUse: '登记使用', Registration: '登记', PesticideProduct: '农药产品',
  LocalActiveIngredient: '本地有效成分', CropTerm: '作物术语', TargetTerm: '防治对象',
  FormulationTerm: '剂型', RegulatoryOrganization: '监管机构', ChEBITerm: 'ChEBI 本体术语',
  AGROVOCConcept: 'AGROVOC 概念', MoAGroup: '作用机制组', ChemicalEntity: '参考化学实体',
}

export function GraphBrowserPage() {
  const { i18n } = useTranslation()
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
        <div><span className="eyebrow">PESTKG / GRAPH</span><h1>{english ? 'Graph browser' : '图谱浏览器'}</h1></div>
        <div className="graph-release-note"><span>{releaseId}</span><small>{english ? 'Independent reference pack' : '独立参考数据包'} · {catalog.data?.data.reference_pack_id || '—'}</small></div>
      </header>
      <form className="graph-query" onSubmit={(event) => run(event)}>
        <Search size={18} aria-hidden="true" />
        <input aria-label={english ? 'Graph query' : '图谱查询'} value={draft.query} onChange={(event) => setDraft({ ...draft, query: event.target.value })} placeholder={english ? 'Name or node / source identifier' : '节点名称、节点 ID 或来源标识'} />
        <button type="submit" disabled={result.isFetching}><Play size={15} />{english ? 'Run' : '运行'}</button>
      </form>
      <div className="graph-query-options">
        <label>{english ? 'Node limit' : '节点上限'}<select value={draft.limit} onChange={(event) => setDraft({ ...draft, limit: Number(event.target.value) })}>{[60, 120, 240, 300].map((value) => <option key={value}>{value}</option>)}</select></label>
        <label className="graph-check"><input type="checkbox" checked={draft.provenance} onChange={(event) => { const next = { ...draft, provenance: event.target.checked }; setDraft(next); run(undefined, next) }} />{english ? 'Provenance projection' : '溯源属性投影'}</label>
        <span>{english ? 'Read-only · bounded view' : '只读 · 有界视图'}</span>
      </div>
      {error || catalog.isError || result.isError ? <ErrorState message={error || catalog.error?.message || result.error?.message} /> : null}
      <div className="graph-workspace">
        <aside className="graph-database">
          <div className="graph-database-heading"><Database size={34} /><div><h2>{english ? 'Graph scope' : '图谱范围'}</h2><span>{english ? 'Jurisdictions & websites' : '辖区与独立网站'}</span></div><button className="icon-button graph-catalog-toggle" type="button" title={english ? 'Labels and relationships' : '标签与关系'} aria-label={english ? 'Labels and relationships' : '标签与关系'} aria-controls="graph-catalog" aria-expanded={catalogOpen} onClick={() => setCatalogOpen((value) => !value)}><ListFilter size={18} /></button></div>
          <label className="graph-scope-label">{english ? 'Scope' : '辖区／来源'}
            <select aria-label={english ? 'Graph scope' : '图谱范围'} value={draft.scope} onChange={(event) => changeScope(event.target.value)} disabled={catalog.isLoading}>
              <option value="all">{english ? 'All loaded scopes' : '全部已加载子图'}</option>
              {(['jurisdiction', 'source', 'reference'] as const).map((kind) => <optgroup key={kind} label={kind === 'jurisdiction' ? (english ? 'Jurisdictions' : '监管辖区') : kind === 'source' ? (english ? 'Official websites' : '官方来源网站') : (english ? 'Independent reference websites' : '独立补充网站')}>
                {catalog.data?.data.scopes.filter((item) => item.kind === kind).map((item) => <option value={item.id} key={item.id}>{item.kind === 'jurisdiction' ? `${item.name} · ${jurisdictionName(item.name, english)}` : item.name}</option>)}
              </optgroup>)}
            </select>
          </label>
          <dl className="graph-scope-counts"><div><dt>{english ? 'Nodes' : '节点'}</dt><dd>{scope ? formatInteger(scope.nodes) : '—'}</dd></div><div><dt>{english ? 'Stored relations' : '存储关系'}</dt><dd>{scope ? formatInteger(scope.edges) : '—'}</dd></div></dl>
          {scope?.kind === 'reference' ? <p className="graph-scope-status">{scope.coverage_status === 'BOUNDED_OFFICIAL_API_SUBGRAPH' ? (english ? 'Bounded official API subgraph' : '官方接口有界子图') : scope.coverage_status === 'LEGACY_DERIVED_REFERENCE_UNREVIEWED' ? (english ? 'Legacy reference import · unreviewed' : '旧参考子图导入 · 待审核') : (english ? 'Official ontology snapshot' : '官方本体文件快照')}<br />{english ? 'Regulatory identity links: 0' : '已审核监管身份连接：0'}</p> : null}
          <div id="graph-catalog" className={`graph-catalog-scroll${catalogOpen ? ' is-open' : ''}`}>
            <h3>{english ? 'Node labels' : '节点标签'}<small>NODE LABELS</small></h3>
            <button className="graph-label-row" type="button" aria-pressed={!applied.type} onClick={() => { const next = { ...draft, type: '' }; setDraft(next); run(undefined, next) }}><span>{english ? 'All labels' : '全部标签'}</span></button>
            {Object.entries(scope?.node_types ?? {}).sort((a, b) => b[1] - a[1]).map(([type, count]) => <button key={type} className="graph-label-row" type="button" aria-pressed={applied.type === type} onClick={() => { const next = { ...draft, type }; setDraft(next); run(undefined, next) }}><i style={{ background: nodeColors[type] ?? '#87958b' }} /><span>{english ? type : typeNames[type] ?? type}</span><small>{formatInteger(count)}</small></button>)}
            <h3>{english ? 'Relationship types' : '关系类型'}<small>RELATIONSHIP TYPES</small></h3>
            {Object.entries(scope?.relation_types ?? {}).sort((a, b) => b[1] - a[1]).map(([predicate, count]) => <button key={predicate} className="graph-label-row" type="button" aria-pressed={relation === predicate} onClick={() => setRelation((previous) => previous === predicate ? '' : predicate)}><i className="relation-swatch" /><span title={predicate}>{predicate}</span><small>{formatInteger(count)}</small></button>)}
            <details className="graph-loaded-nodes"><summary>{english ? 'Loaded nodes' : '当前节点'} · {graph.nodes.length}</summary><div>{graph.nodes.map((item) => <button key={item.id} type="button" onClick={() => selectNode(item.id)} title={item.id}>{preferredLabel(item, i18n.language)}</button>)}</div></details>
          </div>
        </aside>
        <div className="graph-main-canvas" ref={canvasPanel}>
          <div className="graph-toolbar" role="toolbar" aria-label={english ? 'Graph tools' : '图谱工具'}>
            <button className="icon-button" type="button" title={english ? 'Zoom in' : '放大'} aria-label={english ? 'Zoom in' : '放大'} disabled={!graph.nodes.length} onClick={() => canvas.current?.zoom(1.25)}><Plus size={17} /></button>
            <button className="icon-button" type="button" title={english ? 'Zoom out' : '缩小'} aria-label={english ? 'Zoom out' : '缩小'} disabled={!graph.nodes.length} onClick={() => canvas.current?.zoom(0.8)}><Minus size={17} /></button>
            <button className="icon-button" type="button" title={english ? 'Fit graph' : '适应画布'} aria-label={english ? 'Fit graph' : '适应画布'} disabled={!graph.nodes.length} onClick={() => canvas.current?.fit()}><Focus size={17} /></button>
            <button className="icon-button" type="button" title={english ? 'Relayout' : '重新布局'} aria-label={english ? 'Relayout' : '重新布局'} disabled={!graph.nodes.length} onClick={() => { canvas.current?.relayout(); setPinned([]) }}><RotateCcw size={17} /></button>
            <button className="icon-button" type="button" title={english ? 'Relationship labels' : '关系标签'} aria-label={english ? 'Relationship labels' : '关系标签'} aria-pressed={showLabels} disabled={!graph.nodes.length} onClick={() => setShowLabels((value) => !value)}><Tag size={17} /></button>
            <button className="icon-button" type="button" title={english ? 'Export PNG' : '导出 PNG'} aria-label={english ? 'Export PNG' : '导出 PNG'} disabled={!graph.nodes.length} onClick={downloadPng}><Download size={17} /></button>
            <button className="icon-button" type="button" title={english ? 'Fullscreen' : '全屏'} aria-label={english ? 'Fullscreen' : '全屏'} disabled={!graph.nodes.length} onClick={() => void fullscreen()}><Maximize2 size={17} /></button>
          </div>
          {result.isFetching || catalog.isLoading ? <LoadingState /> : graph.nodes.length ? <GraphCanvas key={key} graph={visibleGraph} language={i18n.language} browser showLabels={showLabels} canvasRef={canvas} onNodeSelect={selectNode} onEdgeSelect={selectEdge} onExpand={expand} /> : <div className="graph-no-results"><Network size={32} /><span>{english ? 'No matching nodes' : '没有符合条件的节点'}</span></div>}
          <footer className="graph-view-status"><span>{graph.nodes.length} {english ? 'nodes' : '节点'} · {visibleGraph.edges.length} {english ? 'relations' : '关系'}</span><span>{expanding ? (english ? 'Expanding…' : '正在展开…') : result.data?.data.truncated ? (english ? 'Bounded sample' : '有界采样') : (english ? 'Query results' : '查询结果')}</span></footer>
        </div>
        <aside className="graph-inspector">
          {!selected ? <div className="graph-inspector-empty"><Network size={32} /><span>{english ? 'No selection' : '暂无选中项'}</span></div> : <>
            <header><span>{node ? (english ? 'NODE' : '节点') : (english ? 'RELATIONSHIP' : '关系')}</span><h2>{label}</h2><small>{node ? (english ? node.type : typeNames[node.type] ?? node.type) : edge?.predicate}</small></header>
            <dl><div><dt>ID</dt><dd>{selected.id}</dd></div>{node?.jurisdiction ? <div><dt>{english ? 'Jurisdiction' : '辖区'}</dt><dd>{node.jurisdiction} · {jurisdictionName(node.jurisdiction, english)}</dd></div> : null}{Object.entries(properties).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—')}</dd></div>)}</dl>
            <div className="graph-inspector-actions">
              {node ? <><button type="button" className="button button--primary" disabled={expanding} onClick={() => void expand(node.id)}><Expand size={15} />{english ? 'Expand' : '展开邻居'}</button><button type="button" className="icon-button" title={english ? 'Pin node' : '固定节点'} aria-label={english ? 'Pin node' : '固定节点'} aria-pressed={pinned.includes(node.id)} onClick={() => { canvas.current?.pin(node.id); setPinned((previous) => previous.includes(node.id) ? previous.filter((id) => id !== node.id) : [...previous, node.id]) }}><Pin size={16} /></button></> : null}
              <button type="button" className="icon-button" title={english ? 'Remove from view' : '从视图移除'} aria-label={english ? 'Remove from view' : '从视图移除'} onClick={remove}><Trash2 size={16} /></button>
              {node?.source_url && /^https?:\/\//.test(node.source_url) ? <a className="icon-button" href={node.source_url} target="_blank" rel="noreferrer" title={english ? 'Source' : '来源'}><ExternalLink size={16} /></a> : null}
            </div>
          </>}
        </aside>
      </div>
    </div>
  )
}
