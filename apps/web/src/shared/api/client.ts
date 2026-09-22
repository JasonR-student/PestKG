import type {
  ApiEnvelope,
  ComparisonRow,
  Country,
  Entity,
  GraphData,
  Overview,
  RegistrationUse,
  RegistrationUseFilters,
  Release,
  Schema,
} from './models'

const API_ROOT = import.meta.env.VITE_API_ROOT ?? '/api/v1'

type RequestOptions = RequestInit & {
  releaseId?: string | null
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly requestId: string | null

  constructor(
    code: string,
    message: string,
    status: number,
    requestId: string | null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.requestId = requestId
  }
}

function releaseHeaders(releaseId?: string | null): Record<string, string> {
  return releaseId ? { 'X-PestKG-Release': releaseId } : {}
}

function requestHeaders(options: RequestOptions): Headers {
  const headers = new Headers(options.headers)
  headers.set('X-Request-ID', crypto.randomUUID())
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  for (const [name, value] of Object.entries(releaseHeaders(options.releaseId))) {
    headers.set(name, value)
  }
  return headers
}

async function parseApiError(response: Response): Promise<ApiError> {
  const body = await response.json().catch(() => null)
  return new ApiError(
    body?.error?.code ?? body?.detail?.code ?? `http_${response.status}`,
    body?.error?.message
      ?? body?.detail?.message
      ?? body?.detail
      ?? `Request failed: ${response.status}`,
    response.status,
    response.headers.get('X-Request-ID'),
  )
}

async function fetchResponse(path: string, options: RequestOptions = {}): Promise<Response> {
  const { releaseId: _releaseId, ...init } = options
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: requestHeaders(options),
  })
  if (!response.ok) throw await parseApiError(response)
  return response
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiEnvelope<T>> {
  const response = await fetchResponse(path, options)
  return response.json() as Promise<ApiEnvelope<T>>
}

function nullableFilters(filters: RegistrationUseFilters) {
  return {
    ...filters,
    query: filters.query || null,
    product: filters.product || null,
    active_ingredient: filters.active_ingredient || null,
    crop: filters.crop || null,
    target: filters.target || null,
    formulation: filters.formulation || null,
    registration_status: filters.registration_status || null,
    pairing_status: filters.pairing_status || null,
  }
}

export const api = {
  overview: (releaseId?: string | null, signal?: AbortSignal) =>
    request<Overview>('/stats/overview', { releaseId, signal }),
  countries: (releaseId?: string | null, signal?: AbortSignal) =>
    request<Country[]>('/stats/countries', { releaseId, signal }),
  schema: (releaseId?: string | null, signal?: AbortSignal) =>
    request<Schema>('/schema', { releaseId, signal }),
  releases: (signal?: AbortSignal) => request<Release[]>('/releases', { signal }),
  search: (
    params: URLSearchParams,
    releaseId?: string | null,
    signal?: AbortSignal,
  ) => request<Entity[]>(`/search?${params.toString()}`, { releaseId, signal }),
  entity: (nodeId: string, releaseId?: string | null, signal?: AbortSignal) =>
    request<Entity>(`/entities/${encodeURIComponent(nodeId)}`, { releaseId, signal }),
  neighborhood: (
    nodeId: string,
    depth = 1,
    releaseId?: string | null,
    signal?: AbortSignal,
  ) => request<GraphData>(
    `/graph/neighborhood?node_id=${encodeURIComponent(nodeId)}&depth=${depth}`,
    { releaseId, signal },
  ),
  path: (
    startId: string,
    endId: string,
    releaseId?: string | null,
    signal?: AbortSignal,
  ) => request<GraphData>(
    `/graph/path?start_id=${encodeURIComponent(startId)}&end_id=${encodeURIComponent(endId)}`,
    { releaseId, signal },
  ),
  registrationUses: (
    filters: RegistrationUseFilters,
    cursor: string | null = null,
    pageSize = 50,
    releaseId?: string | null,
    signal?: AbortSignal,
  ) => request<RegistrationUse[]>('/registration-uses/query', {
    method: 'POST',
    releaseId,
    signal,
    body: JSON.stringify({
      filters: nullableFilters(filters),
      cursor,
      page_size: pageSize,
    }),
  }),
  comparison: (
    question: string,
    query: string,
    jurisdiction: string,
    releaseId?: string | null,
    signal?: AbortSignal,
  ) => {
    const params = new URLSearchParams({ limit: '200' })
    if (query) params.set('q', query)
    if (jurisdiction) params.set('jurisdiction', jurisdiction)
    return request<ComparisonRow[]>(`/compare/${question}?${params.toString()}`, {
      releaseId,
      signal,
    })
  },
  exportRegistrationUses: async (
    filters: RegistrationUseFilters,
    releaseId?: string | null,
    signal?: AbortSignal,
  ) => {
    const response = await fetchResponse('/exports/registration-uses', {
      method: 'POST',
      releaseId,
      signal,
      body: JSON.stringify({ filters: nullableFilters(filters) }),
    })
    return response.blob()
  },
}
