import { Maximize2, Network } from 'lucide-react'
import type { Core } from 'cytoscape'
import { useEffect, useRef, type RefObject } from 'react'

import { preferredLabel } from '../../../shared/lib/format'
import type { GraphData } from '../../../shared/api/models'
import { nodeColors } from './node-colors'

export type GraphCanvasHandle = {
  zoom: (factor: number) => void
  fit: () => void
  relayout: () => void
  png: () => string
  pin: (id: string) => void
}

type Props = {
  graph: GraphData
  language: string
  onNodeSelect?: (nodeId: string) => void
  onEdgeSelect?: (edgeId: string) => void
  onExpand?: (nodeId: string) => void
  canvasRef?: RefObject<GraphCanvasHandle | null>
  browser?: boolean
  showLabels?: boolean
}

export function GraphCanvas({ graph, language, onNodeSelect, onEdgeSelect, onExpand, canvasRef, browser = false, showLabels = false }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const instanceRef = useRef<Core | null>(null)
  const labelsRef = useRef(showLabels)

  useEffect(() => {
    labelsRef.current = showLabels
    instanceRef.current?.style().selector('edge').style('label', showLabels ? 'data(label)' : '').update()
  }, [showLabels])

  useEffect(() => {
    let disposed = false
    let destroy: (() => void) | undefined

    void import('cytoscape').then(({ default: cytoscape }) => {
      if (disposed || !containerRef.current) return
      const labelTypes = new Set([
        'RegistrationUse',
        'Registration',
        'PesticideProduct',
        'ActiveIngredientLocal',
      ])
      const instance = cytoscape({
        container: containerRef.current,
        elements: [
          ...graph.nodes.map((node) => ({
            data: {
              id: node.id,
              label:
                browser || graph.nodes.length <= 10 || labelTypes.has(node.type)
                  ? preferredLabel(node, language)
                  : '',
              fullLabel: preferredLabel(node, language),
              type: node.type,
              color: nodeColors[node.type] ?? '#596660',
            },
          })),
          ...graph.edges.map((edge) => ({
            data: {
              id: edge.id,
              source: edge.start_id,
              target: edge.end_id,
              label: edge.predicate,
              projected: edge.properties?.stored_fact === false ? 1 : 0,
            },
          })),
        ],
        style: [
          {
            selector: 'node',
            style: {
              'background-color': 'data(color)',
              label: 'data(label)',
              color: browser ? '#ffffff' : '#17201d',
              'font-size': browser ? 8 : 10,
              'text-wrap': 'ellipsis',
              'text-max-width': browser ? '30px' : '95px',
              'text-valign': browser ? 'center' : 'bottom',
              'text-margin-y': browser ? 0 : 8,
              width: browser ? 34 : 24,
              height: browser ? 34 : 24,
              'border-width': 2,
              'border-color': '#ffffff',
            },
          },
          {
            selector: 'node.hovered',
            style: {
              label: 'data(fullLabel)',
              'text-max-width': '240px',
              'text-wrap': 'wrap',
              'text-background-color': '#ffffff',
              color: '#17201d',
              'text-background-opacity': 0.94,
              'text-background-padding': '4px',
              'text-border-color': '#d8dfdb',
              'text-border-width': 1,
              'z-index': 10,
            },
          },
          {
            selector: 'edge',
            style: {
              width: 1,
              'line-color': '#bac5c0',
              'target-arrow-color': '#899790',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
              opacity: 0.78,
              label: labelsRef.current ? 'data(label)' : '',
              'font-size': 7,
              'text-background-color': '#ffffff',
              'text-background-opacity': 0.9,
            },
          },
          { selector: 'edge[projected = 1]', style: { 'line-style': 'dashed', 'line-color': '#9fbcae' } },
          {
            selector: 'node:selected',
            style: {
              'border-width': 4,
              'border-color': '#17201d',
            },
          },
        ],
        layout: {
          name: graph.nodes.length > 2 ? 'cose' : 'grid',
          animate: false,
          fit: true,
          padding: 36,
        },
        minZoom: 0.08,
        maxZoom: 4,
      })
      instanceRef.current = instance
      instance.on('mouseover', 'node', (event) => event.target.addClass('hovered'))
      instance.on('mouseout', 'node', (event) => event.target.removeClass('hovered'))
      instance.on('tap', 'node', (event) => onNodeSelect?.(event.target.id()))
      instance.on('tap', 'edge', (event) => onEdgeSelect?.(event.target.id()))
      instance.on('dbltap', 'node', (event) => onExpand?.(event.target.id()))
      if (canvasRef) canvasRef.current = {
        zoom: (factor) => instance.zoom({ level: instance.zoom() * factor, renderedPosition: { x: instance.width() / 2, y: instance.height() / 2 } }),
        fit: () => instance.fit(undefined, 36),
        relayout: () => { instance.nodes().unlock(); instance.layout({ name: 'cose', animate: false, padding: 36 }).run() },
        png: () => instance.png({ full: true, bg: '#fbfdfb', scale: 2 }),
        pin: (id) => { const node = instance.getElementById(id); if (node.locked()) node.unlock(); else node.lock() },
      }
      destroy = () => { if (canvasRef) canvasRef.current = null; instanceRef.current = null; instance.destroy() }
    })

    return () => {
      disposed = true
      destroy?.()
    }
  }, [graph, language, onNodeSelect, onEdgeSelect, onExpand, canvasRef, browser])

  if (!graph.nodes.length) {
    const english = language.startsWith('en')
    return (
      <div className="graph-empty">
        <Network size={28} aria-hidden="true" />
        <span>{english ? 'Select a registration-use row to inspect its local graph.' : '选择一条登记使用记录以查看局部关系图。'}</span>
      </div>
    )
  }

  return (
    <div className="graph-canvas-wrap">
      <div className="graph-counts">
        <span>{graph.nodes.length} nodes</span>
        <span>{graph.edges.length} relations</span>
        <Maximize2 size={14} aria-hidden="true" />
      </div>
      <div ref={containerRef} className="graph-canvas" />
    </div>
  )
}
