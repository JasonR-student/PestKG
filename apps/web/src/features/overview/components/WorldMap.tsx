import { geoNaturalEarth1, geoPath } from 'd3-geo'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { feature } from 'topojson-client'
import world from 'world-atlas/countries-110m.json'

import { formatCompact } from '../../../shared/lib/format'
import type { Country } from '../../../shared/api/models'

type Props = {
  countries: Country[]
  onSelect: (jurisdiction: string) => void
}

const palette = ['#dce4e0', '#b9cec7', '#75a69a', '#356f62', '#17493f']

export function WorldMap({ countries, onSelect }: Props) {
  const { i18n } = useTranslation()
  const english = i18n.language.startsWith('en')
  const geometry = useMemo(() => {
    const collection = feature(
      world as never,
      (world as unknown as { objects: { countries: never } }).objects.countries,
    ) as unknown as GeoJSON.FeatureCollection
    const projection = geoNaturalEarth1().fitSize([900, 430], collection)
    const path = geoPath(projection)
    return { features: collection.features, path }
  }, [])

  const byMapId = useMemo(() => {
    const result = new Map<string, Country[]>()
    for (const country of countries) {
      const key = String(Number(country.map_id))
      result.set(key, [...(result.get(key) ?? []), country])
    }
    return result
  }, [countries])

  const maxNodes = Math.max(...countries.map((country) => country.nodes), 1)

  return (
    <div className="world-map">
      <svg viewBox="0 0 900 430" role="img" aria-label={english ? 'Knowledge graph coverage map' : '知识图谱司法辖区覆盖地图'}>
        {geometry.features.map((countryFeature, featureIndex) => {
          const mapId = String(Number(countryFeature.id))
          const mapped = byMapId.get(mapId)
          const nodes = mapped?.reduce((total, country) => total + country.nodes, 0) ?? 0
          const intensity = nodes
            ? Math.min(
                palette.length - 1,
                Math.max(1, Math.ceil((Math.log10(nodes) / Math.log10(maxNodes)) * 4)),
              )
            : 0
          const label = mapped
            ? `${mapped.map((item) => item.jurisdiction_name).join(' / ')}: ${formatCompact(nodes)} nodes`
            : english ? 'No release data' : '当前版本无数据'
          const selectMappedCountry = () => mapped && onSelect(mapped[0].jurisdiction)
          return (
            <path
              key={countryFeature.id == null ? `feature-${featureIndex}` : String(countryFeature.id)}
              d={geometry.path(countryFeature) ?? undefined}
              fill={palette[intensity]}
              className={mapped ? 'map-country map-country--active' : 'map-country'}
              data-jurisdiction={mapped?.[0].jurisdiction}
              role={mapped ? 'button' : undefined}
              tabIndex={mapped ? 0 : undefined}
              aria-label={mapped ? label : undefined}
              onClick={selectMappedCountry}
              onKeyDown={(event) => {
                if (mapped && (event.key === 'Enter' || event.key === ' ')) {
                  event.preventDefault()
                  selectMappedCountry()
                }
              }}
            >
              <title>{label}</title>
            </path>
          )
        })}
      </svg>
      <div className="map-legend" aria-hidden="true">
        <span>{english ? 'Lower' : '较低'}</span>
        {palette.slice(1).map((color) => (
          <i key={color} style={{ backgroundColor: color }} />
        ))}
        <span>{english ? 'Higher node volume' : '较高节点量'}</span>
      </div>
    </div>
  )
}
