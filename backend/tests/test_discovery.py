"""发现层测试 —— 用 fixture 证明加速逻辑, 不靠网络、不靠等一天。

核心验证 (发现区别于搜索的本质):
- 首次运行无历史 -> 只建基线, 报告标注"明天起才有加速"。
- 第二次运行 -> 同一 item 的 signal 上涨能被算成 delta, 全新 item 被标 is_new。
- 分类: 低基数在涨 -> seed; 信号已很大 -> mainstream; 低信号没涨 -> noise。
"""
import os
import tempfile

import pytest

from app.discovery.sources import DiscoveryItem, _arxiv_id
from app.discovery.store import DiscoveryStore
from app.discovery import report


@pytest.fixture()
def store():
    path = os.path.join(tempfile.gettempdir(), "discovery_test.db")
    if os.path.exists(path):
        os.remove(path)
    s = DiscoveryStore(db_path=path)
    yield s
    s.close()
    try:
        os.remove(path)
    except OSError:
        pass


def _hn(ext_id, title, points, comments=0):
    return DiscoveryItem(source="hackernews", external_id=ext_id, title=title,
                         url=f"https://news.ycombinator.com/item?id={ext_id}",
                         signal=points, engagement=comments)


def test_first_run_is_baseline_only(store):
    """首次运行: 无历史, run_count=0 -> 报告只建基线。"""
    assert store.run_count() == 0
    items = [_hn("1", "Seed thing", 40), _hn("2", "Big thing", 800)]
    scored = store.score(items, run_id="day1", now_iso="day1")
    # 首次: 全部 is_new, prev_signal=None
    assert all(s.is_new for s in scored)
    assert all(s.prev_signal is None for s in scored)
    md = report.build_report(scored, run_id="day1", has_history=False)
    assert "仅建立基线" in md
    assert "明天起" in md


def test_acceleration_detected_on_second_run(store):
    """第二次运行: 同一 item 信号上涨 -> delta 被正确算出 (加速)。"""
    day1 = [_hn("1", "Rising seed", 30), _hn("2", "Flat thing", 50)]
    store.score(day1, run_id="day1", now_iso="day1")
    store.commit_run(day1, run_id="day1", now_iso="day1")
    assert store.run_count() == 1

    # 第二天: item 1 从 30 涨到 90 (加速 +60); item 2 几乎没动; item 3 全新出现
    day2 = [_hn("1", "Rising seed", 90), _hn("2", "Flat thing", 52), _hn("3", "Brand new", 45)]
    scored = store.score(day2, run_id="day2", now_iso="day2")
    by_id = {s.item.external_id: s for s in scored}

    assert by_id["1"].is_new is False
    assert by_id["1"].prev_signal == 30
    assert by_id["1"].delta == 60          # 加速量被抓住
    assert by_id["2"].delta == 2           # 几乎没动
    assert by_id["3"].is_new is True       # 全新苗头
    assert by_id["3"].delta == 45          # 新项 delta = 当前信号


def test_categorize_three_buckets(store):
    """有历史时分三档: 加速->seed, 已大->mainstream, 没涨->noise。"""
    day1 = [_hn("1", "Rising", 30), _hn("2", "Flat", 50)]
    store.score(day1, run_id="day1", now_iso="day1")
    store.commit_run(day1, run_id="day1", now_iso="day1")

    day2 = [
        _hn("1", "Rising", 90),    # +60 -> 在加速 -> seed
        _hn("2", "Flat", 52),      # +2 -> 没涨 -> noise
        _hn("3", "New seed", 45),  # 全新且带初速度 -> seed
        _hn("4", "Already big", 900),  # 信号已很大 -> mainstream
        _hn("5", "New tiny", 5),   # 全新但太小 -> noise
    ]
    scored = store.score(day2, run_id="day2", now_iso="day2")
    cats = {s.item.external_id: report.categorize(s, has_history=True) for s in scored}

    assert cats["1"] == "seed"
    assert cats["2"] == "noise"
    assert cats["3"] == "seed"
    assert cats["4"] == "mainstream"
    assert cats["5"] == "noise"


def test_arxiv_new_is_seed_seen_is_noise(store):
    """arXiv 无投票信号: 全新一篇=种子; 已见过=noise (论文不会随时间'加速')。"""
    paper = DiscoveryItem(source="arxiv", external_id="2406.01234", title="A paper",
                          url="http://arxiv.org/abs/2406.01234", category="cs.AI")
    scored1 = store.score([paper], run_id="day1", now_iso="day1")
    assert report.categorize(scored1[0], has_history=True) == "seed"  # 全新
    store.commit_run([paper], run_id="day1", now_iso="day1")

    scored2 = store.score([paper], run_id="day2", now_iso="day2")
    assert scored2[0].is_new is False
    assert report.categorize(scored2[0], has_history=True) == "noise"  # 已见过


