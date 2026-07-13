import axios from 'axios'
import { computed, ref, watch } from 'vue'
import { deleteDigQueueItem, fetchDigQueue, saveDigQueueItem } from '../api/dossierApi'
import type { DigQueueRecord } from '../types/dossier'

export type DigQueueItem = {
  id: string
  topicId: number
  topicName: string
  eventId: number | null
  eventTitle: string
  view: 'contrast' | 'analogue'
  addedAt: string
  revision: number | null
}

type MutationBase = {
  schema: 1
  mutationId: string
  itemKey: string
  expectedRevision: number | null
  createdAt: string
  operationKey: string
  afterMutationId?: string
  afterResultRevision?: number
}

type UpsertMutation = MutationBase & {
  kind: 'upsert'
  item: DigQueueItem
}

type DeleteMutation = MutationBase & {
  kind: 'delete'
  legacyUnversioned?: boolean
}

type PendingMutation = UpsertMutation | DeleteMutation

type KnownState = {
  schema: 1
  itemKey: string
  revision: number
  deleted: boolean
}

type RemoteState = {
  item: DigQueueItem
  deleted: boolean
}

const STORAGE_KEY = 'message-platform:dig-queue:v1'
const LEGACY_SYNC_STORAGE_KEY = 'message-platform:dig-queue-sync:v1'
const OPERATION_PREFIX = 'message-platform:dig-queue-op:v1:'
const STATE_PREFIX = 'message-platform:dig-queue-state:v1:'
const memoryHost = globalThis as typeof globalThis & {
  __messagePlatformDigQueueMemory?: {
    operations: Map<string, PendingMutation>
    states: Map<string, KnownState>
  }
}
const digQueueMemory = memoryHost.__messagePlatformDigQueueMemory ?? {
  operations: new Map<string, PendingMutation>(),
  states: new Map<string, KnownState>(),
}
memoryHost.__messagePlatformDigQueueMemory = digQueueMemory
const memoryOperations = digQueueMemory.operations
const memoryKnownStates = digQueueMemory.states
let droppedMalformedOperation = false

export function digItemKey(topicId: number, eventId: number | null): string {
  return eventId == null ? `t:${topicId}` : `t:${topicId}:e:${eventId}`
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0
}

function isIsoDate(value: unknown): value is string {
  return typeof value === 'string' && value.trim() !== '' && Number.isFinite(Date.parse(value))
}

function isCanonicalItemKey(value: unknown): value is string {
  if (typeof value !== 'string') return false
  const match = /^t:([1-9]\d*)(?::e:([1-9]\d*))?$/.exec(value)
  if (!match) return false
  const topicId = Number(match[1])
  const eventId = match[2] ? Number(match[2]) : null
  return isPositiveInteger(topicId)
    && (eventId === null || isPositiveInteger(eventId))
    && value === digItemKey(topicId, eventId)
}

function parseDigQueueItem(value: unknown): DigQueueItem | null {
  if (!value || typeof value !== 'object') return null
  const item = value as Partial<DigQueueItem>
  if (
    !isPositiveInteger(item.topicId)
    || !(item.eventId === null || isPositiveInteger(item.eventId))
    || typeof item.id !== 'string'
    || item.id !== digItemKey(item.topicId, item.eventId)
    || typeof item.topicName !== 'string'
    || item.topicName.trim() === ''
    || typeof item.eventTitle !== 'string'
    || item.eventTitle.trim() === ''
    || (item.view !== 'contrast' && item.view !== 'analogue')
    || !isIsoDate(item.addedAt)
    || !(item.revision == null || isPositiveInteger(item.revision))
  ) {
    return null
  }
  return {
    id: item.id,
    topicId: item.topicId,
    topicName: item.topicName.trim(),
    eventId: item.eventId,
    eventTitle: item.eventTitle.trim(),
    view: item.view,
    addedAt: item.addedAt,
    revision: item.revision ?? null,
  }
}

