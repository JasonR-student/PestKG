import { describe, expect, it } from 'vitest'

import { formatBytes, formatCompact, formatDate, formatInteger, humanize, preferredLabel } from './format'

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

  it('formats compact values using the selected language, not the browser locale', () => {
    expect(formatCompact(10_000, 'en')).toBe('10k')
    expect(formatCompact(1_200_000, 'en')).toBe('1.2M')
    expect(formatCompact(10_000, 'zh')).toBe('1万')
    expect(formatInteger(1103238, 'en')).toBe('1,103,238')
    expect(formatInteger(1103238, 'zh')).toBe('1,103,238')
  })

  it('formats source dates without applying a local timezone shift', () => {
    expect(formatDate('2026-09-23T23:59:59+08:00', 'en')).toBe('Sep 23, 2026')
    expect(formatDate('2026-09-23T23:59:59+08:00', 'zh')).toBe('2026年9月23日')
  })
})
