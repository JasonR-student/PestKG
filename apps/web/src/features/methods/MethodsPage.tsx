import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, GitMerge, Languages, ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { api } from '../../shared/api/client'
import { PageHeader } from '../../shared/ui/PageHeader'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { formatInteger } from '../../shared/lib/format'
import { fieldLabel, nodeTypeLabel, relationLabel } from '../../shared/lib/labels'
import { useRelease } from '../../app/release/useRelease'

export function MethodsPage() {
  const { i18n, t } = useTranslation()
  const { releaseId } = useRelease()
  const schema = useQuery({ queryKey: ['schema', releaseId], queryFn: ({ signal }) => api.schema(releaseId, signal), enabled: Boolean(releaseId) })
  if (schema.isLoading) return <LoadingState />
  if (schema.isError || !schema.data) return <ErrorState />
  const data = schema.data.data

  return (
    <div className="page-stack">
      <PageHeader title={t('methods.title')} description={t('methods.description')} />
      <section className="principle-strip">
        <div><ShieldCheck size={20} /><span><strong>{t('methods.traceableFacts')}</strong><small>source_record_id + source_url</small></span></div>
        <div><GitMerge size={20} /><span><strong>{t('methods.identityReview')}</strong><small>{t('methods.reviewedGlobalChemicals')}</small></span></div>
        <div><Languages size={20} /><span><strong>{t('methods.additiveEnglishLabels')}</strong><small>{t('methods.originalLabelsCanonical')}</small></span></div>
        <div><CheckCircle2 size={20} /><span><strong>{t('methods.independentReferences')}</strong><small>{t('methods.separateSourceNamespaces')}</small></span></div>
      </section>
      <section className="methods-visuals">
        <figure><img src="/research/Figure1_workflow.png" alt={t('methods.workflowAlt')} /><figcaption>{t('methods.workflowCaption')}</figcaption></figure>
        <figure><img src="/research/Figure4_kg_schema.png" alt={t('methods.schemaAlt')} /><figcaption>{t('methods.schemaCaption')}</figcaption></figure>
      </section>
      <section className="schema-layout">
        <div className="section-panel"><div className="section-heading section-heading--compact"><div><h2>{t('methods.nodeInventory')}</h2></div></div><div className="inventory-list">{Object.entries(data.node_types).toSorted((a, b) => b[1] - a[1]).map(([type, count]) => <div key={type}><span title={type}>{nodeTypeLabel(type, i18n.language)}</span><strong title={formatInteger(count, i18n.language)}>{formatInteger(count, i18n.language)}</strong></div>)}</div></div>
        <div className="section-panel"><div className="section-heading section-heading--compact"><div><h2>{t('methods.relationInventory')}</h2></div></div><div className="inventory-list">{Object.entries(data.relation_types).toSorted((a, b) => b[1] - a[1]).map(([type, count]) => <div key={type}><span title={type}>{relationLabel(type, i18n.language)}</span><strong title={formatInteger(count, i18n.language)}>{formatInteger(count, i18n.language)}</strong></div>)}</div></div>
      </section>
      <section className="section-panel rule-panel"><div className="section-heading section-heading--compact"><div><h2>{t('methods.releaseInvariants')}</h2></div></div><dl className="detail-list">{Object.entries(data.rules).map(([key, value]) => <div key={key}><dt title={key}>{fieldLabel(key, i18n.language)}</dt><dd>{value}</dd></div>)}</dl></section>
    </div>
  )
}
