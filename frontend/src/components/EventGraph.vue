<script setup lang="ts">
import { computed, ref } from 'vue'

type EventGraphNode = {
  key: string
  index: number
  title: string
  date: string | null
  summary: string
  evidence: string
}
type EventGraphEdge = {
  key: string
  from: number
  to: number
  label: string
  direction: 'directed' | 'symmetric'
  evidence: string
  items: string[]
}

const props = defineProps<{
  nodes: EventGraphNode[]
  edges: EventGraphEdge[]
  selectedIndex: number
  fmtDate: (value: string | null, withTime?: boolean) => string
}>()

const emit = defineEmits<{ (e: 'select', index: number): void }>()

// —— 布局常量（时间锚定编辑风：极简、无动效） ——
const PAD_X = 52
const TITLE_Y = 22
const DATE_Y = 42
const BASELINE = 80
const MIN_GAP = 132
const NODE_R = 8
const ARC_BASE = 30
const ARC_PER_DIST = 16
const ARC_MAX = 120
const ARC_PAD_BOTTOM = 34

// 对称边按类型分色（复用 style.css 已有透镜 token，克制不抢主色）
const EDGE_STYLE: Record<string, { color: string; dashed: boolean }> = {
  时间顺序: { color: 'var(--brand-accent)', dashed: false },
  同组报道: { color: 'var(--lens-rising-fg)', dashed: true },
  共享对象: { color: 'var(--lens-hype-fg)', dashed: true },
  共同来源: { color: 'var(--lens-herding-fg)', dashed: true },
}
function edgeColor(label: string) {
  return EDGE_STYLE[label]?.color || 'var(--text-faint)'
}
function edgeDashed(label: string) {
  return EDGE_STYLE[label]?.dashed ?? true
}

function parseTs(date: string | null): number | null {
  if (!date) return null
  const t = new Date(date).getTime()
  return Number.isFinite(t) ? t : null
}

function truncate(text: string, max = 8) {
  const value = text || ''
  return value.length > max ? `${value.slice(0, max)}…` : value
}

const hoveredEdgeKey = ref<string | null>(null)

const layout = computed(() => {
  const nodes = props.nodes
  const n = nodes.length
  if (!n) return { width: 600, height: 200, nodes: [], edges: [] }

  // —— X 定位：按真实日期比例落在时间轴上；日期缺失/不足则均匀退化 ——
  const times = nodes.map((node) => parseTs(node.date))
  const known = times.filter((t): t is number => t !== null)
  const tMin = known.length ? Math.min(...known) : 0
  const tMax = known.length ? Math.max(...known) : 0
  const span = tMax - tMin
  const innerW = Math.max(MIN_GAP * Math.max(1, n - 1), 480)

  const xs: number[] = nodes.map((_, i) => {
    const t = times[i]
    if (span > 0 && t !== null) return PAD_X + ((t - tMin) / span) * innerW
    // 无有效跨度：均匀分布
    return PAD_X + (n === 1 ? innerW / 2 : (i / (n - 1)) * innerW)
  })
  // 左到右保最小间距（节点已按日期排序，index 即时间序）
  for (let i = 1; i < n; i += 1) {
    if (xs[i] < xs[i - 1] + MIN_GAP) xs[i] = xs[i - 1] + MIN_GAP
  }

  const laidNodes = nodes.map((node, i) => ({
    ...node,
    x: xs[i],
    y: BASELINE,
    titleShort: truncate(node.title),
  }))

  // —— 边：时间序=基线实线（带箭头）；对称边=基线下方虚线弧 ——
  const seenSpan = new Map<string, number>() // 同一对节点多条对称边错开深度
  let maxDepth = 0
  const laidEdges = props.edges
    .map((edge) => {
      const a = laidNodes[edge.from]
      const b = laidNodes[edge.to]
      if (!a || !b) return null
      const color = edgeColor(edge.label)
      const dashed = edgeDashed(edge.label)
      if (edge.direction === 'directed') {
        return {
          ...edge,
          kind: 'line' as const,
          x1: a.x,
          y1: BASELINE,
          x2: b.x,
          y2: BASELINE,
          color,
          dashed,
          labelX: (a.x + b.x) / 2,
          labelY: BASELINE - 8,
        }
      }
      const dist = Math.abs(edge.to - edge.from)
      const spanKey = `${Math.min(edge.from, edge.to)}-${Math.max(edge.from, edge.to)}`
      const stack = seenSpan.get(spanKey) || 0
      seenSpan.set(spanKey, stack + 1)
      const depth = Math.min(ARC_MAX, ARC_BASE + dist * ARC_PER_DIST + stack * 14)
      maxDepth = Math.max(maxDepth, depth)
      const midX = (a.x + b.x) / 2
      const cy = BASELINE + depth
      return {
        ...edge,
        kind: 'arc' as const,
        path: `M ${a.x} ${BASELINE} Q ${midX} ${cy} ${b.x} ${BASELINE}`,
        color,
        dashed,
        labelX: midX,
        labelY: cy - 4,
      }
    })
    .filter((edge): edge is NonNullable<typeof edge> => edge !== null)

  const width = xs[n - 1] + PAD_X
  const height = BASELINE + Math.max(maxDepth, 10) + ARC_PAD_BOTTOM
  return { width, height, nodes: laidNodes, edges: laidEdges }
})

