export function formatCompact(value: number): string {
  return new Intl.NumberFormat(undefined, {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

export function formatInteger(value: number): string {
  return new Intl.NumberFormat().format(value)
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
  return value
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/^./, (character) => character.toUpperCase())
}
