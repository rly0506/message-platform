"""发现层测试 —— 用 fixture 证明加速逻辑, 不靠网络、不靠等一天。

核心验证 (发现区别于搜索的本质):
- 首次运行无历史 -> 只建基线, 报告标注"明天起才有加速"。
- 第二次运行 -> 同一 item 的 signal 上涨能被算成 delta, 全新 item 被标 is_new。
- 分类: 低基数在涨 -> seed; 信号已很大 -> mainstream; 低信号没涨 -> noise。
"""
import json
import os
from pathlib import Path

import pytest

from app.discovery.sources import DiscoveryItem, _arxiv_id
from app.discovery.store import DiscoveryStore
from app.discovery import report


@pytest.fixture()
def store(tmp_path):
    path = tmp_path / "discovery_test.db"
    instance = DiscoveryStore(db_path=str(path))
    yield instance
    instance.close()


def test_store_fixture_uses_per_test_database(store, tmp_path):
    assert Path(store.db_path).parent == tmp_path


def _hn(ext_id, title, points, comments=0):
    return DiscoveryItem(source="hackernews", external_id=ext_id, title=title,
                         url=f"https://news.ycombinator.com/item?id={ext_id}",
                         signal=points, engagement=comments)


def _write_report_pair(directory, run_id, markdown, seeds=None, sidecar=True):
    safe = run_id.replace(":", "").replace("-", "")
    md_path = os.path.join(directory, f"frontier-{safe}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    if sidecar:
        with open(md_path[:-3] + ".json", "w", encoding="utf-8") as f:
            json.dump(seeds or [], f, ensure_ascii=False)
    return md_path


@pytest.fixture()
def reports_dir(monkeypatch, tmp_path):
    from app.discovery import run
    monkeypatch.setattr(run, "REPORTS_DIR", str(tmp_path))
    return tmp_path


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
    assert seed["info_value_labels"] == [
        {
            "code": "availability_high",
            "label": "可得性偏高",
            "note": "信号正在快速上升，提示先把它当早期线索，而不是已经被充分验证的结论。",
            "severity": "hint",
        },
    ]
    # 必备字段齐全 (前端依赖)
    for key in ("title", "url", "domain", "domain_label", "signal", "delta", "is_new",
                "what", "why", "still_niche", "info_value_labels"):
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


def test_synthesis_degrades_without_llm(monkeypatch):
    """无 LLM key 时, 综述层返回 "" (优雅降级, 报告仍出清单, 不报错)。"""
    from app import config
    from app.discovery import annotate
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    seeds = [type("S", (), {"item": _hn("1", "x", 40)})()]
    assert annotate.synthesize_frontier(seeds) == ""
    # 无种子也返回 "" (不浪费一次 LLM 调用)
    assert annotate.synthesize_frontier([]) == ""


def test_synthesis_uses_llm_when_available(monkeypatch):
    """有 LLM key 时, 综述层调用 llm.chat 并返回其正文 (去掉模型自带的一级标题)。"""
    from app import config
    from app.discovery import annotate
    monkeypatch.setattr(config, "LLM_API_KEY", "fake-key")

    captured = {}

    def fake_chat(model, prompt, max_tokens=0, system=""):
        captured["prompt"] = prompt
        return "# 综述\n今天前沿的主线是推理加速。"

    import app.llm as llm_mod
    monkeypatch.setattr(llm_mod, "chat", fake_chat)
    seeds = [type("S", (), {"item": _hn("1", "Speculative decoding", 90)})()]
    out = annotate.synthesize_frontier(seeds)
    assert "推理加速" in out
    assert not out.startswith("#")  # 模型自带的一级标题被剥掉
    assert "Speculative decoding" in captured["prompt"]  # 种子标题进了 prompt


def test_report_renders_synthesis_section():
    """build_report 收到 synthesis 时, 在顶部渲染「前沿综述」段; 空则不出该段。"""
    from app.discovery import report
    scored = []  # 综述段不依赖具体条目, 只看 synthesis 入参
    md = report.build_report(scored, run_id="d2", has_history=False,
                             synthesis="今天主线是推理加速。")
    assert "📰 前沿综述" in md
    assert "今天主线是推理加速。" in md
    # 无综述时不出该段 (降级路径)
    md2 = report.build_report(scored, run_id="d2", has_history=False, synthesis="")
    assert "前沿综述" not in md2


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


# ---- 主题拆解 (decompose): 下钻子角度 + 历史先例 ----

def test_decompose_degrades_without_llm(monkeypatch):
    """无 LLM key 时, 拆解返回空 (调用方退回原 query_variants 行为, 绝不报错)。"""
    from app import config
    from app.discovery import decompose
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    result = decompose.decompose_topic("中国政府债务")
    assert result.is_empty
    assert result.subtopics == []
    assert result.analogues == []


def test_decompose_empty_query_no_llm_call(monkeypatch):
    """空主题直接返回空, 不浪费一次 LLM 调用。"""
    from app import config
    from app.discovery import decompose
    monkeypatch.setattr(config, "LLM_API_KEY", "fake-key")
    # 即便有 key, 空 query 也不该触发调用 (这里不打桩 llm.chat, 调到就会真连网)
    assert decompose.decompose_topic("   ").is_empty


def test_decompose_parses_both_lists(monkeypatch):
    """有 LLM 时, 拆解出 subtopics (下钻) 与 analogues (历史) 两组。"""
    from app import config
    from app.discovery import decompose
    monkeypatch.setattr(config, "LLM_API_KEY", "fake-key")

    def fake_chat(model, prompt, max_tokens=0, system=""):
        return (
            '{"subtopics": ["中央政府债务", "地方政府债务", "化债 隐性债务"], '
            '"analogues": ["2008 雷曼破产", "1997 亚洲金融危机"]}'
        )

    import app.llm as llm_mod
    monkeypatch.setattr(llm_mod, "chat", fake_chat)
    result = decompose.decompose_topic("中国政府债务")
    assert "中央政府债务" in result.subtopics
    assert "地方政府债务" in result.subtopics
    assert "1997 亚洲金融危机" in result.analogues


def test_decompose_clean_list_dedups_and_caps():
    """_clean_list: 去空、去重、限量。"""
    from app.discovery.decompose import _clean_list
    out = _clean_list(["a", "a", "", "  b  ", "c", "d", "e", "f", "g", "h", "i"], limit=8)
    assert out[:3] == ["a", "b", "c"]
    assert len(out) == 8  # 限到 8
    assert _clean_list("not a list") == []
    assert _clean_list(None) == []


def test_search_request_rejects_blank_query():
    from pydantic import ValidationError

    from app.schemas.search import SearchRequest

    with pytest.raises(ValidationError):
        SearchRequest(query="   ")


def test_run_search_caps_expansion_and_never_expands_analogues(monkeypatch):
    """run_search: 只把前 3 条 subtopics 作为本次 extra_queries; analogues 绝不进采集 (避免旧闻污染)。"""
    from app.services import search_service
    from app.discovery.decompose import Decomposition
    from app.schemas.search import SearchRequest

    monkeypatch.setattr(search_service, "EXPAND_SUBTOPIC_LIMIT", 3, raising=True)
    import app.discovery.decompose as dec_mod
    monkeypatch.setattr(
        dec_mod, "decompose_topic",
        lambda q, model="": Decomposition(
            subtopics=["中央债", "地方债", "化债", "城投债", "专项债"],
            analogues=["1997 亚洲金融危机", "2008 雷曼"],
        ),
    )

    captured = {}

    # topic 用真实 query_variants (不含拆解项); 拆解项应只作为 extra_queries 进 collect_topic。
    def fake_get_or_create_topic(session, name, queries=None):
        captured["topic_queries"] = queries or []
        return type("T", (), {"id": 1, "name": name, "queries": queries or []})()

    def fake_collect_topic(session, topic, **kwargs):
        captured["extra_queries"] = kwargs.get("extra_queries") or []
        raise RuntimeError("stop-after-collect")  # 截断: 只验 queries 构造

    monkeypatch.setattr(search_service.topic_ops, "get_or_create_topic", fake_get_or_create_topic)
    monkeypatch.setattr(search_service.topic_ops, "collect_topic", fake_collect_topic)

    with pytest.raises(RuntimeError, match="stop-after-collect"):
        search_service.run_search(SearchRequest(query="中国政府债务", collect=True))

    # topic 持久化的 queries 只有确定性变体, 绝无拆解项
    assert "中央债" not in captured["topic_queries"]
    extra = captured["extra_queries"]
    # 前 3 条子角度作为本次临时检索词
    assert extra == ["中央债", "地方债", "化债"]
    # 第 4、5 条超出 cap, 不进
    assert "城投债" not in extra and "专项债" not in extra
    # 历史先例绝不进采集
    assert "1997 亚洲金融危机" not in extra and "2008 雷曼" not in extra


def test_run_search_decompose_off_no_extra_queries(monkeypatch):
    """decompose=False 时, 不拆解, extra_queries 为空, topic queries 退回原变体。"""
    from app.services import search_service
    from app.schemas.search import SearchRequest

    captured = {}

    def fake_get_or_create_topic(session, name, queries=None):
        captured["topic_queries"] = queries or []
        return type("T", (), {"id": 1, "name": name, "queries": queries or []})()

    def fake_collect_topic(session, topic, **kwargs):
        captured["extra_queries"] = kwargs.get("extra_queries") or []
        raise RuntimeError("stop")

    monkeypatch.setattr(search_service.topic_ops, "get_or_create_topic", fake_get_or_create_topic)
    monkeypatch.setattr(search_service.topic_ops, "collect_topic", fake_collect_topic)
    with pytest.raises(RuntimeError, match="stop"):
        search_service.run_search(SearchRequest(query="美伊战争", collect=True, decompose=False))

    assert captured["topic_queries"] == ["美伊战争", "美伊战争 最新 影响"]
    assert captured["extra_queries"] == []  # 没有拆解项


def test_collect_topic_extra_queries_not_persisted(monkeypatch):
    """关键回归 (GPT 审核发现): extra_queries 只影响本次采集, 绝不写回 topic.queries。

    否则一次拆解后, 后续 decompose=False 也会继续用旧 subtopics 采集。
    """
    from app import topic_ops
    from app.db import Topic, engine, init_db
    from sqlmodel import Session
    init_db()

    seen_queries: list[str] = []

    def fake_gnews(query):
        seen_queries.append(query)
        return []  # 不需要真数据, 只验证哪些 query 被采集

    monkeypatch.setattr(topic_ops.rss, "collect_gnews", fake_gnews)

    with Session(engine) as session:
        topic = Topic(name="持久化回归", queries=["持久化回归", "持久化回归 最新 影响"])
        session.add(topic)
        session.commit()
        session.refresh(topic)
        try:
            topic_ops.collect_topic(session, topic, gnews=True,
                                    extra_queries=["子角度A", "子角度B"])
            # extra_queries 参与了本次采集
            assert "子角度A" in seen_queries and "子角度B" in seen_queries
            # 但绝没写回 topic.queries (重新读库确认)
            session.refresh(topic)
            assert "子角度A" not in topic.queries
            assert "子角度B" not in topic.queries
            assert topic.queries == ["持久化回归", "持久化回归 最新 影响"]
        finally:
            session.delete(topic)
            session.commit()


def test_discovery_report_archive_lists_reports_newest_first(reports_dir):
    from app.discovery import run

    _write_report_pair(
        str(reports_dir),
        "2026-06-29T01:00:00Z",
        "# old report",
        seeds=[{"title": "Old AI seed", "domain": "ai"}],
    )
    _write_report_pair(
        str(reports_dir),
        "2026-07-02T13:57:34Z",
        "# latest report",
        seeds=[
            {"title": "Latest energy seed", "domain": "energy"},
            {"title": "Second energy seed", "domain": "energy"},
        ],
    )
    _write_report_pair(
        str(reports_dir),
        "2026-06-30T04:30:06Z",
        "# middle report",
        sidecar=False,
    )

    reports = run.list_reports()

    assert [item["run_id"] for item in reports] == [
        "20260702T135734Z",
        "20260630T043006Z",
        "20260629T010000Z",
    ]
    assert reports[0]["created_at"] == "20260702T135734Z"
    assert reports[0]["seed_count"] == 2
    assert reports[0]["has_sidecar"] is True
    assert reports[1]["seed_count"] == 0
    assert reports[1]["has_sidecar"] is False


def test_report_by_run_id_reads_markdown_and_sidecar(reports_dir):
    from app.discovery import run

    _write_report_pair(
        str(reports_dir),
        "2026-07-02T13:57:34Z",
        "# archived report\nold content",
        seeds=[{"title": "Energy seed", "url": "https://example.com/e", "domain": "energy"}],
    )

    report_payload = run.report_by_run_id("20260702T135734Z")

    assert report_payload is not None
    assert "old content" in report_payload["markdown"]
    assert report_payload["run_id"] == "20260702T135734Z"
    assert report_payload["seeds"][0]["title"] == "Energy seed"


def test_report_by_run_id_missing_or_broken_sidecar_degrades_to_empty_seeds(reports_dir):
    from app.discovery import run

    _write_report_pair(str(reports_dir), "2026-07-01T00:00:00Z", "# no sidecar", sidecar=False)
    broken = _write_report_pair(str(reports_dir), "2026-07-02T00:00:00Z", "# broken sidecar", seeds=[])
    with open(broken[:-3] + ".json", "w", encoding="utf-8") as f:
        f.write("{broken json")

    assert run.report_by_run_id("20260701T000000Z")["seeds"] == []
    assert run.report_by_run_id("20260702T000000Z")["seeds"] == []


def test_report_by_run_id_rejects_path_traversal(reports_dir):
    from app.discovery import run

    _write_report_pair(str(reports_dir), "2026-07-02T13:57:34Z", "# safe")

    assert run.report_by_run_id("../frontier-20260702T135734Z") is None
    assert run.report_by_run_id("20260702T135734Z/../../x") is None
    assert run.report_by_run_id("not-a-run-id") is None


def test_discovery_archive_api_routes_return_reports(reports_dir):
    from fastapi.testclient import TestClient

    from app import api

    _write_report_pair(
        str(reports_dir),
        "2026-07-02T13:57:34Z",
        "# api latest",
        seeds=[{"title": "API seed", "url": "https://example.com/api", "domain": "energy"}],
    )
    client = TestClient(api.app)

    listing = client.get("/api/discovery/reports")
    detail = client.get("/api/discovery/reports/20260702T135734Z")

    assert listing.status_code == 200
    assert listing.json()[0]["run_id"] == "20260702T135734Z"
    assert listing.json()[0]["seed_count"] == 1
    assert detail.status_code == 200
    assert detail.json()["markdown"] == "# api latest"
    assert detail.json()["seeds"][0]["title"] == "API seed"


def test_discovery_archive_api_rejects_invalid_run_id(reports_dir):
    from fastapi.testclient import TestClient

    from app import api

    _write_report_pair(str(reports_dir), "2026-07-02T13:57:34Z", "# safe")

    response = TestClient(api.app).get("/api/discovery/reports/..%2Ffrontier-20260702T135734Z")

    assert response.status_code == 404


def test_discovery_timeline_tree_api_route(reports_dir):
    from fastapi.testclient import TestClient

    from app import api

    _write_report_pair(
        str(reports_dir),
        "2026-06-30T04:30:06Z",
        "# d1",
        seeds=[{"title": "Grid one", "url": "https://example.com/1", "domain": "energy", "domain_label": "Energy"}],
    )
    _write_report_pair(
        str(reports_dir),
        "2026-07-02T13:57:34Z",
        "# d2",
        seeds=[{"title": "Grid two", "url": "https://example.com/2", "domain": "energy", "domain_label": "Energy"}],
    )

    response = TestClient(api.app).get("/api/discovery/timeline-tree")

    assert response.status_code == 200
    assert response.json()["branches"][0]["branch_key"] == "energy"


def test_timeline_tree_groups_cross_day_seed_domains(reports_dir):
    from app.discovery import run

    _write_report_pair(
        str(reports_dir),
        "2026-06-29T01:00:00Z",
        "# d1",
        seeds=[
            {
                "title": "CPO capacity bottleneck",
                "url": "https://example.com/ai-1",
                "domain": "ai_infra",
                "domain_label": "AI infrastructure",
                "signal": 81,
                "delta": 22,
                "why": "mechanism gap",
            }
        ],
    )
    _write_report_pair(
        str(reports_dir),
        "2026-07-02T13:57:34Z",
        "# d2",
        seeds=[
            {
                "title": "Model serving cost shift",
                "url": "https://example.com/ai-2",
                "domain": "ai_infra",
                "domain_label": "AI infrastructure",
                "signal": 77,
                "delta": 18,
                "why": "same local domain",
            },
            {
                "title": "Solo biotech seed",
                "url": "https://example.com/bio",
                "domain": "biotech",
                "domain_label": "Biotech",
                "signal": 66,
                "delta": 6,
                "why": "single-day appearance",
            },
        ],
    )

    tree = run.timeline_tree()

    assert len(tree["branches"]) == 1
    branch = tree["branches"][0]
    assert branch["branch_key"] == "ai_infra"
    assert branch["label"] == "AI infrastructure"
    assert branch["connection_kind"] == "local_similarity"
    assert branch["evidence_basis"] in {
        "\u540c\u9886\u57df\u8fde\u7eed\u51fa\u73b0",
        "\u5171\u4eab\u9886\u57df\u6807\u7b7e",
        "\u672c\u5730\u76f8\u4f3c\u4fe1\u53f7",
    }
    assert {item["run_id"] for item in branch["items"]} == {"20260629T010000Z", "20260702T135734Z"}
    serialized = json.dumps(tree, ensure_ascii=False)
    for forbidden in ("\u5bfc\u81f4", "\u6839\u56e0", "\u8bc1\u660e", "\u56e0\u679c"):
        assert forbidden not in serialized


def test_timeline_tree_does_not_force_low_sample_branches(reports_dir):
    from app.discovery import run

    _write_report_pair(
        str(reports_dir),
        "2026-07-02T13:57:34Z",
        "# d1",
        seeds=[{"title": "Only seed", "url": "https://example.com/one", "domain": "energy", "domain_label": "Energy"}],
    )

    assert run.timeline_tree() == {"branches": []}


def test_timeline_tree_items_keep_cross_day_evidence_visible(reports_dir):
    from app.discovery import run

    noisy_day_one = [
        {
            "title": f"Day one grid note {index}",
            "url": f"https://example.com/day-one-{index}",
            "domain": "energy",
            "domain_label": "Energy",
            "signal": 100 - index,
            "delta": 10,
            "why": "same local domain",
        }
        for index in range(8)
    ]
    _write_report_pair(str(reports_dir), "2026-07-01T00:00:00Z", "# d1", seeds=noisy_day_one)
    _write_report_pair(
        str(reports_dir),
        "2026-07-02T00:00:00Z",
        "# d2",
        seeds=[
            {
                "title": "Day two grid note",
                "url": "https://example.com/day-two",
                "domain": "energy",
                "domain_label": "Energy",
                "signal": 50,
                "delta": 8,
                "why": "same local domain",
            }
        ],
    )

    branch = run.timeline_tree()["branches"][0]

    assert len(branch["items"]) <= 5
    assert {item["run_id"] for item in branch["items"]} == {"20260701T000000Z", "20260702T000000Z"}


def test_timeline_tree_items_prefer_latest_runs_when_branch_exceeds_limit(reports_dir):
    from app.discovery import run

    run_ids = [
        "2026-06-29T01:00:00Z",
        "2026-06-30T01:00:00Z",
        "2026-07-01T01:00:00Z",
        "2026-07-02T01:00:00Z",
        "2026-07-03T01:00:00Z",
        "2026-07-04T01:00:00Z",
    ]
    for index, run_id in enumerate(run_ids, start=1):
        _write_report_pair(
            str(reports_dir),
            run_id,
            f"# d{index}",
            seeds=[
                {
                    "title": f"Energy signal {index}",
                    "url": f"https://example.com/energy-{index}",
                    "domain": "energy",
                    "domain_label": "Energy",
                    "signal": 10 + index,
                    "delta": index,
                    "why": "same local domain",
                }
            ],
        )

    branch = run.timeline_tree()["branches"][0]

    item_run_ids = [item["run_id"] for item in branch["items"]]
    assert len(item_run_ids) == 5
    assert "20260704T010000Z" in item_run_ids
    assert "20260629T010000Z" not in item_run_ids
