# 事件发现系统 (Discovery)

与"搜索"互补的另一半。搜索要你先叫得出名字；发现主动从"注意力前沿"
（HN / arXiv / 智库 / 央行）捞认知之外的苗头。

## 核心理念

- **借别人的注意力过滤器**：不扫世界，订阅各领域聪明人已筛过一遍的源。
- **看"加速"不看"最大"**：从低基数在长（5→50）比稳在 5000 有信息量。
  稳在高位 = 已出圈 = 看到就迟了。
- **必须有记忆**：每天存快照到 `discovery.db`，比 delta 才能算加速。
  这是发现区别于无状态搜索的本质 —— 首日只能建基线，次日起才有加速信号。
- **不依赖 LLM**：核心链路纯启发式分类。LLM 二级分拣是可选增强（`--annotate`），
  无 key 自动降级。

## 手动运行

```powershell
# 基础：拉前沿 -> 存快照 -> 出报告（打印 + 落盘）
venv\Scripts\python.exe backend\cli.py discover

# 带 LLM 二级分拣（给种子标"这是什么/为何重要"，无 LLM 自动降级）
venv\Scripts\python.exe backend\cli.py discover --annotate

# 静默跑（只落盘不打印，给定时任务用）
venv\Scripts\python.exe backend\cli.py discover --no-print
```

报告落盘在 `backend\discovery_reports\frontier-<时间戳>.md`。

## 每日定时（Windows 任务计划程序）

发现系统要"攒基线"才有价值 —— 连续每天跑，加速信号才会浮现。
如果只需要落盘报告，可以继续调用 `run_discovery.bat`；如果要每天把日报发到手机邮箱，优先使用 `scripts\send_daily_digest.ps1`，它会先跑 discovery，再通过 SMTP 发送最新日报。

```powershell
# 注册：每天 08:30 生成并发送日报邮件（按需改时间/路径）
schtasks /Create /SC DAILY /TN "事件发现日报邮件" /TR 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "d:\意向项目\scripts\send_daily_digest.ps1"' /ST 08:30

# 查看
schtasks /Query /TN "事件发现日报邮件"

# 立即手动触发一次（测试）
schtasks /Run /TN "事件发现日报邮件"

# 删除
schtasks /Delete /TN "事件发现日报邮件" /F
```

无人值守发送需要 SMTP 环境变量，详见 `docs\operations.md` 的 Daily Digest Email 一节。Agent Mail 发送仍是两阶段确认，不适合任务计划自动发送。

跑几天后，打开最新的 `discovery_reports\frontier-*.md`，重点看 **A. 种子** 一档 ——
那是"在加速 / 全新冒头、还没出圈"的东西，按领域（科技/金融/地缘）分组。

## 配置前沿源

编辑 `backend\config\frontier_sources.json` 增删源。每个源：

- `type`: `hackernews` | `arxiv` | `rss`
- `domain`: 领域桶（`tech` / `finance` / `geopolitics` / ...），报告按此分组
- `enabled`: `false` 则暂不拉取
- arXiv 用 `categories` + `per_cat`；rss 用 `url`

想突破技术圈，就加该领域的策展源（智库 RSS、央行公告、专业 newsletter）。
诚实约束：中文社会/思潮类源大多没有干净 RSS/API，覆盖会偏英文技术圈。

## 已知边界

- **首日只建基线**，加速信号要攒几天才显现（设计如此，非缺陷）。
- **源决定视野**：HN/arXiv 偏技术圈；政治时事的对口引擎是 GDELT
  （报道量异常突增 = 政治版加速检测），但 GDELT 当前 IP 被封。
- **判断归你**：工具只把候选端到面前，"哪颗种子会长大"是你的判断。
