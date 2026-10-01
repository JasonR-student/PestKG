import { describe, expect, it } from 'vitest'

import { artifactCategoryLabel, fieldLabel, nodeTypeLabel, relationLabel, statusLabel } from './labels'

describe('label mappings', () => {
  it('maps technical graph terms while keeping unknown values readable', () => {
    expect(nodeTypeLabel('PesticideProduct', 'en')).toBe('Pesticide products')
    expect(nodeTypeLabel('PesticideProduct', 'zh')).toBe('农药产品')
    expect(relationLabel('USES_ACTIVE_INGREDIENT', 'en')).toBe('Uses active ingredient')
    expect(relationLabel('USES_ACTIVE_INGREDIENT', 'zh')).toBe('使用有效成分')
    expect(fieldLabel('registration_use_count', 'en')).toBe('Registration use count')
    expect(artifactCategoryLabel('knowledge_graph', 'en')).toBe('Knowledge graph')
  })

  it('maps release and integrity statuses', () => {
    expect(statusLabel('INTERNAL_RESEARCH_RELEASE', 'en')).toBe('Internal research release')
    expect(statusLabel('ALLOWED_DEC_002', 'en')).toBe('Distribution restricted')
    expect(statusLabel('PASSED', 'zh')).toBe('通过')
    expect(statusLabel('FAILED', 'en')).toBe('Failed')
    expect(statusLabel('active', 'en')).toBe('Active')
  })
})
