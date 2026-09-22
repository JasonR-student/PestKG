import type {
  ComparisonRow as GeneratedComparisonRow,
  CountryData,
  CoverageRecord as GeneratedCoverageRecord,
  EdgeData,
  EntityData,
  EntityRef as GeneratedEntityRef,
  EnvelopeOverviewData,
  GraphData as GeneratedGraphData,
  OverviewData,
  RegistrationUseData,
  RegistrationUseFilters as ApiRegistrationUseFilters,
  ReleaseData,
  SchemaData,
} from './generated'

type EnvelopeBase = Omit<EnvelopeOverviewData, 'data'>

export type ApiEnvelope<T> = EnvelopeBase & { data: T }
export type CoverageRecord = GeneratedCoverageRecord
export type ComparisonRow = GeneratedComparisonRow
export type Overview = OverviewData
export type Country = CountryData
export type EntityRef = GeneratedEntityRef
export type Entity = EntityData
export type Edge = EdgeData
export type GraphData = GeneratedGraphData
export type RegistrationUse = RegistrationUseData
export type Schema = SchemaData
export type Release = ReleaseData

type TextFilterKey =
  | 'query'
  | 'product'
  | 'active_ingredient'
  | 'crop'
  | 'target'
  | 'formulation'
  | 'registration_status'
  | 'pairing_status'

export type RegistrationUseFilters = {
  jurisdictions: string[]
} & {
  [Key in TextFilterKey]: NonNullable<ApiRegistrationUseFilters[Key]>
}
