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

/** Set one filter to an exact value, or clear it with null. */
export function setFilter(current: Selection, kind: EntityKind, id: string | null): Selection {
  if (kind === 'farm') return { ...current, farmId: id }
  if (kind === 'client') return { ...current, clientId: id }
  return { ...current, segment: (id as Segment) ?? null }
}

export interface SelectionChip {
  kind: EntityKind
  id: string
  label: string
}

export function selectionChips(selection: Selection): SelectionChip[] {
  const chips: SelectionChip[] = []
  if (selection.farmId) chips.push({ kind: 'farm', id: selection.farmId, label: `Farm ${selection.farmId}` })
  if (selection.clientId)
    chips.push({ kind: 'client', id: selection.clientId, label: `Client ${selection.clientId}` })
  if (selection.segment)
    chips.push({ kind: 'segment', id: selection.segment, label: `Segment ${selection.segment}` })
  return chips
}
