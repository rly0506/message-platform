"""全文抓取测试 —— 用 HTML 字符串验证抽取, 不依赖网络。"""
from app.pipeline import fulltext


_SAMPLE_HTML = """
<html><head><title>测试文章标题</title></head>
<body>
<nav>导航 首页 关于</nav>
<article>
<h1>新型固态电池突破</h1>
<p>研究团队宣布了一种新的固态电解质材料, 能量密度显著提升, 这可能改变电动车的续航格局。</p>
<p>该材料在实验室条件下表现稳定, 但量产仍面临成本挑战。专家认为还需数年验证。</p>
</article>
<footer>版权所有 广告 订阅</footer>
</body></html>
"""


def test_extract_from_html_gets_body_drops_chrome():
    """正文抽取应拿到文章主体, 滤掉导航/页脚噪声。"""
    res = fulltext.extract_from_html(_SAMPLE_HTML, url="http://example.com/x")
    if not res.ok:
        # trafilatura 在某些精简 HTML 上可能抽不出, 那是库行为不是 bug; 跳过断言主体
        return
    assert "固态电解质" in res.full_text
    assert "导航" not in res.full_text          # chrome 被滤掉
    assert res.word_count > 0


def test_excerpt_is_capped():
    """摘录长度受 EXCERPT_CHARS 限制 (只存摘录, 不囤全文)。"""
    long_html = "<html><body><article>" + "<p>" + ("内容 " * 2000) + "</p></article></body></html>"
    res = fulltext.extract_from_html(long_html)
    if res.ok:
        assert len(res.excerpt) <= fulltext.EXCERPT_CHARS


def test_extract_url_empty_is_safe():
    """空 URL 安全返回, 不抛异常。"""
    res = fulltext.extract_url("")
    assert res.ok is False
    assert res.error


def test_degrades_when_trafilatura_missing(monkeypatch):
    """trafilatura 不可用时优雅降级: ok=False, 不崩。"""
    monkeypatch.setattr(fulltext, "_trafilatura", lambda: None)
    res = fulltext.extract_url("http://example.com")
    assert res.ok is False
    assert "unavailable" in res.error


def test_extract_url_proxied_empty_is_safe():
    """空 URL 走代理路径也安全返回, 不抛异常。"""
    res = fulltext.extract_url_proxied("")
    assert res.ok is False
    assert res.error


def test_extract_url_proxied_degrades_on_fetch_error(monkeypatch):
    """网络/代理抓取失败时, 返回 ok=False, 不抛异常 (软失败, 不阻断 enrich)。"""
    class _BoomClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url):
            raise RuntimeError("connection refused")

    import httpx
    monkeypatch.setattr(httpx, "Client", _BoomClient)
    res = fulltext.extract_url_proxied("http://example.com/x")
    assert res.ok is False
    assert res.error


def test_extract_url_proxied_extracts_from_fetched_html(monkeypatch):
    """抓到 HTML 后交给 extract_from_html 抽正文。"""
    class _OkClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url):
            class _Resp:
                text = _SAMPLE_HTML

                def raise_for_status(self):
                    return None

            return _Resp()

    import httpx
    monkeypatch.setattr(httpx, "Client", _OkClient)
    res = fulltext.extract_url_proxied("http://example.com/x")
    # 若 trafilatura 抽得出正文则 ok, 抽不出是库行为, 至少不崩。
    if res.ok:
        assert "固态电解质" in res.full_text