const legend = computed(() => {
  const present = new Set(props.edges.map((edge) => edge.label))
  return Object.keys(EDGE_STYLE)
    .filter((label) => present.has(label))
    .map((label) => ({ label, color: EDGE_STYLE[label].color, dashed: EDGE_STYLE[label].dashed }))
})

function connector(direction: 'directed' | 'symmetric') {
  return direction === 'directed' ? '→' : '↔'
}
</script>

<template>
  <div class="event-graph">
    <p class="event-structure-note">本地证据边，不显示 LLM 因果假设。沿横轴 = 时间；实线 = 时间序，虚线 = 共享实体/来源/报道。</p>

    <div class="event-graph-canvas">
      <svg
        :viewBox="`0 0 ${layout.width} ${layout.height}`"
        :width="layout.width"
        :height="layout.height"
        class="event-graph-svg"
        role="img"
        aria-label="事件时间锚定关系图"
        preserveAspectRatio="xMinYMin meet"
      >
        <defs>
          <marker
            id="event-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--brand-accent)" />
          </marker>
        </defs>

        <!-- 时间轴基线 -->
        <line
          v-if="layout.nodes.length > 1"
          :x1="layout.nodes[0].x"
          :y1="BASELINE"
          :x2="layout.nodes[layout.nodes.length - 1].x"
          :y2="BASELINE"
          class="event-graph-axis"
        />

        <!-- 边 -->
        <g class="event-graph-edges">
          <template v-for="edge in layout.edges" :key="edge.key">
            <line
              v-if="edge.kind === 'line'"
              class="event-graph-edge event-graph-edge-line"
              :class="{ hovered: edge.key === hoveredEdgeKey }"
              :x1="edge.x1"
              :y1="edge.y1"
              :x2="edge.x2"
              :y2="edge.y2"
              :stroke="edge.color"
              :stroke-dasharray="edge.dashed ? '5 4' : undefined"
              marker-end="url(#event-arrow)"
              @mouseenter="hoveredEdgeKey = edge.key"
              @mouseleave="hoveredEdgeKey = null"
            >
              <title>{{ edge.label }}：{{ edge.evidence }}</title>
            </line>
            <path
              v-else
              class="event-graph-edge event-graph-edge-arc"
              :class="{ hovered: edge.key === hoveredEdgeKey }"
              :d="edge.path"
              fill="none"
              :stroke="edge.color"
              :stroke-dasharray="edge.dashed ? '5 4' : undefined"
              @mouseenter="hoveredEdgeKey = edge.key"
              @mouseleave="hoveredEdgeKey = null"
            >
              <title>{{ edge.label }}：{{ edge.evidence }}</title>
            </path>
          </template>
        </g>

        <!-- 节点 -->
        <g class="event-graph-nodes">
          <g
            v-for="node in layout.nodes"
            :key="node.key"
            class="event-graph-node"
            :class="{ active: node.index === selectedIndex }"
            :transform="`translate(${node.x} 0)`"
            role="button"
            tabindex="0"
            :aria-label="`事件 ${node.index + 1}：${node.title}`"
            @click="emit('select', node.index)"
            @keydown.enter.prevent="emit('select', node.index)"
            @keydown.space.prevent="emit('select', node.index)"
          >
            <title>{{ node.title }} · {{ node.evidence }}</title>
            <text class="event-graph-node-title" :y="TITLE_Y" text-anchor="middle">{{ node.titleShort }}</text>
            <text class="event-graph-node-date" :y="DATE_Y" text-anchor="middle">{{ fmtDate(node.date) }}</text>
            <circle class="event-graph-dot" :cy="BASELINE" :r="NODE_R" />
            <text class="event-graph-node-index" :y="BASELINE + 4" text-anchor="middle">{{ node.index + 1 }}</text>
          </g>
        </g>
      </svg>
    </div>

    <!-- 图例 -->
    <ul v-if="legend.length" class="event-graph-legend">
      <li v-for="item in legend" :key="item.label">
        <span class="legend-swatch" :class="{ dashed: item.dashed }" :style="{ '--swatch': item.color }" />
        {{ item.label }}
      </li>
    </ul>

    <!-- 证据边列表：始终可见（审计红线：证据可核查，不藏在悬停后）。与图双向联动高亮。 -->
    <ul v-if="edges.length" class="event-graph-evidence-list">
      <li
        v-for="edge in edges"
        :key="edge.key"
        class="event-graph-evidence-row"
        :class="{ hovered: edge.key === hoveredEdgeKey }"
        @mouseenter="hoveredEdgeKey = edge.key"
        @mouseleave="hoveredEdgeKey = null"
      >
        <span class="evidence-edge-swatch" :class="{ dashed: edgeDashed(edge.label) }" :style="{ '--swatch': edgeColor(edge.label) }" />
        <strong>{{ edge.label }}</strong>
        <span class="evidence-span">#{{ edge.from + 1 }} {{ connector(edge.direction) }} #{{ edge.to + 1 }}</span>
        <span class="evidence-text">{{ edge.evidence }}</span>
        <span v-if="edge.items.length" class="evidence-items">
          <span v-for="item in edge.items" :key="item" class="evidence-item">{{ item }}</span>
        </span>
      </li>
    </ul>

    <p v-if="!layout.edges.length" class="source-matrix-empty">暂无可连接的事件边。</p>
  </div>