function parseRemoteRecord(value: unknown): RemoteState | null {
  if (!value || typeof value !== 'object') return null
  const record = value as Partial<DigQueueRecord>
  if (
    !isPositiveInteger(record.id)
    || !isCanonicalItemKey(record.item_key)
    || typeof record.deleted !== 'boolean'
    || !isPositiveInteger(record.revision)
  ) {
    return null
  }
  const item = parseDigQueueItem({
    id: record.item_key,
    topicId: record.topic_id,
    topicName: record.topic_name,
    eventId: record.event_id,
    eventTitle: record.event_title,
    view: record.view,
    addedAt: record.added_at,
    revision: record.revision,
  })
  return item ? { item, deleted: record.deleted } : null
}

function loadFromStorage(): DigQueueItem[] {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '[]')
    if (!Array.isArray(parsed)) return []
    return parsed.map(parseDigQueueItem).filter((item): item is DigQueueItem => item !== null)
  } catch {
    return []
  }
}

function operationBaseKey(itemKey: string): string {
  return `${OPERATION_PREFIX}${encodeURIComponent(itemKey)}`
}

function operationStorageKey(itemKey: string, mutationId: string): string {
  return `${operationBaseKey(itemKey)}:${encodeURIComponent(mutationId)}`
}

function stateStorageKey(itemKey: string): string {
  return `${STATE_PREFIX}${encodeURIComponent(itemKey)}`
}

function readKnownState(itemKey: string): KnownState | null {
  const memoryState = memoryKnownStates.get(itemKey) ?? null
  try {
    const parsed = JSON.parse(window.localStorage.getItem(stateStorageKey(itemKey)) || 'null') as Partial<KnownState> | null
    if (
      parsed?.schema !== 1
      || parsed.itemKey !== itemKey
      || !isPositiveInteger(parsed.revision)
      || typeof parsed.deleted !== 'boolean'
    ) {
      return memoryState
    }
    const storedState: KnownState = {
      schema: 1,
      itemKey,
      revision: parsed.revision,
      deleted: parsed.deleted,
    }
    return memoryState && memoryState.revision > storedState.revision ? memoryState : storedState
  } catch {
    return memoryState
  }
}

function rememberKnownState(itemKey: string, revision: number, deleted: boolean): boolean {
  const current = readKnownState(itemKey)
  if (current && current.revision > revision) return false
  const state: KnownState = { schema: 1, itemKey, revision, deleted }
  try {
    window.localStorage.setItem(stateStorageKey(itemKey), JSON.stringify(state))
    memoryKnownStates.delete(itemKey)
  } catch {
    memoryKnownStates.set(itemKey, state)
  }
  return true
}

function clearKnownState(itemKey: string): void {
  memoryKnownStates.delete(itemKey)
  try {
    window.localStorage.removeItem(stateStorageKey(itemKey))
  } catch {
    // Ignore unavailable storage.
  }
}

function operationKeyMatches(storageKey: string, itemKey: string, mutationId: string): boolean {
  const baseKey = operationBaseKey(itemKey)
  return storageKey === baseKey || storageKey === operationStorageKey(itemKey, mutationId)
}

function parsePendingMutation(storageKey: string, raw: string): PendingMutation | null {
  try {
    const value = JSON.parse(raw) as Record<string, unknown>
    if (
      value.schema !== 1
      || typeof value.mutationId !== 'string'
      || value.mutationId.trim() === ''
      || !isCanonicalItemKey(value.itemKey)
      || value.operationKey !== storageKey
      || !operationKeyMatches(storageKey, value.itemKey, value.mutationId)
      || !isIsoDate(value.createdAt)
    ) {
      return null
    }
    const afterMutationId = typeof value.afterMutationId === 'string' && value.afterMutationId
      ? value.afterMutationId
      : undefined
    const afterResultRevision = isPositiveInteger(value.afterResultRevision)
      ? value.afterResultRevision
      : undefined
    const expectedRevision = value.expectedRevision == null
      ? null
      : isPositiveInteger(value.expectedRevision) ? value.expectedRevision : undefined
    if (expectedRevision === undefined || (afterResultRevision !== undefined && !afterMutationId)) {
      return null
    }
    if (afterMutationId && expectedRevision !== null) return null

    const common: MutationBase = {
      schema: 1,
      mutationId: value.mutationId,
      itemKey: value.itemKey,
      expectedRevision,
      createdAt: value.createdAt,
      operationKey: storageKey,
      ...(afterMutationId ? { afterMutationId } : {}),
      ...(afterResultRevision ? { afterResultRevision } : {}),
    }
    if (value.kind === 'upsert') {
      const item = parseDigQueueItem(value.item)
      if (
        !item
        || item.id !== value.itemKey
        || (afterMutationId ? item.revision !== null : item.revision !== expectedRevision)
      ) {
        return null
      }
      return { ...common, kind: 'upsert', item }
    }
    if (value.kind === 'delete') {
      const legacyUnversioned = value.legacyUnversioned === true
      if (expectedRevision === null && !afterMutationId && !legacyUnversioned) return null
      return { ...common, kind: 'delete', ...(legacyUnversioned ? { legacyUnversioned: true } : {}) }
    }
  } catch {
    return null
  }
  return null
}

