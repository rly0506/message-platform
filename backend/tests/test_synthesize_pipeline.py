from app.pipeline import synthesize as synthp


def test_synthesize_builds_fallback_analysis_when_llm_returns_empty(monkeypatch):
    monkeypatch.setattr(
        synthp,
        "synth_timeline",
        lambda name, desc, rows: [
            {
                "date": "2026-06-01",
                "title_zh": "冲突升级",
                "summary_zh": "多家媒体确认冲突升级。",
                "article_ids": [1, 2],
            }
        ],
    )
    monkeypatch.setattr(
        synthp,
        "synth_framing",
        lambda name, desc, rows: [
            {
                "party": "测试媒体",
                "stance": "关注升级风险",
                "summary_zh": "强调冲突升级与信息缺口。",
                "article_ids": [1],
            }
        ],
    )
    monkeypatch.setattr(synthp, "synth_analysis", lambda name, desc, timeline, framing: "")

    data = synthp.synthesize(
        "测试事件",
        "测试说明",
        [
            {
                "id": 1,
                "date": "2026-06-01",
                "source": "测试来源",
                "lang": "zh",
                "stance": "关注升级风险",
                "title_zh": "测试报道",
            }
        ],
    )

    assert data["analysis_md"]
    assert "LLM 批判分析未返回有效正文" in data["analysis_md"]
    assert "冲突升级" in data["analysis_md"]
    assert "测试媒体" in data["analysis_md"]
