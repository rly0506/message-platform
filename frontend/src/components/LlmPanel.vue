<script setup lang="ts">
type StepState = { key: string; label: string; status: string }

defineProps<{
  hasLlmAnalysis: boolean
  deepAnalyzing: boolean
  academicAnalyzing: boolean
  sentimentAnalyzing: boolean
  activeDeepJobId: string
  deepMessage: string
  deepSteps: StepState[]
  safeAnalysisHtml: string
  displayAnalysisText: string
  stepStatusText: (status: string) => string
}>()

defineEmits<{
  runDeepAnalysis: []
}>()
</script>

<template>
  <section class="feed-pane tab-pane-wide">
    <section class="wide-panel llm-panel">
      <div class="pane-header compact">
        <div>
          <p class="eyebrow">Deep Analysis</p>
          <h2>{{ hasLlmAnalysis ? 'LLM 批判分析' : '本地规则说明' }}</h2>
        </div>
        <div class="event-actions">
          <span v-if="hasLlmAnalysis" class="llm-badge">LLM 生成</span>
          <button type="button" :disabled="deepAnalyzing || academicAnalyzing || sentimentAnalyzing" @click="$emit('runDeepAnalysis')">
            {{ deepAnalyzing || academicAnalyzing || sentimentAnalyzing ? 'LLM 分析中...' : '深度分析（LLM）' }}
          </button>
        </div>
      </div>

      <p v-if="activeDeepJobId" class="search-message">深度任务：{{ activeDeepJobId.slice(0, 8) }}</p>
      <p v-if="deepMessage" class="search-message">{{ deepMessage }}</p>
      <div v-if="deepSteps.length" class="step-list deep-step-list">
        <span v-for="step in deepSteps" :key="step.key" :class="`step-${step.status}`">
          {{ step.label }} · {{ stepStatusText(step.status) }}
        </span>
      </div>

      <div v-if="safeAnalysisHtml" class="analysis markdown-body llm-analysis-body" v-html="safeAnalysisHtml" />
      <div v-else-if="displayAnalysisText" class="analysis llm-analysis-body">
        <p>{{ displayAnalysisText }}</p>
      </div>
      <p v-else class="muted">{{ hasLlmAnalysis ? 'LLM 分析尚未生成。' : '本地分析尚未生成。' }}</p>
    </section>
  </section>
</template>