function removeStoredOperation(storageKey: string): boolean {
  const removedFromMemory = memoryOperations.delete(storageKey)
  try {
    window.localStorage.removeItem(storageKey)
    return window.localStorage.getItem(storageKey) === null
  } catch {
    return removedFromMemory
  }
}

function storeOperation(mutation: PendingMutation): void {
  try {
    window.localStorage.setItem(mutation.operationKey, JSON.stringify(mutation))
    memoryOperations.delete(mutation.operationKey)
  } catch {
    memoryOperations.set(mutation.operationKey, mutation)
  }
}

function mutationDepth(
  mutation: PendingMutation,
  byId: Map<string, PendingMutation>,
  visiting = new Set<string>(),
): number {
  if (!mutation.afterMutationId) return 0
  if (visiting.has(mutation.mutationId)) return Number.MAX_SAFE_INTEGER
  const parent = byId.get(mutation.afterMutationId)
  if (!parent) return 1
  const nextVisiting = new Set(visiting)
  nextVisiting.add(mutation.mutationId)
  return 1 + mutationDepth(parent, byId, nextVisiting)
}

function sortMutations(mutations: PendingMutation[]): PendingMutation[] {
  const byId = new Map(mutations.map((mutation) => [mutation.mutationId, mutation]))
  return mutations.slice().sort((left, right) => (
    mutationDepth(left, byId) - mutationDepth(right, byId)
    || left.createdAt.localeCompare(right.createdAt)
    || left.mutationId.localeCompare(right.mutationId)
  ))
}

function loadPendingMutations(): PendingMutation[] {
  const operations = new Map(memoryOperations)
  const keys: string[] = []
  try {
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index)
      if (key?.startsWith(OPERATION_PREFIX)) keys.push(key)
    }
    for (const key of keys) {
      const raw = window.localStorage.getItem(key)
      const mutation = raw ? parsePendingMutation(key, raw) : null
      if (mutation) {
        operations.set(key, mutation)
      } else {
        droppedMalformedOperation = true
        removeStoredOperation(key)
        operations.delete(key)
      }
    }
  } catch {
    // Memory operations are still flushable.
  }
  return sortMutations([...operations.values()])
}

function latestMutation(itemKey: string): PendingMutation | null {
  const mutations = loadPendingMutations().filter((mutation) => mutation.itemKey === itemKey)
  if (!mutations.length) return null
  const predecessorIds = new Set(
    mutations.map((mutation) => mutation.afterMutationId).filter((value): value is string => Boolean(value)),
  )
  const tails = mutations.filter((mutation) => !predecessorIds.has(mutation.mutationId))
  return (tails.length ? tails : mutations).at(-1) ?? null
}

function predictedResultRevision(mutation: PendingMutation): number | null {
  if (mutation.afterResultRevision) return mutation.afterResultRevision + 1
  if (mutation.expectedRevision) return mutation.expectedRevision + 1
  if (mutation.kind === 'upsert' && !mutation.afterMutationId) return 1
  return null
}

function applyPendingMutations(
  baseItems: DigQueueItem[],
  pending = loadPendingMutations(),
): DigQueueItem[] {
  let next = [...baseItems]
  for (const mutation of sortMutations(pending)) {
    next = next.filter((item) => item.id !== mutation.itemKey)
    if (mutation.kind === 'upsert') next.unshift(mutation.item)
  }
  return next
}