def test_mass_tier_fresh_is_mainstream_not_seed(store):
    """源分级修复: 大众媒体 (mass) 的当日新闻 = 已出圈, 不进种子档。

    回归 bug: MIT Tech Review 这类 RSS 源 signal=0, 旧逻辑只凭'新鲜'就判种子,
    导致 A 档塞满'已出圈'的大众媒体新闻 (报告自相矛盾)。现在 mass 源新鲜->mainstream。
    对照: 同样 signal=0、同样全新, 但 niche 源 (默认) 仍是种子。
    """
    mass = DiscoveryItem(source="MIT Technology Review", external_id="https://tr/x",
                         title="The Download: today's news", url="https://tr/x", tier="mass")
    niche = DiscoveryItem(source="Carnegie", external_id="https://c/y",
                          title="A niche think-tank piece", url="https://c/y", tier="niche")
    scored = store.score([mass, niche], run_id="day1", now_iso="day1")
    by_id = {s.item.external_id: s for s in scored}
    # 两者都全新、signal=0; tier 是唯一区别
    assert report.categorize(by_id["https://tr/x"], has_history=True) == "mainstream"
    assert report.categorize(by_id["https://c/y"], has_history=True) == "seed"


def test_mass_tier_stale_is_noise(store):
    """大众媒体的旧条目 (过新鲜窗口) -> noise, 不残留在任何档。"""
    mass = DiscoveryItem(source="MIT Technology Review", external_id="https://tr/old",
                         title="Old news", url="https://tr/old", tier="mass")
    store.score([mass], run_id="2026-06-25T09:00:00Z", now_iso="2026-06-25T09:00:00Z")
    store.commit_run([mass], run_id="2026-06-25T09:00:00Z", now_iso="2026-06-25T09:00:00Z")
    # 3 天后: age=72h > 36h 窗口
    scored = store.score([mass], run_id="2026-06-28T09:00:00Z", now_iso="2026-06-28T09:00:00Z")
    assert report.categorize(scored[0], has_history=True) == "noise"


def test_mass_tier_real_acceleration_still_seed(store):
    """破例: 大众媒体若真加速 (delta 超阈值), 仍算种子 —— 但需有投票信号才可能发生。

    构造一个带 signal 的 mass 源 (假想场景), 验证加速通道没被源分级误堵死。
    """
    mass = DiscoveryItem(source="SomeMassOutlet", external_id="m1", title="Surging story",
                         url="https://m/1", signal=30, tier="mass")
    store.score([mass], run_id="day1", now_iso="day1")
    store.commit_run([mass], run_id="day1", now_iso="day1")
    mass_up = DiscoveryItem(source="SomeMassOutlet", external_id="m1", title="Surging story",
                            url="https://m/1", signal=90, tier="mass")  # +60 > RISE_DELTA_MIN
    scored = store.score([mass_up], run_id="day2", now_iso="day2")
    assert scored[0].delta == 60
    assert report.categorize(scored[0], has_history=True) == "seed"


def test_collect_seeds_structured(store):
    """collect_seeds: 有历史时返回结构化种子 (供前端点击闭环); 无历史返回 []。"""
    day1 = [_hn("1", "Rising seed", 30), _hn("2", "Flat", 50)]
    store.score(day1, run_id="day1", now_iso="day1")
    store.commit_run(day1, run_id="day1", now_iso="day1")
    day2 = [_hn("1", "Rising seed", 95), _hn("2", "Flat", 51)]  # 1 加速->seed, 2 没动->noise
    scored = store.score(day2, run_id="day2", now_iso="day2")

    seeds = report.collect_seeds(scored, has_history=True)
    assert len(seeds) == 1
    seed = seeds[0]
    assert seed["title"] == "Rising seed"
    assert seed["delta"] == 65
    # 必备字段齐全 (前端依赖)
    for key in ("title", "url", "domain", "domain_label", "signal", "delta", "is_new",
                "what", "why", "still_niche"):
        assert key in seed
    # 无历史 = 只建基线 = 无种子
    assert report.collect_seeds(scored, has_history=False) == []


def test_collect_seeds_carries_annotation(store):
    """有 LLM 标注时, collect_seeds 把 what/why/still_niche 一并带出给前端。"""
    from app.discovery.annotate import Annotation
    day1 = [_hn("1", "Rising", 30)]
    store.score(day1, run_id="day1", now_iso="day1")
    store.commit_run(day1, run_id="day1", now_iso="day1")
    day2 = [_hn("1", "Rising", 95)]
    scored = store.score(day2, run_id="day2", now_iso="day2")
    anns = {"1": Annotation(external_id="1", what="一个新方法", why="可能降本", still_niche=False)}
    seeds = report.collect_seeds(scored, has_history=True, annotations=anns)
    assert seeds[0]["what"] == "一个新方法"
    assert seeds[0]["why"] == "可能降本"
    assert seeds[0]["still_niche"] is False


def test_distill_degrades_without_llm(monkeypatch):
    """distill_topic 无 LLM key 时降级到启发式截断, llm=False, 绝不报错。"""
    from app import config
    from app.discovery import annotate
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    r = annotate.distill_topic("The Download: brain-melting heatwaves and OpenAI restrictions", "tech")
    assert r["llm"] is False
    # 启发式应去掉 "The Download:" 栏目前缀
    assert "Download" not in r["query"]
    assert r["query"]


