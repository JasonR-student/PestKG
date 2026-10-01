import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../../shared/api/client'
import { echarts } from '../../shared/charts/echarts'
import { ReactEChartsCore } from '../../shared/charts/react-echarts-core'
import { PageHeader } from '../../shared/ui/PageHeader'
import { ErrorState, LoadingState } from '../../shared/ui/QueryState'
import { useRelease } from '../../app/release/useRelease'
import { jurisdictionName } from '../../shared/lib/jurisdictions'
import { fieldLabel } from '../../shared/lib/labels'
import { formatInteger } from '../../shared/lib/format'

const questions = ['q1', 'q2', 'q3', 'q4', 'q5'] as const

const chartFields: Record<string, { label: string; value: string }> = {
  q1: { label: 'active_ingredient_label_en', value: 'registration_use_count' },
  q2: { label: 'product_name', value: 'registration_use_count' },
  q3: { label: 'crop_label_en', value: 'registration_use_count' },
  q4: { label: 'formulation_label_en', value: 'product_count' },
  q5: { label: 'jurisdiction', value: 'registration_use_count' },
}

export function ComparePage() {
  const { i18n, t } = useTranslation()
  const english = i18n.language.startsWith('en')
  const { releaseId } = useRelease()
  const [question, setQuestion] = useState<typeof questions[number]>('q1')
  const [query, setQuery] = useState('')
  const [jurisdiction, setJurisdiction] = useState('')
  const countries = useQuery({ queryKey: ['countries', releaseId], queryFn: ({ signal }) => api.countries(releaseId, signal), enabled: Boolean(releaseId) })
  const comparison = useQuery({
    queryKey: ['comparison', releaseId, question, query, jurisdiction],
    queryFn: ({ signal }) => api.comparison(question, query, jurisdiction, releaseId, signal),
    enabled: Boolean(releaseId),
  })
  const rows = useMemo(() => comparison.data?.data ?? [], [comparison.data])
  const columns = rows.length ? Object.keys(rows[0]).slice(0, 8) : []
  const chart = chartFields[question]
  const chartRows = useMemo(
    () => rows
      .toSorted((a, b) => Number(b[chart.value] || 0) - Number(a[chart.value] || 0))
      .slice(0, 12)
    .toReversed(),
    [rows, chart],
  )
  const chartLabels = chartRows.map((row) => question === 'q5'
    ? `${row.jurisdiction || '—'} · ${row.active_ingredient_label_en || '—'}`
    : row[chart.label] || '—')
  const formatCell = (column: string, value: unknown) => {
    if (value === null || value === undefined || value === '') return '—'
    if (column.endsWith('_count') && Number.isFinite(Number(value))) return formatInteger(Number(value), i18n.language)
    return String(value)
  }
  const option = {
    animationDuration: 400,
    color: ['#205b4f'],
    grid: { left: 150, right: 54, top: 10, bottom: 30 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', axisLabel: { formatter: (value: number) => formatInteger(value, i18n.language) }, splitLine: { lineStyle: { color: '#e8ece9' } } },
    yAxis: { type: 'category', data: chartLabels, axisLabel: { width: 130, overflow: 'truncate' } },
    series: [{ type: 'bar', data: chartRows.map((row) => Number(row[chart.value] || 0)), barMaxWidth: 18, label: { show: true, position: 'right', color: '#44534e', fontSize: 9 } }],
    media: [{ query: { maxWidth: 520 }, option: { grid: { left: 72, right: 42 }, yAxis: { axisLabel: { width: 62, overflow: 'truncate' } } } }],
  }

  return (
    <div className="page-stack">
      <PageHeader
        title={t('compare.title')}
        description={t('compare.description')}
      />
      <div className="question-tabs" role="tablist">
        {questions.map((key) => (
          <button key={key} role="tab" type="button" aria-selected={question === key} className={question === key ? 'is-active' : ''} onClick={() => setQuestion(key)}><strong>{key.toUpperCase()}</strong><span>{t(`compare.${key}`)}</span></button>
        ))}
      </div>
      <section className="comparison-toolbar">
        <label className="field field--wide"><span>{t('compare.searchResultSet')}</span><div className="input-with-icon"><Search size={15} /><input aria-label={t('compare.searchResultSet')} value={query} onChange={(event) => setQuery(event.target.value)} /></div></label>
        <label className="field"><span>{t('compare.jurisdiction')}</span><select aria-label={t('compare.jurisdiction')} value={jurisdiction} onChange={(event) => setJurisdiction(event.target.value)}><option value="">{t('common.all')}</option>{countries.data?.data.map((country) => <option key={country.jurisdiction} value={country.jurisdiction}>{country.jurisdiction} · {jurisdictionName(country.jurisdiction, english)}</option>)}</select></label>
      </section>
      {comparison.isLoading ? <LoadingState /> : null}
      {comparison.isError ? <ErrorState message={comparison.error.message} /> : null}
      {comparison.isSuccess ? (
        <section className="comparison-layout">
          <div className="section-panel comparison-chart"><div className="section-heading section-heading--compact"><div><h2>{t(`compare.${question}`)}</h2><p>{t('compare.chartSummary', { chartCount: chartRows.length, rowCount: rows.length, tableCount: Math.min(rows.length, 100) })}</p></div></div><ReactEChartsCore echarts={echarts} option={option} style={{ height: 410 }} /></div>
          <div className="section-panel comparison-table"><div className="data-table-wrap"><table className="data-table"><thead><tr>{columns.map((column) => <th key={column} title={column}>{fieldLabel(column, i18n.language)}</th>)}</tr></thead><tbody>{rows.slice(0, 100).map((row, index) => <tr key={`${question}-${index}`}>{columns.map((column) => <td key={column} title={row[column] ?? undefined}>{formatCell(column, row[column])}</td>)}</tr>)}</tbody></table></div></div>
        </section>
      ) : null}
    </div>
  )
}
