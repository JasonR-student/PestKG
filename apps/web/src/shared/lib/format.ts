type Language = string | undefined

function isChinese(language: Language) {
  return language?.startsWith('zh') ?? false
}

function formatScaled(value: number, suffix: string) {
  const number = new Intl.NumberFormat('en-US', {
    maximumFractionDigits: 1,
    minimumFractionDigits: 0,
    useGrouping: false,
  }).format(value)
  return `${number}${suffix}`
}

export function formatCompact(value: number, language: Language = 'en'): string {
  if (isChinese(language)) {
    return new Intl.NumberFormat('zh-CN', {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value)
  }

  const absolute = Math.abs(value)
  if (absolute >= 1_000_000_000) return formatScaled(value / 1_000_000_000, 'B')
  if (absolute >= 1_000_000) return formatScaled(value / 1_000_000, 'M')
  if (absolute >= 1_000) return formatScaled(value / 1_000, 'k')
  return formatInteger(value, language)
}

export function formatInteger(value: number, language: Language = 'en'): string {
  return new Intl.NumberFormat(isChinese(language) ? 'zh-CN' : 'en-US').format(value)
}

export function formatDate(value: string | null | undefined, language: Language = 'en'): string {
  if (!value) return '—'
  const datePart = value.slice(0, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(datePart)) return value
  const date = new Date(`${datePart}T00:00:00Z`)
  if (isChinese(language)) {
    return `${date.getUTCFullYear()}年${date.getUTCMonth() + 1}月${date.getUTCDate()}日`
  }
  return new Intl.DateTimeFormat(isChinese(language) ? 'zh-CN' : 'en-US', {
    timeZone: 'UTC',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

export function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let size = value / 1024
  let unit = units[0]
  for (let index = 1; index < units.length && size >= 1024; index += 1) {
    size /= 1024
    unit = units[index]
  }
  return `${size >= 10 ? size.toFixed(0) : size.toFixed(1)} ${unit}`
}

export function preferredLabel(
  value: { label_original?: string | null; label_en?: string | null },
  language: string,
): string {
  if (language.startsWith('en')) {
    return value.label_en || value.label_original || 'Untitled'
  }
  return value.label_original || value.label_en || '未命名'
}

export function humanize(value: string): string {
  const result = value
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/^./, (character) => character.toUpperCase())
  return result
    .replace(/\bApi\b/g, 'API')
    .replace(/\bId\b/g, 'ID')
    .replace(/\bUrl\b/g, 'URL')
    .replace(/\bKg\b/g, 'KG')
    .replace(/\bSha256\b/g, 'SHA-256')
}
