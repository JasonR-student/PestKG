import { describe, expect, it } from 'vitest'

import { categoryFromQuery, categoryLabel, categoryMatches } from './graph-categories'

describe('graph categories', () => {
  const types = ['PesticideProduct', 'LocalActiveIngredient', 'CropTerm', 'TargetTerm']
  it('resolves exact bilingual category names and common aliases', () => {
    for (const query of ['products', ' PRODUCT ', '农药产品', 'PesticideProduct']) {
      expect(categoryFromQuery(query, types)).toBe('PesticideProduct')
    }
    expect(categoryFromQuery('active ingredients', types)).toBe('LocalActiveIngredient')
    expect(categoryFromQuery('作物', types)).toBe('CropTerm')
    expect(categoryFromQuery('pests', types)).toBe('TargetTerm')
  })
  it('keeps name searches, unknown types and unavailable categories unchanged', () => {
    for (const query of ['', 'prod', 'Frutor Fungicide', 'glyphosate', 'CHEBI']) {
      expect(categoryFromQuery(query, types)).toBeUndefined()
    }
    expect(categoryFromQuery('products', ['ChEBITerm'])).toBeUndefined()
    expect(categoryLabel('UnknownTerm', true)).toBe('UnknownTerm')
  })
  it('filters partial names without converting them to category queries', () => {
    expect(categoryMatches('CropTerm', 'cro')).toBe(true)
    expect(categoryMatches('CropTerm', '作物')).toBe(true)
    expect(categoryMatches('CropTerm', 'products')).toBe(false)
    expect(categoryLabel('PesticideProduct', true)).toBe('Pesticide products')
    expect(categoryLabel('PesticideProduct', false)).toBe('农药产品')
  })
  it('deduplicates catalog types and refuses ambiguous aliases', () => {
    expect(categoryFromQuery('products', ['PesticideProduct', 'PesticideProduct'])).toBe('PesticideProduct')
    expect(categoryFromQuery('products', ['PesticideProduct', 'products'])).toBeUndefined()
  })
})
