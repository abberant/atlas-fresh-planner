/**
 * Fetch wrapper for the planning API.
 *
 * Every failure becomes an ApiError with a kind the UI can show honestly:
 * a bad workbook, a server problem, a network problem or a timeout.
 */

import type { AssistantResponse, PlanResponse, QuestionId, ValidationIssue } from './types'

export type ApiErrorKind =
  | 'validation'
  | 'server'
  | 'network'
  | 'timeout'
  | 'bad_request'
  | 'plan_expired'

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
  if (response.status === 404 && body.error === 'PLAN_NOT_FOUND') {
    throw new ApiError('plan_expired', body.message ?? 'This plan is no longer in memory.')
  }
  throw new ApiError('server', body.message ?? 'Something went wrong on the server.')
}

/** Load today's workbook from the server and build the plan. */
export function loadSeedPlan(): Promise<PlanResponse> {
  return request<PlanResponse>('/api/plan/seed', { method: 'POST' })
}

/** Ask the read only assistant about a plan the server still has in memory. */
export function askAssistant(
  planId: string,
  question: { questionId: QuestionId } | { questionText: string },
): Promise<AssistantResponse> {
  const payload =
    'questionId' in question
      ? { plan_id: planId, question_id: question.questionId }
      : { plan_id: planId, question_text: question.questionText }

  return request<AssistantResponse>('/api/assistant/ask', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
