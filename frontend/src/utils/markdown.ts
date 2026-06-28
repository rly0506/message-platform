import DOMPurify from 'dompurify'
import { marked } from 'marked'

/**
 * 把 markdown 渲染成已净化的安全 HTML。
 * 全站统一入口 —— 媒体分析、各 job 结果、发现日报都走这里，避免多份重复实现漂移。
 */
export function renderMarkdown(text: string | undefined | null): string {
  if (!text) return ''
  const html = marked.parse(text, { async: false, breaks: true, gfm: true }) as string
  return DOMPurify.sanitize(html)
}