function newMutationId(): string {
  if (typeof window.crypto?.randomUUID === 'function') return window.crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function latestRevision(itemKey: string, localRevision: number | null | undefined): number | null {
  const knownRevision = readKnownState(itemKey)?.revision ?? null
  if (localRevision && knownRevision) return Math.max(localRevision, knownRevision)
  return localRevision ?? knownRevision
}

function queueMutation(
  itemKey: string,
  intent: { kind: 'upsert'; item: DigQueueItem } | { kind: 'delete' },
  baseRevision: number | null,
): PendingMutation | null {
  const predecessor = latestMutation(itemKey)
  if (!predecessor && intent.kind === 'delete' && baseRevision === null) return null
  const mutationId = newMutationId()
  const operationKey = operationStorageKey(itemKey, mutationId)
  const afterResultRevision = predecessor ? predictedResultRevision(predecessor) : null
  const common: MutationBase = {
    schema: 1,
    mutationId,
    itemKey,
    expectedRevision: predecessor ? null : baseRevision,
    createdAt: new Date().toISOString(),
    operationKey,
    ...(predecessor ? { afterMutationId: predecessor.mutationId } : {}),
    ...(afterResultRevision ? { afterResultRevision } : {}),
  }
  const mutation: PendingMutation = intent.kind === 'upsert'
    ? {
        ...common,
        kind: 'upsert',
        item: { ...intent.item, revision: predecessor ? null : baseRevision },
      }
    : { ...common, kind: 'delete' }
  storeOperation(mutation)
  return mutation
}

function migrateLegacySyncState(localItems: DigQueueItem[]): void {
  try {
    const raw = window.localStorage.getItem(LEGACY_SYNC_STORAGE_KEY)
    if (!raw) return
    const legacy = JSON.parse(raw) as {
      pending?: Record<string, { kind?: string; item?: unknown; id?: unknown; version?: unknown }>
    }
    for (const [entryKey, mutation] of Object.entries(legacy.pending ?? {})) {
      const itemKey = isCanonicalItemKey(mutation.id) ? mutation.id : entryKey
      if (!isCanonicalItemKey(itemKey)) {
        droppedMalformedOperation = true
        continue
      }
      const mutationId = `legacy-${String(mutation.version ?? 'unknown')}-${itemKey}`
      const operationKey = operationStorageKey(itemKey, mutationId)
      if (mutation.kind === 'upsert') {
        const item = parseDigQueueItem(mutation.item)
          ?? localItems.find((candidate) => candidate.id === itemKey)
          ?? null
        if (!item || item.id !== itemKey) {
          droppedMalformedOperation = true
          continue
        }
        storeOperation({
          schema: 1,
          mutationId,
          kind: 'upsert',
          itemKey,
          item,
          expectedRevision: item.revision,
          createdAt: item.addedAt,
          operationKey,
        })
      } else if (mutation.kind === 'delete') {
        storeOperation({
          schema: 1,
          mutationId,
          kind: 'delete',
          itemKey,
          expectedRevision: null,
          createdAt: new Date().toISOString(),
          operationKey,
          legacyUnversioned: true,
        })
      }
    }
    window.localStorage.removeItem(LEGACY_SYNC_STORAGE_KEY)
  } catch {
    droppedMalformedOperation = true
    try {
      window.localStorage.removeItem(LEGACY_SYNC_STORAGE_KEY)
    } catch {
      // Ignore unavailable storage.
    }
  }
}

function migrateUnversionedCachedItems(localItems: DigQueueItem[]): void {
  for (const item of localItems) {
    if (item.revision !== null || latestMutation(item.id)) continue
    const mutationId = `unversioned-${item.id}-${item.addedAt}`
    const operationKey = operationStorageKey(item.id, mutationId)
    storeOperation({
      schema: 1,
      mutationId,
      kind: 'upsert',
      itemKey: item.id,
      item,
      expectedRevision: null,
      createdAt: item.addedAt,
      operationKey,
    })
  }
}

const cachedItems = loadFromStorage()
for (const item of cachedItems) {
  if (item.revision) rememberKnownState(item.id, item.revision, false)
}
migrateLegacySyncState(cachedItems)
migrateUnversionedCachedItems(cachedItems)
const items = ref<DigQueueItem[]>(applyPendingMutations(cachedItems))
const digQueueSyncing = ref(false)
const digQueueSyncError = ref('')
let syncPromise: Promise<void> | null = null
let syncRequested = false

watch(
  items,
  (value) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
    } catch {
      // The queue remains available in memory.
    }
  },
  { deep: true },
)

