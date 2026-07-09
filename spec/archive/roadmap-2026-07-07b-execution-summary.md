# 路线图执行总结 —— roadmap-claude-gpt-2026-07-07b

状态:**执行记录**。对账对象 `roadmap-claude-gpt-2026-07-07b.md`(Claude 拟、人类拍板的第二版分工路线图)。基线 commit `d61fece`(路线图写作时的 HEAD)。数据线一批已审 ACCEPT 并提交为 `ea233bd`,截止本总结时 `feature = ea233bd`(领先 `origin/master = 42ab615` 一个 commit,未 push/合并——等人类拍板)。**这份路线图已全部走完。**

北极星(全程锚):反回音壁认知拓展(护城河)· 诚实有证据的数据 · 补打开欲 · 不做成瘾 feed。

---

## 一、一句话结论

**路线图表格全部落地——含最后一行"P3 数据线"(已提交 `ea233bd`,默认全关)。** 期间还超额完成两件表外事:把数据线从"阻塞于起 docker"推进到"SearXNG 实测通",以及证实"事件影响网络早已建好"省掉一整块预估工作。**这份路线图正式收官。**

---

## 二、逐条对账(对路线图第三节阶段表)

| 路线图项 | 计划归属 | 状态 | 证据 |
| --- | --- | --- | --- |
| 校准闭环**前端半** + confidence 中性化 | Claude | ✅ 上主干 | `04eb526` |
| 校准闭环**后端半** + 复审 | GPT 做 / Claude 审 | ✅ 上主干 | `d162ab8`,Claude 审 domain 契约/映射/幅度 ACCEPT |
| 阶段0 债务四条 | GPT | ✅ 上主干 | `5db8353`/`41d0bdd`/`265b402`/`42ab615`,Claude 逐笔审 |
| AcademicPanel/SentimentPanel 重排 | Claude(原排下轮) | ✅ 上主干(提前) | `1b3e944` |
| MediaPanel 重排 | Claude(路线图记为已完成) | ✅ 上主干 | `c047749` |
| SearXNG + gnews 解码 + Scrapling | GPT(阻塞于 docker) | ✅ **已提交 `ea233bd`**(默认全关) | 16 文件;阻塞已解、审计 ACCEPT |
| 事件网络打磨 | Claude,可选 | ⏸ 未动(已上线,非新建) | — |
| 认知地图 / tikhub / last30days | 缓 | ⏸ 按计划仍缓 | — |

**路线图第四节两问**均已拍:① confidence 中性化 → 人类**追认**;② 下轮接 Academic/Sentiment 重排 → **已做**。

---

## 三、按北极星三支柱 + 稳定性归类的成果

### 分析层 —— 可读性(前端,Claude)
- `c047749` MediaPanel:~89 处硬编码色收敛进全局 token,暖化 + 主次分层 + 呼吸;保 e2e 类名。
- `1b3e944` AcademicPanel + SentimentPanel:同法迁移(结构中性色→暖 token、品牌 teal→`--brand*`、金色族→`--lens-hype-*`);绿/红语义状态色有意留字面量(无对应淡底 token,强映射会误导状态)。
- 建立设计 token 体系:语义软底色对、透镜专用色、`--brand-wash`。

### 认知层 —— 校准闭环(护城河)
- `d162ab8` 后端(GPT):`CognitionMark` 加 `domain` 列 + 迁移;**种子域→画像域 key 映射表**(修正路线图零节前"只要落 domain 就能回写"的空转假设——两套词表原本只 `finance` 重合);marks→profile 轻推(known+5 / unfamiliar−5 / doubtful 只留 lesson / unexpected 不参与);重复 PUT 去抖;evidence 追 lesson 留痕;**无"高 confidence 少推该域"逻辑**(反回音壁守卫)。
- `04eb526` 前端(Claude):`saveCognitionMark` 传 `domain`;类型对齐;标记后 `fetchCognitionProfile()` 闭环刷新;**confidence 中性化**(去 `confidenceBoost`、保 `interestBoost`)——confidence 回归"透明告知"不再"越懂越推"。方向可逆,留待认知测试验证。

