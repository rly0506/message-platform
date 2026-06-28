<script setup lang="ts">
import type { SentimentLayer, SentimentPost, TopicSummary } from '../types/dossier'

type StepState = { key: string; label: string; status: string }
type SentimentPlatformGroup = { platform: string; label: string; posts: SentimentPost[] }

defineProps<{
  sentimentAnalyzing: boolean
  hasSentimentLayer: boolean
  activeSentimentJobId: string
  sentimentMessage: string
  sentimentSteps: StepState[]
  sentimentLoading: boolean
  sentimentError: string
  sentimentPostItems: SentimentPost[]
  sentimentCommentItems: SentimentPost[]
  sentimentPlatformLabels: string
  sentimentLayer: SentimentLayer | null
  selectedTopic: TopicSummary
  sentimentPosts: SentimentPost[]
  safeSentimentSummaryHtml: string
  sentimentPlatformGroups: SentimentPlatformGroup[]
  stepStatusText: (status: string) => string
  sentimentPlatformLabel: (platform: string) => string
  sentimentCommunityLabel: (post: SentimentPost) => string
  sentimentPostDate: (post: SentimentPost) => string
  sentimentSnippet: (post: SentimentPost) => string
  sentimentCommentsForPost: (post: SentimentPost) => SentimentPost[]
}>()

defineEmits<{
  runSentimentAnalysis: []
}>()
</script>

<template>
  <section class="feed-pane tab-pane-wide">
    <section class="wide-panel sentiment-panel">
      <div class="pane-header compact">
        <div>
          <p class="eyebrow">Public Sentiment</p>
          <h2>民间情绪</h2>
        </div>
        <button type="button" class="ghost-button" :disabled="sentimentAnalyzing" @click="$emit('runSentimentAnalysis')">
          {{ sentimentAnalyzing ? '分析中...' : hasSentimentLayer ? '刷新民间情绪' : '生成民间情绪' }}
        </button>
      </div>

      <div class="sentiment-warning">
        <strong>民间情绪 · 最该被怀疑的一角</strong>
        <span>Reddit / Hacker News 样本以情绪、站队和看热闹为主；高赞≠事实，只能作为待核实线索。</span>
        <span class="sentiment-prereq">⚠️ 中文平台(B站/小红书/雪球)经本机浏览器采集：点击前请确认 Chrome 已打开并登录这些平台。Hacker News 与已配 API 的 Reddit 不需要浏览器。</span>
      </div>

      <p v-if="activeSentimentJobId" class="search-message">民间情绪任务：{{ activeSentimentJobId.slice(0, 8) }}</p>
      <p v-if="sentimentMessage" class="search-message">{{ sentimentMessage }}</p>
      <div v-if="sentimentSteps.length" class="step-list deep-step-list">
        <span v-for="step in sentimentSteps" :key="step.key" :class="`step-${step.status}`">
          {{ step.label }} · {{ stepStatusText(step.status) }}
        </span>
      </div>

      <p v-if="sentimentLoading" class="muted">正在读取民间情绪层...</p>
      <p v-else-if="sentimentError" class="country-compare-error">{{ sentimentError }}</p>

      <template v-else>
          <div class="academic-metrics sentiment-metrics">
          <div>
            <strong>{{ sentimentPostItems.length }}</strong>
            <span>平台帖子</span>
          </div>
          <div>
            <strong>{{ sentimentCommentItems.length }}</strong>
            <span>高赞评论</span>
          </div>
          <div>
            <strong>{{ sentimentPlatformLabels || '待生成' }}</strong>
            <span>覆盖平台</span>
          </div>
          <div>
            <strong>{{ sentimentLayer?.queries?.reddit || sentimentLayer?.query || '待生成' }}</strong>
            <span>Reddit 英文查询</span>
          </div>
          <div>
            <strong>{{ sentimentLayer?.queries?.chinese || selectedTopic.name }}</strong>
            <span>中文平台查询</span>
          </div>
        </div>

        <div v-if="sentimentLayer?.errors?.length" class="sentiment-platform-errors">
          <p v-for="item in sentimentLayer.errors" :key="`${item.platform}-${item.error}`">
            {{ sentimentPlatformLabel(item.platform) }} 暂不可用：{{ item.error }}
          </p>
        </div>

        <p v-if="!sentimentPosts.length" class="muted">
          暂无民间平台样本。点击“生成民间情绪”会调用本地 OpenCLI；如果 Chrome、扩展或平台登录不可用，错误会显示在这里。
        </p>

        <div v-if="safeSentimentSummaryHtml" class="analysis markdown-body academic-summary sentiment-summary" v-html="safeSentimentSummaryHtml" />
        <p v-else class="muted">暂无民间情绪摘要。</p>

        <div v-if="sentimentPosts.length" class="academic-section">
          <div class="evidence-header">
            <strong>多平台讨论样本</strong>
            <span>{{ sentimentPostItems.length }} 条帖子 · {{ sentimentCommentItems.length }} 条评论</span>
          </div>
          <div class="sentiment-platform-groups">
            <section v-for="group in sentimentPlatformGroups" :key="group.platform" class="sentiment-platform-group">
              <div class="country-card-head">
                <strong>{{ group.label }}</strong>
                <span>{{ group.posts.length }} 条</span>
              </div>
              <div class="sentiment-post-list">
                <article v-for="post in group.posts" :key="`${post.platform}-${post.url}-${post.title}`" class="sentiment-post">
                  <div>
                    <span>{{ sentimentCommunityLabel(post) }}</span>
                    <b>{{ post.score }} 赞</b>
                    <b>{{ post.num_comments }} 评论</b>
                    <time>{{ sentimentPostDate(post) }}</time>
                  </div>
                  <h3>
                    <a :href="post.url" target="_blank" rel="noreferrer">{{ post.title || '未命名讨论' }}</a>
                  </h3>
                  <p>{{ sentimentSnippet(post) }}</p>
                  <small>作者：{{ post.author || 'unknown' }} · {{ group.label }} 情绪样本，非事实来源</small>
                  <details v-if="sentimentCommentsForPost(post).length" class="sentiment-comments">
                    <summary>{{ sentimentCommentsForPost(post).length }} 条高赞评论</summary>
                    <article
                      v-for="comment in sentimentCommentsForPost(post)"
                      :key="`${comment.platform}-${comment.id}-${comment.title}`"
                      class="sentiment-comment"
                    >
                      <div>
                        <span>评论</span>
                        <b>{{ comment.score }} 赞</b>
                        <time>{{ sentimentPostDate(comment) }}</time>
                      </div>
                      <p>{{ sentimentSnippet(comment) }}</p>
                      <small>作者：{{ comment.author || 'unknown' }} · 评论样本，非事实来源</small>
                    </article>
                  </details>
                </article>
              </div>
            </section>
          </div>
        </div>
      </template>
    </section>
  </section>
</template>