function replaceLocalItem(item: DigQueueItem): void {
  items.value = [item, ...items.value.filter((current) => current.id !== item.id)]
}

function applyRemoteRecord(value: unknown, itemKey: string): boolean {
  if (value === null) {
    clearKnownState(itemKey)
    items.value = items.value.filter((item) => item.id !== itemKey)
    return true
  }
  const parsed = parseRemoteRecord(value)
  if (!parsed || parsed.item.id !== itemKey) return false
  const accepted = rememberKnownState(itemKey, parsed.item.revision as number, parsed.deleted)
  if (!accepted) {
    if (readKnownState(itemKey)?.deleted) {
      items.value = items.value.filter((item) => item.id !== itemKey)
    }
    return true
  }
  if (parsed.deleted) {
    items.value = items.value.filter((item) => item.id !== itemKey)
  } else {
    replaceLocalItem(parsed.item)
  }
  return true
}

function parseSnapshot(values: unknown[]): Map<string, RemoteState> {
  const snapshot = new Map<string, RemoteState>()
  for (const value of values) {
    const parsed = parseRemoteRecord(value)
    if (!parsed) throw new Error('invalid dig queue snapshot')
    const accepted = rememberKnownState(
      parsed.item.id,
      parsed.item.revision as number,
      parsed.deleted,
    )
    if (accepted) {
      snapshot.set(parsed.item.id, parsed)
      continue
    }
    const known = readKnownState(parsed.item.id)
    if (!known) throw new Error('missing newer dig queue state')
    if (known.deleted) {
      snapshot.set(parsed.item.id, {
        item: { ...parsed.item, revision: known.revision },
        deleted: true,
      })
      continue
    }
    const local = items.value.find(
      (item) => item.id === parsed.item.id && item.revision === known.revision,
    )
    if (!local) throw new Error('stale dig queue snapshot')
    snapshot.set(local.id, { item: local, deleted: false })
  }
  return snapshot
}

function conflictCurrent(error: unknown): unknown | undefined {
  if (!axios.isAxiosError(error) || error.response?.status !== 409) return undefined
  const data = error.response.data as { detail?: { current?: unknown } } | undefined
  return data?.detail && Object.prototype.hasOwnProperty.call(data.detail, 'current')
    ? data.detail.current
    : undefined
}

function permanentValidationError(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false
  const status = error.response?.status
  return status === 400 || status === 422
}

function removeOperationsDescendantsFirst(mutations: PendingMutation[]): boolean {
  const byId = new Map(mutations.map((mutation) => [mutation.mutationId, mutation]))
  const ordered = mutations.slice().sort((left, right) => (
    mutationDepth(right, byId) - mutationDepth(left, byId)
    || right.createdAt.localeCompare(left.createdAt)
  ))
  for (const mutation of ordered) {
    if (!removeStoredOperation(mutation.operationKey)) return false
  }
  return true
}

function removeMutationTree(rootMutationId: string): boolean {
  const mutations = loadPendingMutations()
  const ids = new Set([rootMutationId])
  let changed = true
  while (changed) {
    changed = false
    for (const mutation of mutations) {
      if (mutation.afterMutationId && ids.has(mutation.afterMutationId) && !ids.has(mutation.mutationId)) {
        ids.add(mutation.mutationId)
        changed = true
      }
    }
  }
  return removeOperationsDescendantsFirst(
    mutations.filter((mutation) => ids.has(mutation.mutationId)),
  )
}

function resolvedMutation(mutation: PendingMutation, revision: number): PendingMutation {
  const common: MutationBase = {
    schema: 1,
    mutationId: mutation.mutationId,
    itemKey: mutation.itemKey,
    expectedRevision: revision,
    createdAt: mutation.createdAt,
    operationKey: mutation.operationKey,
  }
  return mutation.kind === 'upsert'
    ? { ...common, kind: 'upsert', item: { ...mutation.item, revision } }
    : { ...common, kind: 'delete' }
}

