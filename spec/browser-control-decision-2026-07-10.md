# 浏览器接管与 OpenCLI 去留决策记录

## 背景

用户希望 Codex 能直接打开、读取和操作浏览器，不再依赖 OpenCLI，并且不能因为重新安装插件而退出当前基于 API key 的 Codex 登录。

本次只完成本机工具配置和决策记录，没有修改项目业务代码、`backend/.env`、日常 Chrome 用户目录或任何网站登录态。

## 已完成的改动

已在 Codex 全局 MCP 配置中启用官方 Playwright MCP：

- MCP 名称：`playwright-browser`
- 包版本：`@playwright/mcp@0.0.78`
- 浏览器：本机 Chrome
- 能力：页面视觉读取、点击、输入、截图和 DevTools
- 独立持久化用户目录：`C:\Users\任锂帅\AppData\Local\Codex\playwright-profile`

配置命令等价于：

```text
C:\Program Files\nodejs\npx.cmd -y @playwright/mcp@0.0.78 \
  --browser=chrome \
  --user-data-dir=C:\Users\任锂帅\AppData\Local\Codex\playwright-profile \
  --caps=vision,devtools \
  --console-level=warning
```

验证结果：

- `codex mcp get playwright-browser` 显示 `enabled: true`。
- `codex mcp list` 能看到 `playwright-browser`。
- MCP 包版本可正常执行。
- 独立持久化 profile 已创建。

当前 Codex 会话启动时尚未加载这项新 MCP，因此需要重启 Codex 客户端或新开会话后才能获得浏览器工具。重启不会删除 API key 配置，也不要求卸载现有 Chrome 插件。

## 为什么使用独立浏览器 profile

- 不占用或锁定日常 Chrome 的 Default profile。
- 不复制 Cookie、密码或本机 Chrome 数据，降低登录态损坏风险。
- 平台需要登录时，用户只需在受控浏览器中手动登录一次；后续会话复用该 profile。
- 不手工修补 Codex Chrome 插件的 Native Messaging Host，避免进入不受支持的安装状态。

## Playwright MCP 与 OpenCLI 不是同一层

| 能力 | Playwright MCP | OpenCLI |
| --- | --- | --- |
| Codex 代用户打开、点击、输入、截图 | 适合 | 不是主要用途 |
| 读取当前网页并辅助人工研究 | 适合 | 能力受适配器限制 |
| 后端定时、批量、结构化采集民间平台 | 当前不直接提供 | 当前项目仍在使用 |
| 在项目后端无人值守运行 | 尚未接入 | 已有 collector 和诊断链 |
| 登录态 | 独立持久化 Chrome profile | 依赖 OpenCLI/Chrome 外部状态 |

因此，浏览器接管已经可以绕开 OpenCLI 完成“Codex 操作浏览器”，但还不能直接替换产品内部的民间情绪采集链。当前代码中：

- Reddit 配置 API key 时优先走 Reddit API；未配置时才回退 OpenCLI。
- Hacker News 不依赖 OpenCLI。
- B 站、小红书、雪球仍通过 OpenCLI adapter 采集。
- `/api/integrations/opencli/diagnostics` 和相关回归测试仍在维护 OpenCLI 的启动与错误边界。

## 当前建议

### 短期：保留但降级为可选兼容通道

暂不删除 OpenCLI，也不立即改动 `OPENCLI_COMMAND`。将它视为民间平台采集的 legacy/optional adapter，而不是浏览器控制基础设施。

理由：直接弃用会让 B 站、小红书和雪球立即失去现有采集路径；Playwright MCP 又不能被 FastAPI 后端直接当作稳定、无人值守的结构化采集器调用。

### 下一步候选改动

在 Claude 独立审查后，再决定是否实施以下最小迁移：

1. 增加明确的社区采集 provider 开关，例如 `COMMUNITY_COLLECTION_PROVIDER=opencli|disabled`，默认策略由人类拍板。
2. 前端把 OpenCLI 标为“可选兼容采集器”，未启用时不再反复显示误导性的全平台故障。
3. 保留平台级错误和降级留痕，Hacker News、Reddit API 等独立通道不受 OpenCLI 失败影响。
4. 为 B 站、小红书、雪球找到可验证的替代 provider 后，再进入正式弃用期。

不建议直接让后端调用 Codex 的 Playwright MCP。MCP 属于 agent 会话工具，不是现有 FastAPI 服务的稳定运行时依赖；强行耦合会让定时任务、部署和测试都依赖一个交互式 agent 会话。

## OpenCLI 正式弃用门槛

只有同时满足以下条件，才删除 OpenCLI 代码与配置：

1. B 站、小红书、雪球至少有一条替代采集路径，并能返回项目需要的结构化字段。
2. 替代路径能区分“未登录、无结果、平台限制、启动失败”，失败不能静默伪装为空数据。
3. 有真实页面/真实响应的薄集成验证，不能只依赖 mock。
4. 登录态、频率限制、合规边界和数据清洗规则有明确说明。
5. 前端、API payload、测试和运行文档已经迁移，不再引用 OpenCLI。

## 重启后的验收

新会话中执行一次无害测试：

1. 让 Codex 打开 `https://example.com` 或百度。
2. 确认 Chrome 可见启动。
3. 确认 Codex 能读取页面、点击、输入和截图。
4. 需要访问登录平台时，仅在独立受控 profile 中手动登录一次。

若新会话仍看不到浏览器工具，先检查：

```powershell
codex mcp get playwright-browser
codex mcp list
```

此时应排查 Codex 对 MCP 的加载/重启行为，不回退到手工修改 Native Messaging Host。
