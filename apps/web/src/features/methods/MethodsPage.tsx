import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, GitMerge, Languages, ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { api } from '../../shared/api/client'
import { PageHeader } from '../../shared/ui/PageHeader'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { formatInteger, humanize } from '../../shared/lib/format'
import { useRelease } from '../../app/release/useRelease'

export function MethodsPage() {
  const { i18n } = useTranslation()
  const { releaseId } = useRelease()
  const english = i18n.language.startsWith('en')
  const schema = useQuery({ queryKey: ['schema', releaseId], queryFn: ({ signal }) => api.schema(releaseId, signal), enabled: Boolean(releaseId) })
  if (schema.isLoading) return <LoadingState />
  if (schema.isError || !schema.data) return <ErrorState />
  const data = schema.data.data

  return (
    <div className="page-stack">
      <PageHeader title={english ? 'Methodology and data quality' : '方法与数据质量'} description={english ? 'The portal preserves local regulatory identity, explicit provenance and release-level validation.' : '平台保留监管实体的本地身份、明确来源链与版本级质量验证。'} />
      <section className="principle-strip">
        <div><ShieldCheck size={20} /><span><strong>{english ? 'Traceable facts' : '事实可追溯'}</strong><small>source_record_id + source_url</small></span></div>
        <div><GitMerge size={20} /><span><strong>{english ? 'Federated identity' : '联邦身份模型'}</strong><small>exactMatch / lexicalAlignment</small></span></div>
        <div><Languages size={20} /><span><strong>{english ? 'Additive English labels' : '英文增强字段'}</strong><small>{english ? 'Original labels remain canonical' : '原始名称仍为规范事实'}</small></span></div>
        <div><CheckCircle2 size={20} /><span><strong>{english ? 'Validated release' : '已验证版本'}</strong><small>zero broken alignment edges</small></span></div>
      </section>
      <section className="methods-visuals">
        <figure><img src="/research/Figure1_workflow.png" alt={english ? 'Knowledge graph research workflow' : '知识图谱研究流程'} /><figcaption>{english ? 'Figure 1. Reproducible workflow from official source snapshots to a federated release.' : '图 1：从官方来源快照到联邦发布版本的可复现流程。'}</figcaption></figure>
        <figure><img src="/research/Figure4_kg_schema.png" alt={english ? 'Knowledge graph schema' : '知识图谱 Schema'} /><figcaption>{english ? 'Figure 4. Country-local registration entities and shared semantic alignments.' : '图 4：国家本地登记实体与共享语义对齐。'}</figcaption></figure>
      </section>
      <section className="schema-layout">
        <div className="section-panel"><div className="section-heading section-heading--compact"><div><h2>{english ? 'Node inventory' : '节点类型清单'}</h2></div></div><div className="inventory-list">{Object.entries(data.node_types).toSorted((a, b) => b[1] - a[1]).map(([type, count]) => <div key={type}><span>{humanize(type)}</span><strong>{formatInteger(count)}</strong></div>)}</div></div>
        <div className="section-panel"><div className="section-heading section-heading--compact"><div><h2>{english ? 'Relation inventory' : '关系类型清单'}</h2></div></div><div className="inventory-list">{Object.entries(data.relation_types).toSorted((a, b) => b[1] - a[1]).map(([type, count]) => <div key={type}><span>{humanize(type)}</span><strong>{formatInteger(count)}</strong></div>)}</div></div>
      </section>
      <section className="section-panel rule-panel"><div className="section-heading section-heading--compact"><div><h2>{english ? 'Release invariants' : '发布不变量'}</h2></div></div><dl className="detail-list">{Object.entries(data.rules).map(([key, value]) => <div key={key}><dt>{humanize(key)}</dt><dd>{value}</dd></div>)}</dl></section>
    </div>
  )
}
