import { echarts } from '../../../shared/charts/echarts'
import { ReactEChartsCore } from '../../../shared/charts/react-echarts-core'
import type { CoverageRecord } from '../../../shared/api/models'
import { useTranslation } from 'react-i18next'

export function CoverageChart({ coverage, language: _language }: { coverage: CoverageRecord[]; language: string }) {
  const { t } = useTranslation()
  const option = {
    animationDuration: 500,
    color: ['#205b4f', '#c06144', '#3c6e97', '#a87c2c'],
    tooltip: { trigger: 'axis', valueFormatter: (value: number) => `${Math.round(value * 100)}%` },
    legend: { bottom: 0, itemWidth: 10, itemHeight: 10 },
    grid: { left: 42, right: 18, top: 16, bottom: 68 },
    xAxis: {
      type: 'category',
      data: coverage.map((item) => item.jurisdiction),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#cad2ce' } },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLabel: { formatter: (value: number) => `${Math.round(value * 100)}%` },
      splitLine: { lineStyle: { color: '#e8ece9' } },
    },
    series: [
      {
        name: t('fieldLabels.crop'),
        type: 'bar',
        data: coverage.map((item) => Number(item.crop_english_given_source || 0)),
      },
      {
        name: t('fieldLabels.target'),
        type: 'bar',
        data: coverage.map((item) => Number(item.target_english_given_source || 0)),
      },
      {
        name: t('fieldLabels.activeIngredient'),
        type: 'bar',
        data: coverage.map((item) => Number(item.active_english_given_source || 0)),
      },
      {
        name: t('fieldLabels.formulation'),
        type: 'bar',
        data: coverage.map((item) => Number(item.formulation_english_given_source || 0)),
      },
    ],
  }

  return <ReactEChartsCore echarts={echarts} option={option} style={{ height: 360 }} notMerge />
}
