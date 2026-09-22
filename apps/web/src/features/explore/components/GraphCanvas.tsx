import { Maximize2, Network } from 'lucide-react'
import { useEffect, useRef } from 'react'

import { preferredLabel } from '../../../shared/lib/format'
import type { GraphData } from '../../../shared/api/models'

const nodeColors: Record<string, string> = {
  RegistrationUse: '#205b4f',
  PesticideProduct: '#c06144',
  ActiveIngredientLocal: '#3c6e97',
  CropLocal: '#7b964f',
  TargetLocal: '#a87c2c',
  Registration: '#7b5d91',
  FormulationLocal: '#6d7772',
}

type Props = {
  graph: GraphData
  language: string
  onNodeSelect?: (nodeId: string) => void
}

export function GraphCanvas({ graph, language, onNodeSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

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
                graph.nodes.length <= 10 || labelTypes.has(node.type)
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
            },
          })),
        ],
        style: [
          {
            selector: 'node',
            style: {
              'background-color': 'data(color)',
              label: 'data(label)',
              color: '#17201d',
              'font-size': 10,
              'text-wrap': 'ellipsis',
              'text-max-width': '95px',
              'text-valign': 'bottom',
              'text-margin-y': 8,
              width: 24,
              height: 24,
              'border-width': 2,
              'border-color': '#ffffff',
            },
          },
          {
            selector: 'node.hovered',
            style: {
              label: 'data(fullLabel)',
              'text-background-color': '#ffffff',
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
            },
          },
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
        minZoom: 0.25,
        maxZoom: 2.5,
      })
      instance.on('mouseover', 'node', (event) => event.target.addClass('hovered'))
      instance.on('mouseout', 'node', (event) => event.target.removeClass('hovered'))
      instance.on('tap', 'node', (event) => onNodeSelect?.(event.target.id()))
      destroy = () => instance.destroy()
    })

    return () => {
      disposed = true
      destroy?.()
    }
  }, [graph, language, onNodeSelect])

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
