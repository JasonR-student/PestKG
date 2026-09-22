import { describe, expect, it } from 'vitest'

import { formatBytes, humanize, preferredLabel } from './format'

describe('format helpers', () => {
  it('prefers the requested language without losing the original label', () => {
    const entity = { label_original: '毒死蜱', label_en: 'Chlorpyrifos' }
    expect(preferredLabel(entity, 'zh')).toBe('毒死蜱')
    expect(preferredLabel(entity, 'en')).toBe('Chlorpyrifos')
  })

  it('humanizes graph identifiers', () => {
    expect(humanize('hasRegistrationUse')).toBe('Has registration use')
    expect(humanize('REGISTERED_FOR_CROP')).toBe('Registered for crop')
  })

  it('formats release artifact sizes', () => {
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(1536)).toBe('1.5 KB')
    expect(formatBytes(12 * 1024 * 1024)).toBe('12 MB')
  })
})
