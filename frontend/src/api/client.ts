/**
 * Fetch wrapper for the planning API.
 *
 * Every failure becomes an ApiError with a kind the UI can show honestly:
 * a bad workbook, a server problem, a network problem or a timeout.
 */

import type { PlanResponse, ValidationIssue } from './types'

export type ApiErrorKind = 'validation' | 'server' | 'network' | 'timeout' | 'bad_request'

const DEFAULT_TIMEOUT_MS = 20_000

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly issues: ValidationIssue[]

  constructor(kind: ApiErrorKind, message: string, issues: ValidationIssue[] = []) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.issues = issues
  }
}

interface ErrorBody {
  error?: string
  message?: string
  errors?: ValidationIssue[]
}

async function request<T>(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)

  let response: Response
  try {
    response = await fetch(path, { ...init, signal: controller.signal })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') {
      throw new ApiError('timeout', 'The server took too long to answer.')
    }
    throw new ApiError('network', 'The server could not be reached. Check that it is running.')
  } finally {
    window.clearTimeout(timer)
  }

  if (response.ok) {
    return (await response.json()) as T
  }

  let body: ErrorBody = {}
  try {
    body = (await response.json()) as ErrorBody
  } catch {
    // An error response without JSON is treated as a plain server problem.
  }

  if (response.status === 422 && body.error === 'VALIDATION_FAILED') {
    const issues = body.errors ?? []
    throw new ApiError('validation', `The workbook has ${issues.length} problems.`, issues)
  }
  if (response.status === 422) {
    throw new ApiError('bad_request', body.message ?? 'The request was not understood.')
  }
  throw new ApiError('server', body.message ?? 'Something went wrong on the server.')
}

/** Load today's workbook from the server and build the plan. */
export function loadSeedPlan(): Promise<PlanResponse> {
  return request<PlanResponse>('/api/plan/seed', { method: 'POST' })
}
