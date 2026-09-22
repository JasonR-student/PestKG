import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  zh: {
    translation: {
      brand: '农药登记知识图谱',
      brandShort: 'PestKG',
      nav: {
        overview: '研究概览',
        explore: '数据探索',
        compare: '跨国比较',
        downloads: '数据下载',
        methods: '方法与质量',
      },
      common: {
        loading: '正在读取数据',
        error: '数据暂时无法读取',
        reset: '重置',
        apply: '应用筛选',
        search: '搜索',
        all: '全部',
        view: '查看',
        source: '官方来源',
        release: '数据版本',
        sampleMode: '真实样例模式',
        fullMode: '全量数据模式',
        rows: '条记录',
        noData: '没有符合条件的数据',
      },
    },
  },
  en: {
    translation: {
      brand: 'Pesticide Registration Knowledge Graph',
      brandShort: 'PestKG',
      nav: {
        overview: 'Overview',
        explore: 'Explore',
        compare: 'Compare',
        downloads: 'Downloads',
        methods: 'Methods & quality',
      },
      common: {
        loading: 'Loading research data',
        error: 'The data service is unavailable',
        reset: 'Reset',
        apply: 'Apply filters',
        search: 'Search',
        all: 'All',
        view: 'View',
        source: 'Official source',
        release: 'Release',
        sampleMode: 'Real-data sample',
        fullMode: 'Full release',
        rows: 'records',
        noData: 'No matching data',
      },
    },
  },
}

void i18n.use(initReactI18next).init({
  resources,
  lng: window.localStorage.getItem('pestkg-language') ?? 'zh',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export default i18n