### 分析层 —— 破全文天花板(数据线,GPT)【已提交 `ea233bd`,默认全关】
- gnews URL 解码:离线优先 + batchexecute 网络兜底;**spike 证实 20/20 新格式 CBMi 离线解不出、只网络可解** → 据此默认关 `GNEWS_DECODE_URLS=0`。
- Scrapling 全文变体:懒导入 StealthyFetcher,软降级,复用 `extract_from_html`,不破付费墙;默认关 `FULLTEXT_USE_SCRAPLING=0`。
- SearXNG 采集器:打自托管实例 `/search?format=json`,rss 同款 dict,接 `collect_topic`;默认关 `USE_SEARXNG=0`。
- `Article` 加 `original_url`/`url_decoded` 留痕列;`_decode_stats` 诊断(经 Claude 审出并修正"默认态误报 100% 失败"的撒谎留痕)。
- 审计:八轴七过一修;测试真红绿;后端 272 passed。

### 稳定性 —— 阶段0 债务(GPT)
- `5db8353` 整数边界:非数字入参 422 不再 500;`project_id:null` 正确解绑。
- `41d0bdd` 空白 query:schema 层拒绝。
- `265b402` 改名综述丢失:改按 `topic_id`(唯一)取 job,不再靠易变话题名——修 bug 兼消除同名话题串号隐患。
- `42ab615` daily-email Windows:`cmd /c` 启动 shim,不碰 SMTP,不真发信。

---

## 四、表外超额完成

1. **基础设施:本地 SearXNG 从零搭通**(Claude 引导人类)。装 Docker Desktop(WSL2 后端)→ 写 compose/settings(手动开 JSON API)→ 起容器 → 诊断国内引擎超时 → 配宿主机代理(需代理开 LAN,容器经 `host.docker.internal:10808`)→ 实测搜 "OpenAI" 返回 61 条真实发布方 URL。配置在 gitignore 的 `dev/searxng/`。把 P3 从"阻塞"推进到"可实测"。
2. **认知修正:事件影响网络早已建好**。探查确认它是 live 组件(`MediaPanel.vue:130-201`),已锁"结构视图/无因果箭头",e2e 覆盖。省掉一整块预估的"V1 新建"工作,也化解了之前"用 6 维还是 14 维"的争论(代码已是诚实结构版)。

---

## 五、协作机制沉淀(本轮确立/沿用)

- **驾驶舱汇报规则**(GPT 提、写入 BOARD):人类不读原始日志,长任务收尾先人话汇报(做了啥/绿黄红/待拍板 ABC/风险/下一步)。
- **分工按目录切死**:Claude 主 `frontend/` + 产品/排序判断;GPT 主 `backend/`+`docs/`+`spec/CHANGELOG`。互审、不混提交。
- **硬约束全程守住**:不合 master/不推 origin 由人类拍;每步独立提交 + 门禁;改符号前 GitNexus impact;降级必留痕(且留痕要诚实——`_decode_stats` 即因此打回);不提交 gitnexus 幽灵/`.agent-bridge`/`dev/`/真实库。
- **产品方法论沉淀**:按意图设计(页面数/分割/呈现是下游,起点是用户意图与时刻;用户即目标用户→自我观察最准)。

---

## 六、当前待办与下一步

**路线图已收官**:数据线 16 文件已提交 `ea233bd`(默认全关,不改变默认采集路径)。表格全部落地。feature 分支现领先 origin/master 1 个 commit(`ea233bd`),push/合并 master 待人类拍板。

**提交后的开关决策**(需人类):SearXNG 已就绪、不烧钱不招限流,可先开;`GNEWS_DECODE_URLS` 开启前需先给 batchexecute 加上限/缓存(防请求放大 + Google 限流);Scrapling 需 `pip install scrapling` 才生效。

**下一版路线图头号候选**:稳定性 + 护城河 + 可读性均落地后,"按意图重新审视前端页面结构"成为下一个真问题(见 [[product-design-by-intent]])——产品骨架是否长对。
