import { humanize } from './format'

type Language = string

const nodeTypes: Record<string, [string, string]> = {
  Jurisdiction: ['Jurisdictions', '辖区'],
  CountryOrTerritory: ['Countries and territories', '国家与地区'],
  Source: ['Sources', '来源'],
  SourceSnapshot: ['Source snapshots', '来源快照'],
  RegistrationUse: ['Registered uses', '登记使用'],
  Registration: ['Registrations', '登记'],
  PesticideProduct: ['Pesticide products', '农药产品'],
  LocalActiveIngredient: ['Local active ingredients', '本地有效成分'],
  CropTerm: ['Crops', '作物'],
  TargetTerm: ['Pests and targets', '防治对象'],
  FormulationTerm: ['Formulations', '剂型'],
  RegulatoryOrganization: ['Regulatory organizations', '监管机构'],
  ChEBITerm: ['ChEBI terms', 'ChEBI 本体术语'],
  AGROVOCConcept: ['AGROVOC concepts', 'AGROVOC 概念'],
  MoAGroup: ['Modes of action', '作用机制组'],
  ChemicalEntity: ['Reference chemicals', '参考化学实体'],
  ActiveIngredient: ['Reference active ingredients', '参考有效成分'],
  ChemicalClass: ['Chemical classes', '化学类别'],
  Synonym: ['Synonyms', '同义词'],
  ClassificationDocument: ['Classification documents', '分类文档'],
  DocumentPage: ['Document pages', '文档页'],
  MicroorganismTaxon: ['Microorganism taxa', '微生物分类'],
  AnimalTaxon: ['Animal taxa', '动物分类'],
  TaxonOrCommodity: ['Taxa and commodities', '生物分类与商品'],
  CropOrPlantTaxon: ['Crop and plant taxa', '作物与植物分类'],
  MultilingualLabel: ['Multilingual labels', '多语言标签'],
}

const relations: Record<string, [string, string]> = {
  HAS_REGISTRATION_USE: ['Has registration use', '包含登记使用'],
  HAS_REGISTRATION: ['Has registration', '包含登记'],
  USES_ACTIVE_INGREDIENT: ['Uses active ingredient', '使用有效成分'],
  APPLIES_TO_CROP: ['Applies to crop', '适用于作物'],
  TARGETS: ['Targets', '防治对象'],
  HAS_FORMULATION: ['Has formulation', '剂型为'],
  FROM_SOURCE: ['From source', '来源于'],
  HAS_SOURCE_SNAPSHOT: ['Has source snapshot', '包含来源快照'],
  IN_JURISDICTION: ['In jurisdiction', '位于辖区'],
  SAME_AS: ['Same as', '同一实体'],
  DERIVED_FROM: ['Derived from', '派生自'],
  HAS_LABEL: ['Has label', '包含标签'],
}

const artifactCategories: Record<string, [string, string]> = {
  canonical: ['Canonical data', '规范数据'],
  knowledge_graph: ['Knowledge graph', '知识图谱'],
  metadata: ['Metadata', '元数据'],
  docs: ['Documentation', '文档'],
  sample: ['Sample data', '样例数据'],
}

const fields: Record<string, [string, string]> = {
  jurisdiction: ['Jurisdiction', '监管辖区'],
  product: ['Product', '产品'],
  ingredient: ['Active ingredient', '有效成分'],
  active_ingredient: ['Active ingredient', '有效成分'],
  crop: ['Crop', '作物'],
  target: ['Target', '防治对象'],
  formulation: ['Formulation', '剂型'],
  source: ['Source', '来源'],
  active_ingredient_label_en: ['Active ingredient', '有效成分'],
  crop_label_en: ['Crop', '作物'],
  formulation_label_en: ['Formulation', '剂型'],
  registration_use_count: ['Registration use count', '登记使用数量'],
  product_count: ['Product count', '产品数量'],
}

function english(language: Language) {
  return language.startsWith('en')
}

export function nodeTypeLabel(type: string, language: Language) {
  return nodeTypes[type]?.[english(language) ? 0 : 1] ?? humanize(type)
}

export function relationLabel(predicate: string, language: Language) {
  return relations[predicate]?.[english(language) ? 0 : 1] ?? humanize(predicate)
}

export function artifactCategoryLabel(category: string, language: Language) {
  return artifactCategories[category]?.[english(language) ? 0 : 1] ?? humanize(category)
}

export function fieldLabel(field: string, language: Language) {
  return fields[field]?.[english(language) ? 0 : 1] ?? humanize(field)
}

export function statusLabel(status: string | null | undefined, language: Language) {
  const key = status?.toUpperCase() ?? ''
  const mapped: Record<string, [string, string]> = {
    INTERNAL_RESEARCH_RELEASE: ['Internal research release', '内部研究版本'],
    ALLOWED_DEC_002: ['Distribution restricted', '限制分发'],
    READY: ['Ready', '已就绪'],
    PASSED: ['Passed', '通过'],
    FAILED: ['Failed', '失败'],
    ACTIVE: ['Active', '当前'],
  }
  return mapped[key]?.[english(language) ? 0 : 1] ?? humanize(status ?? '')
}