</template>

<style scoped>
.event-graph {
  display: grid;
  gap: var(--space-3);
}

.event-structure-note {
  margin: 0;
  color: var(--text-faint);
  font-size: var(--font-size-0);
  line-height: 1.5;
}

.event-graph-canvas {
  overflow-x: auto;
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: var(--surface);
  padding: var(--space-2);
}

.event-graph-svg {
  display: block;
  max-width: none;
}

.event-graph-axis {
  stroke: var(--border-strong);
  stroke-width: 1;
}

.event-graph-edge {
  stroke-width: 1.6;
  cursor: pointer;
  transition: stroke-width 0.1s ease;
}

.event-graph-edge.hovered {
  stroke-width: 3;
}

.event-graph-node {
  cursor: pointer;
}

.event-graph-node:focus {
  outline: none;
}

.event-graph-dot {
  fill: var(--surface);
  stroke: var(--brand-mid);
  stroke-width: 2;
  transition: r 0.1s ease;
}

.event-graph-node:hover .event-graph-dot,
.event-graph-node:focus .event-graph-dot {
  stroke: var(--brand-accent);
}

.event-graph-node.active .event-graph-dot {
  fill: var(--brand-accent);
  stroke: var(--brand-deep);
  r: 10;
}

.event-graph-node-index {
  fill: var(--text-muted);
  font-size: 10px;
  font-weight: 800;
  pointer-events: none;
}

.event-graph-node.active .event-graph-node-index {
  fill: var(--surface);
}

.event-graph-node-title {
  fill: var(--text-heading);
  font-size: var(--font-size-1);
  font-weight: 700;
  pointer-events: none;
}

.event-graph-node-date {
  fill: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 800;
  pointer-events: none;
}

.event-graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}

.event-graph-legend li {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--text-muted);
  font-size: var(--font-size-0);
  font-weight: 700;
}

.legend-swatch {
  display: inline-block;
  width: 22px;
  height: 0;
  border-top: 2px solid var(--swatch);
}

.legend-swatch.dashed {
  border-top-style: dashed;
}

.event-graph-evidence-list {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.event-graph-evidence-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
  border: 1px solid var(--border-soft);
  border-radius: 8px;
  background: var(--surface-tint);
  padding: var(--space-2) var(--space-3);
  font-size: var(--font-size-1);
  cursor: default;
}

.event-graph-evidence-row.hovered {
  border-color: var(--brand-accent);
  background: var(--brand-wash);
}

.evidence-edge-swatch {
  display: inline-block;
  width: 18px;
  height: 0;
  border-top: 2px solid var(--swatch);
}

.evidence-edge-swatch.dashed {
  border-top-style: dashed;
}

.event-graph-evidence-row strong {
  color: var(--text-heading);
}

.evidence-span {
  color: var(--text-faint);
  font-size: var(--font-size-0);
  font-weight: 800;
}

.evidence-text {
  color: var(--text-muted);
}

.evidence-items {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
}

.evidence-item {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 2px 8px;
  background: var(--surface);
  color: var(--text-muted);
  font-size: var(--font-size-0);
  font-weight: 700;
}
</style>
