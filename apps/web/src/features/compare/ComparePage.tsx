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

const questions = {
  q1: { zh: '作物—有效成分跨国覆盖', en: 'Crop–ingredient coverage' },
  q2: { zh: '相同防治对象的登记产品', en: 'Products for a shared target' },
  q3: { zh: '共享作物—防治对象组合', en: 'Shared crop–target pairs' },
  q4: { zh: '有效成分与剂型', en: 'Ingredient formulations' },
  q5: { zh: '有效成分国家使用画像', en: 'Country use profiles' },
}

const chartFields: Record<string, { label: string; value: string }> = {
  q1: { label: 'active_ingredient_label_en', value: 'registration_use_count' },
  q2: { label: 'product_name', value: 'registration_use_count' },
  q3: { label: 'crop_label_en', value: 'registration_use_count' },
  q4: { label: 'formulation_label_en', value: 'product_count' },
  q5: { label: 'jurisdiction', value: 'registration_use_count' },
}

export function ComparePage() {
  const { i18n } = useTranslation()
  const english = i18n.language.startsWith('en')
  const { releaseId } = useRelease()
  const [question, setQuestion] = useState<keyof typeof questions>('q1')
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
  const option = {
    animationDuration: 400,
    color: ['#205b4f'],
    grid: { left: 150, right: 54, top: 10, bottom: 30 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#e8ece9' } } },
    yAxis: { type: 'category', data: chartLabels, axisLabel: { width: 130, overflow: 'truncate' } },
    series: [{ type: 'bar', data: chartRows.map((row) => Number(row[chart.value] || 0)), barMaxWidth: 18, label: { show: true, position: 'right', color: '#44534e', fontSize: 9 } }],
    media: [{ query: { maxWidth: 520 }, option: { grid: { left: 72, right: 42 }, yAxis: { axisLabel: { width: 62, overflow: 'truncate' } } } }],
  }

  return (
    <div className="page-stack">
      <PageHeader
        title={english ? 'Cross-country competency questions' : '跨国研究问题比较'}
        description={english ? 'Published Q1–Q5 results use shared semantic alignments without merging local regulatory entities.' : 'Q1–Q5 通过共享语义对齐进行比较，同时保留各司法辖区本地实体。'}
      />
      <div className="question-tabs" role="tablist">
        {Object.entries(questions).map(([key, label]) => (
          <button key={key} role="tab" type="button" aria-selected={question === key} className={question === key ? 'is-active' : ''} onClick={() => setQuestion(key as keyof typeof questions)}><strong>{key.toUpperCase()}</strong><span>{english ? label.en : label.zh}</span></button>
        ))}
      </div>
      <section className="comparison-toolbar">
        <label className="field field--wide"><span>{english ? 'Search result set' : '搜索结果集'}</span><div className="input-with-icon"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} /></div></label>
        <label className="field"><span>{english ? 'Jurisdiction' : '司法辖区'}</span><select value={jurisdiction} onChange={(event) => setJurisdiction(event.target.value)}><option value="">All</option>{countries.data?.data.map((country) => <option key={country.jurisdiction} value={country.jurisdiction}>{country.jurisdiction} · {country.jurisdiction_name}</option>)}</select></label>
      </section>
      {comparison.isLoading ? <LoadingState /> : null}
      {comparison.isError ? <ErrorState message={comparison.error.message} /> : null}
      {comparison.isSuccess ? (
        <section className="comparison-layout">
          <div className="section-panel comparison-chart"><div className="section-heading section-heading--compact"><div><h2>{questions[question][english ? 'en' : 'zh']}</h2><p>{english ? `Chart shows top ${chartRows.length} of ${rows.length}; table shows first ${Math.min(rows.length, 100)}.` : `图表展示前 ${chartRows.length} 项（共 ${rows.length} 项）；表格展示前 ${Math.min(rows.length, 100)} 项。`}</p></div></div><ReactEChartsCore echarts={echarts} option={option} style={{ height: 410 }} /></div>
          <div className="section-panel comparison-table"><div className="data-table-wrap"><table className="data-table"><thead><tr>{columns.map((column) => <th key={column}>{column.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{rows.slice(0, 100).map((row, index) => <tr key={`${question}-${index}`}>{columns.map((column) => <td key={column} title={row[column] ?? undefined}>{row[column] || '—'}</td>)}</tr>)}</tbody></table></div></div>
        </section>
      ) : null}
    </div>
  )
}