function resolveDirectSuccessors(predecessor: PendingMutation, revision: number): string[] {
  const warnings: string[] = []
  const successors = loadPendingMutations().filter(
    (mutation) => mutation.afterMutationId === predecessor.mutationId,
  )
  for (const successor of successors) {
    if (successor.afterResultRevision && successor.afterResultRevision !== revision) {
      if (!removeMutationTree(successor.mutationId)) {
        throw new Error('could not persist rejected dig queue successor')
      }
      warnings.push('另一设备已更新这条好奇心，后继本地操作未强行套用。')
      continue
    }
    storeOperation(resolvedMutation(successor, revision))
  }
  return warnings
}

function isReadyMutation(mutation: PendingMutation): boolean {
  if (mutation.afterMutationId) return false
  return mutation.kind === 'upsert' || mutation.expectedRevision !== null
}

async function flushPendingMutations(): Promise<string[]> {
  const warnings: string[] = []
  while (true) {
    const mutation = loadPendingMutations().find(isReadyMutation)
    if (!mutation) return warnings
    try {
      let revision: number
      if (mutation.kind === 'upsert') {
        const remote = await saveDigQueueItem({
          topic_id: mutation.item.topicId,
          topic_name: mutation.item.topicName,
          event_id: mutation.item.eventId,
          event_title: mutation.item.eventTitle,
          view: mutation.item.view,
          added_at: mutation.item.addedAt,
          expected_revision: mutation.expectedRevision,
        })
        const parsed = parseRemoteRecord(remote)
        if (!parsed || parsed.deleted || parsed.item.id !== mutation.itemKey) {
          throw new Error('invalid dig queue response')
        }
        applyRemoteRecord(remote, mutation.itemKey)
        revision = parsed.item.revision as number
      } else {
        const remote = await deleteDigQueueItem(mutation.itemKey, mutation.expectedRevision as number)
        if (!remote.deleted || remote.item_key !== mutation.itemKey || !isPositiveInteger(remote.revision)) {
          throw new Error('invalid dig queue delete response')
        }
        rememberKnownState(mutation.itemKey, remote.revision, true)
        items.value = items.value.filter((item) => item.id !== mutation.itemKey)
        revision = remote.revision
      }
      warnings.push(...resolveDirectSuccessors(mutation, revision))
      if (!removeStoredOperation(mutation.operationKey)) {
        throw new Error('could not persist completed dig queue operation')
      }
      items.value = applyPendingMutations(items.value)
    } catch (error) {
      const current = conflictCurrent(error)
      if (current !== undefined && applyRemoteRecord(current, mutation.itemKey)) {
        if (!removeMutationTree(mutation.mutationId)) {
          throw new Error('could not persist rejected dig queue operation')
        }
        warnings.push('另一设备已更新这条好奇心，已采用服务端最新状态。')
        continue
      }
      if (permanentValidationError(error)) {
        if (!removeMutationTree(mutation.mutationId)) {
          throw new Error('could not quarantine invalid dig queue operation')
        }
        warnings.push('一条无效的本地队列操作已隔离，其余操作继续同步。')
        continue
      }
      throw error
    }
  }
}

function reconcileBlockedMutations(snapshot: Map<string, RemoteState>): string[] {
  const warnings: string[] = []
  let mutations = loadPendingMutations()
  const mutationIds = new Set(mutations.map((mutation) => mutation.mutationId))
  for (const mutation of mutations) {
    const remote = snapshot.get(mutation.itemKey) ?? null
    if (mutation.kind === 'delete' && mutation.legacyUnversioned && mutation.expectedRevision === null) {
      if (!remote || remote.deleted) {
        if (!removeStoredOperation(mutation.operationKey)) {
          throw new Error('could not persist legacy dig queue reconciliation')
        }
      } else if (remote.item.revision === 1) {
        storeOperation(resolvedMutation(mutation, 1))
      } else {
        if (!removeMutationTree(mutation.mutationId)) {
          throw new Error('could not persist legacy dig queue rejection')
        }
        warnings.push('旧版删除意图遇到更新后的服务端状态，已保留服务端版本。')
      }
      continue
    }
    if (mutation.afterMutationId && !mutationIds.has(mutation.afterMutationId)) {
      if (remote && mutation.afterResultRevision === remote.item.revision) {
        storeOperation(resolvedMutation(mutation, remote.item.revision as number))
      } else {
        if (!removeMutationTree(mutation.mutationId)) {
          throw new Error('could not persist orphaned dig queue rejection')
        }
        warnings.push('在途操作的服务端版本已变化，未重放旧的后继意图。')
      }
    }
  }

  mutations = loadPendingMutations()
  if (mutations.length && !mutations.some(isReadyMutation)) {
    if (!removeOperationsDescendantsFirst(mutations)) {
      throw new Error('could not quarantine invalid dig queue operation chain')
    }
    warnings.push('检测到无法安全恢复的队列操作链，已隔离并采用服务端状态。')
  }
  return warnings
}

