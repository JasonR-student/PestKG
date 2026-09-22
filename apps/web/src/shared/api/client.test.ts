import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, ApiError } from './client'
import type { RegistrationUseFilters } from './models'

const emptyFilters: RegistrationUseFilters = {
  jurisdictions: [],
  query: '',
  product: '',
  active_ingredient: '',
  crop: '',
  target: '',
  formulation: '',
  registration_status: '',
  pairing_status: '',
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('API client', () => {
  it('sends release, request ID, and abort signal headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: { version: '2026.08.3_federated' } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()

    await api.overview('2026.08.3_federated', controller.signal)

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const headers = new Headers(init.headers)
    expect(url).toBe('/api/v1/stats/overview')
    expect(init.signal).toBe(controller.signal)
    expect(headers.get('X-PestKG-Release')).toBe('2026.08.3_federated')
    expect(headers.get('X-Request-ID')).toBeTruthy()
  })

  it('normalizes optional filters and posts JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.registrationUses(emptyFilters, 'cursor-1', 25)

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    const body = JSON.parse(String(init.body))
    expect(init.method).toBe('POST')
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
    expect(body).toMatchObject({ cursor: 'cursor-1', page_size: 25 })
    expect(body.filters).toEqual({ jurisdictions: [], query: null, product: null,
      active_ingredient: null, crop: null, target: null, formulation: null,
      registration_status: null, pairing_status: null })
  })

  it('maps compatible detail errors and response request IDs', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        detail: { code: 'invalid_cursor', message: 'Cursor is invalid' },
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json', 'X-Request-ID': 'request-42' },
      }),
    ))

    const error = await api.registrationUses(emptyFilters).catch((reason: unknown) => reason)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      code: 'invalid_cursor',
      message: 'Cursor is invalid',
      status: 400,
      requestId: 'request-42',
    })
  })

  it('returns CSV exports as blobs', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response('use_id,jurisdiction\nAU:1,AU\n', {
        status: 200,
        headers: { 'Content-Type': 'text/csv' },
      }),
    ))

    const blob = await api.exportRegistrationUses(emptyFilters)
    expect(blob.type).toBe('text/csv')
    expect(await blob.text()).toContain('use_id,jurisdiction')
  })
})