def test_heuristic_topic_strips_noise():
    """启发式提炼: 去栏目前缀 / 取冒号前主干 / 去 [pdf] 括注。"""
    from app.discovery.annotate import _heuristic_topic
    assert _heuristic_topic("DSpark: Speculative decoding accelerates LLM inference [pdf]") == "DSpark"
    assert "[pdf]" not in _heuristic_topic("Some title [pdf]")
    assert _heuristic_topic("The Download: AI restrictions").strip() == "AI restrictions"


def test_arxiv_id_strips_version():
    """external_id 必须跨天稳定: 去掉 vN 版本后缀让同一篇论文对齐。"""
    assert _arxiv_id("http://arxiv.org/abs/2406.01234v2") == "2406.01234"
    assert _arxiv_id("http://arxiv.org/abs/2406.01234") == "2406.01234"
    assert _arxiv_id("http://arxiv.org/abs/2406.01234v15") == "2406.01234"


def test_runs_seen_accumulates(store):
    """runs_seen 跨运行累加 -> 衡量一个苗头的持续性。"""
    item = _hn("1", "Persistent", 40)
    store.score([item], run_id="day1", now_iso="day1")
    store.commit_run([item], run_id="day1", now_iso="day1")
    store.commit_run([item], run_id="day2", now_iso="day2")
    scored = store.score([item], run_id="day3", now_iso="day3")
    assert scored[0].runs_seen == 3


def test_config_driven_sources_have_domains():
    """配置化前沿源: 加载 enabled 源, 覆盖多个领域 (突破技术圈)。"""
    from app.discovery import sources
    cfg = sources.load_frontier_config()
    assert len(cfg) >= 2
    domains = {s.get("domain") for s in cfg}
    # 至少应有技术之外的领域 (金融/地缘), 否则就退化回纯技术圈了
    assert domains - {"tech"}, "前沿源应覆盖技术圈之外的领域"


def test_annotate_degrades_without_llm(monkeypatch):
    """无 LLM key 时, 标注层静默降级返回空 dict, 绝不报错 (守住无-LLM 红线)。"""
    from app import config
    from app.discovery import annotate
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    seeds = [type("S", (), {"item": _hn("1", "x", 40)})()]
    assert annotate.annotate_seeds(seeds) == {}


def test_report_renders_with_annotations(store):
    """带标注时, 报告在种子下渲染 LLM 解读。"""
    from app.discovery import report
    from app.discovery.annotate import Annotation
    day1 = [_hn("1", "Rising", 30)]
    store.score(day1, run_id="d1", now_iso="d1")
    store.commit_run(day1, run_id="d1", now_iso="d1")
    day2 = [_hn("1", "Rising", 95)]
    scored = store.score(day2, run_id="d2", now_iso="d2")
    anns = {"1": Annotation(external_id="1", what="一个新方法", why="可能降低推理成本", still_niche=True)}
    md = report.build_report(scored, run_id="d2", has_history=True, annotations=anns)
    assert "一个新方法" in md
    assert "还在小圈子" in md


def test_same_day_rerun_keeps_fresh_seed(store):
    """关键修复: 今天首见的论文, 同一天重跑仍是种子 (不因被轮询两次而被打成噪声)。"""
    from app.discovery import report
    paper = DiscoveryItem(source="arxiv", external_id="2606.001", title="Fresh paper",
                          url="http://arxiv.org/abs/2606.001", category="cs.AI")
    # 上午 09:00 首见
    store.score([paper], run_id="2026-06-28T09:00:00Z", now_iso="2026-06-28T09:00:00Z")
    store.commit_run([paper], run_id="2026-06-28T09:00:00Z", now_iso="2026-06-28T09:00:00Z")
    # 同日 11:00 重跑: age=2h, 仍在新鲜窗口 -> 仍是种子
    scored = store.score([paper], run_id="2026-06-28T11:00:00Z", now_iso="2026-06-28T11:00:00Z")
    assert scored[0].is_new is False              # 确实被见过两次
    assert scored[0].age_hours == 2.0
    assert report.categorize(scored[0], has_history=True) == "seed"  # 但仍是种子!


def test_stale_item_ages_out_to_noise(store):
    """超过新鲜窗口 (FRESH_HOURS) 的旧条目, 老化成噪声。"""
    from app.discovery import report
    paper = DiscoveryItem(source="arxiv", external_id="2606.002", title="Old paper",
                          url="http://arxiv.org/abs/2606.002", category="cs.AI")
    store.score([paper], run_id="2026-06-25T09:00:00Z", now_iso="2026-06-25T09:00:00Z")
    store.commit_run([paper], run_id="2026-06-25T09:00:00Z", now_iso="2026-06-25T09:00:00Z")
    # 3 天后重跑: age=72h > 36h 窗口 -> 老化进噪声
    scored = store.score([paper], run_id="2026-06-28T09:00:00Z", now_iso="2026-06-28T09:00:00Z")
    assert scored[0].age_hours == 72.0
    assert report.categorize(scored[0], has_history=True) == "noise"