function pendingSignature(): string {
  return loadPendingMutations()
    .map((mutation) => `${mutation.mutationId}:${mutation.expectedRevision}:${mutation.afterMutationId ?? ''}`)
    .join('|')
}

async function runSync(): Promise<void> {
  digQueueSyncing.value = true
  digQueueSyncError.value = ''
  const warnings: string[] = []
  if (droppedMalformedOperation) {
    warnings.push('一条损坏的本地队列操作已隔离，其余操作继续同步。')
    droppedMalformedOperation = false
  }
  try {
    while (true) {
      warnings.push(...await flushPendingMutations())
      const remoteItems = await fetchDigQueue()
      const snapshot = parseSnapshot(remoteItems)
      warnings.push(...reconcileBlockedMutations(snapshot))
      const pending = loadPendingMutations()
      if (pending.some(isReadyMutation)) continue

      const signature = pendingSignature()
      const activeItems = [...snapshot.values()]
        .filter((record) => !record.deleted)
        .map((record) => record.item)
      items.value = applyPendingMutations(activeItems, pending)
      if (pendingSignature() !== signature) continue
      digQueueSyncError.value = [...new Set(warnings)].join(' ')
      return
    }
  } catch {
    const degraded = '跨设备同步暂不可用，本机队列已保留；下次操作或刷新时重试。'
    digQueueSyncError.value = [...new Set([...warnings, degraded])].join(' ')
  } finally {
    const shouldRerun = syncRequested
    syncRequested = false
    digQueueSyncing.value = false
    syncPromise = null
    if (shouldRerun) void syncDigQueue()
  }
}

function syncDigQueue(): Promise<void> {
  if (syncPromise) {
    syncRequested = true
  } else {
    syncPromise = runSync()
  }
  return syncPromise
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (!event.key?.startsWith(OPERATION_PREFIX)) return
    items.value = applyPendingMutations(items.value)
    void syncDigQueue()
  })
}

export function useDigQueue() {
  const digItems = computed(() => items.value)
  const digCount = computed(() => items.value.length)

  function addToDigQueue(
    item: Omit<DigQueueItem, 'addedAt' | 'revision'> & { addedAt?: string },
  ): void {
    const existing = items.value.find((candidate) => candidate.id === item.id)
    const baseRevision = latestRevision(item.id, existing?.revision)
    const queued = parseDigQueueItem({
      ...item,
      topicName: item.topicName.trim(),
      eventTitle: item.eventTitle.trim(),
      addedAt: item.addedAt ?? new Date().toISOString(),
      revision: latestMutation(item.id) ? null : baseRevision,
    })
    if (!queued) return
    replaceLocalItem(queued)
    queueMutation(queued.id, { kind: 'upsert', item: queued }, baseRevision)
    items.value = applyPendingMutations(items.value)
    void syncDigQueue()
  }

  function removeFromDigQueue(id: string): void {
    const existing = items.value.find((item) => item.id === id)
    const baseRevision = latestRevision(id, existing?.revision)
    items.value = items.value.filter((item) => item.id !== id)
    queueMutation(id, { kind: 'delete' }, baseRevision)
    items.value = applyPendingMutations(items.value)
    void syncDigQueue()
  }

  return {
    digItems,
    digCount,
    digQueueSyncing,
    digQueueSyncError,
    addToDigQueue,
    removeFromDigQueue,
    syncDigQueue,
  }
}
