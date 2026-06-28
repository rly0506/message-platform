<script setup lang="ts">
type StepState = { key: string; label: string; status: string }
type CrossChainItem = { key: string; label: string; status: string; error: string }

defineProps<{
  crossSynthesisAnalyzing: boolean
  hasCrossSynthesis: boolean
  activeCrossSynthesisJobId: string
  crossSynthesisMessage: string
  crossSynthesisSteps: StepState[]
  crossChainItems: CrossChainItem[]
  crossSynthesisLoading: boolean
  crossSynthesisError: string
  crossVoicesUsed: string[]
  safeCrossSynthesisHtml: string
  stepStatusText: (status: string) => string
  voiceLabel: (voice: string) => string
}>()

defineEmits<{
  runCrossSynthesis: []
}>()
</script>

<template>
  <section class="feed-pane tab-pane-wide">
    <section class="wide-panel cross-synthesis-panel">
      <div class="pane-header compact">
        <div>
          <p class="eyebrow">Cross Synthesis</p>
          <h2>三方对照</h2>
        </div>
        <button type="button" class="cross-primary-button" :disabled="crossSynthesisAnalyzing" @click="$emit('runCrossSynthesis')">
          {{ crossSynthesisAnalyzing ? '生成中...' : hasCrossSynthesis ? '刷新三方对照' : '生成三方对照' }}
        </button>
      </div>

      <div class="cross-synthesis-note">
        <strong>媒体 / 学界 / 民间的交叉校验</strong>
        <span>点击后会依次尝试更新媒体、学界、民间声部；单个声部失败不会阻断最终综合。</span>
        <span>综合共识、矛盾、盲区、机制链条和批判提示；民间情绪始终按非事实源处理。</span>
      </div>

      <p v-if="activeCrossSynthesisJobId" class="search-message">三方对照任务：{{ activeCrossSynthesisJobId.slice(0, 8) }}</p>
      <p v-if="crossSynthesisMessage" class="search-message">{{ crossSynthesisMessage }}</p>
      <div v-if="crossSynthesisSteps.length" class="step-list deep-step-list">
        <span v-for="step in crossSynthesisSteps" :key="step.key" :class="`step-${step.status}`">
          {{ step.label }} · {{ stepStatusText(step.status) }}
        </span>
      </div>

      <div v-if="hasCrossSynthesis || crossSynthesisSteps.length" class="cross-chain-status">
        <article v-for="item in crossChainItems" :key="item.key" :class="`chain-${item.status}`">
          <strong>{{ item.label }}</strong>
          <span>{{ stepStatusText(item.status) }}</span>
          <p v-if="item.error">{{ item.error }}</p>
        </article>
      </div>

      <p v-if="crossSynthesisLoading" class="muted">正在读取三方对照...</p>
      <p v-else-if="crossSynthesisError" class="country-compare-error">{{ crossSynthesisError }}</p>

      <template v-else>
        <div class="voice-badges">
          <span v-if="!crossVoicesUsed.length">暂无可用声部</span>
          <span v-for="voice in crossVoicesUsed" :key="voice">{{ voiceLabel(voice) }}</span>
        </div>

        <div v-if="safeCrossSynthesisHtml" class="analysis markdown-body cross-synthesis-summary" v-html="safeCrossSynthesisHtml" />
        <p v-else class="muted">请先运行媒体/学界/民间分析，再生成三方对照。</p>
      </template>
    </section>
  </section>
</template>
