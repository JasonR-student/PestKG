const categories: Record<string, { en: string; zh: string; aliases?: string[] }> = {
  Jurisdiction: { en: 'Jurisdictions', zh: '辖区', aliases: ['jurisdiction'] },
  CountryOrTerritory: { en: 'Countries and territories', zh: '国家与地区' },
  Source: { en: 'Sources', zh: '来源', aliases: ['source', 'websites'] },
  SourceSnapshot: { en: 'Source snapshots', zh: '来源快照', aliases: ['snapshots'] },
  RegistrationUse: { en: 'Registered uses', zh: '登记使用', aliases: ['uses', 'registration uses'] },
  Registration: { en: 'Registrations', zh: '登记', aliases: ['registration'] },
  PesticideProduct: { en: 'Pesticide products', zh: '农药产品', aliases: ['products', 'product', 'pesticide product', '产品'] },
  LocalActiveIngredient: { en: 'Active ingredients (local)', zh: '本地有效成分', aliases: ['active ingredients', 'active ingredient', 'ingredients', '有效成分'] },
  CropTerm: { en: 'Crops', zh: '作物', aliases: ['crop', 'crop terms', '作物术语'] },
  TargetTerm: { en: 'Pests and targets', zh: '防治对象', aliases: ['pests', 'pest', 'targets', 'target', '害虫'] },
  FormulationTerm: { en: 'Formulations', zh: '剂型', aliases: ['formulation'] },
  RegulatoryOrganization: { en: 'Regulatory organizations', zh: '监管机构', aliases: ['regulators'] },
  ChEBITerm: { en: 'ChEBI terms', zh: 'ChEBI 本体术语', aliases: ['chebi'] },
  AGROVOCConcept: { en: 'AGROVOC concepts', zh: 'AGROVOC 概念', aliases: ['agrovoc'] },
  MoAGroup: { en: 'Modes of action', zh: '作用机制组', aliases: ['mode of action', 'moa'] },
  ChemicalEntity: { en: 'Reference chemicals', zh: '参考化学实体' },
  ActiveIngredient: { en: 'Reference active ingredients', zh: '参考有效成分' },
  ChemicalClass: { en: 'Chemical classes', zh: '化学类别' },
  Synonym: { en: 'Synonyms', zh: '同义词', aliases: ['synonym'] },
  ClassificationDocument: { en: 'Classification documents', zh: '分类文档' },
  DocumentPage: { en: 'Document pages', zh: '文档页' },
  MicroorganismTaxon: { en: 'Microorganism taxa', zh: '微生物分类' },
  AnimalTaxon: { en: 'Animal taxa', zh: '动物分类' },
  TaxonOrCommodity: { en: 'Taxa and commodities', zh: '生物分类与商品' },
  CropOrPlantTaxon: { en: 'Crop and plant taxa', zh: '作物与植物分类' },
  MultilingualLabel: { en: 'Multilingual labels', zh: '多语言标签' },
}

const normalize = (value: string) => value.trim().toLowerCase().replace(/[\s_-]+/g, ' ')
const names = (type: string) => {
  const category = categories[type]
  return [type, ...(category ? [category.en, category.zh, ...(category.aliases ?? [])] : [])].map(normalize)
}

export function categoryLabel(type: string, english: boolean): string {
  const category = categories[type]
  return category ? category[english ? 'en' : 'zh'] : type
}

export function categoryMatches(type: string, query: string): boolean {
  return names(type).some((name) => name.includes(normalize(query)))
}

export function categoryFromQuery(query: string, availableTypes: string[]): string | undefined {
  if (!query.trim()) return undefined
  const matches = [...new Set(availableTypes)].filter((type) => names(type).includes(normalize(query)))
  return matches.length === 1 ? matches[0] : undefined
}
