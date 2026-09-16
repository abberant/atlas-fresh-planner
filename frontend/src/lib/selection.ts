/** What the user has clicked. One selection drives every view. */

import type { Segment } from '../api/types'

export type TabId = 'production' | 'commercial' | 'allocations'
export type EntityKind = 'farm' | 'client' | 'segment'

export interface Selection {
  farmId: string | null
  clientId: string | null
  segment: Segment | null
}

export const NO_SELECTION: Selection = { farmId: null, clientId: null, segment: null }

/** Which tab answers a click on this kind of ID. */
export const TAB_FOR_KIND: Record<EntityKind, TabId> = {
  farm: 'production',
  client: 'commercial',
  segment: 'allocations',
}

export function withSelection(current: Selection, kind: EntityKind, id: string): Selection {
  if (kind === 'farm') return { ...current, farmId: current.farmId === id ? null : id }
  if (kind === 'client') return { ...current, clientId: current.clientId === id ? null : id }
  const segment = id as Segment
  return { ...current, segment: current.segment === segment ? null : segment }
}

export function isEmpty(selection: Selection): boolean {
  return !selection.farmId && !selection.clientId && !selection.segment
}
