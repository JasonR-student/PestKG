const names: Record<string, [string, string]> = {
  AU: ['澳大利亚', 'Australia'], CN: ['中国大陆', 'China (mainland)'],
  GB: ['大不列颠辖区', 'Great Britain'], 'GB-NI': ['北爱尔兰辖区', 'Northern Ireland'],
  HU: ['匈牙利', 'Hungary'], IE: ['爱尔兰', 'Ireland'], JP: ['日本', 'Japan'],
  KR: ['韩国', 'Republic of Korea'], NL: ['荷兰', 'Netherlands'], NZ: ['新西兰', 'New Zealand'],
  TW: ['台湾地区', 'Taiwan region'], US: ['美国', 'United States'],
}

export function jurisdictionName(code: string, english: boolean) {
  return names[code]?.[english ? 1 : 0] ?? code
}
