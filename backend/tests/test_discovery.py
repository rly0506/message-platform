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
