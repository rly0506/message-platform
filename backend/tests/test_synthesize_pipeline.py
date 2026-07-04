from app.pipeline import synthesize as synthp


def test_listing_includes_local_evidence_fields_without_full_body():
    text = synthp._listing([
        {
            "id": 7,
            "date": "2026-06-01",
            "source": "Reuters",
            "lang": "en",
            "stance": "中立观察",
            "title_zh": "前线态势更新",
            "snippet": "多源摘要，不是全文。",
            "source_type": "rss",
            "quality_tier": "wire",
            "category": "行动进展",
        }
    ])

    assert "tier:wire" in text
    assert "type:rss" in text
    assert "类别:行动进展" in text
    assert "摘要:多源摘要，不是全文。" in text
    assert "全文" not in text.replace("不是全文", "")


def test_synth_timeline_prompt_uses_evidence_package_context(monkeypatch):
    prompts = []

    def fake_call_json(prompt, max_tokens):
        prompts.append(prompt)
        return []

    monkeypatch.setattr(synthp, "_call_json", fake_call_json)

    synthp.synth_timeline(
        "俄乌战争",
        "测试说明",
        [
            {
                "id": 1,
                "date": "2026-06-01",
                "source": "Reuters",
                "lang": "en",
                "stance": "中立观察",
                "title_zh": "前线态势更新",
                "snippet": "本地摘要",
                "source_type": "rss",
                "quality_tier": "wire",
                "category": "行动进展",
            }
        ],
        evidence_package={
            "events": [
                {
                    "date": "2026-06-01",
                    "title_zh": "本地候选事件",
                    "summary_zh": "2 个来源集中指向这一节点。",
                    "article_ids": [1],
                    "source_count": 2,
                }
            ],
            "narrative_signals": [
                {
                    "claim": "补给线变化",
                    "source_count": 2,
                    "article_count": 3,
                }
            ],
        },
    )

    prompt = prompts[0]
    assert "本地预分析候选事件" in prompt
    assert "本地候选事件" in prompt
    assert "补给线变化" in prompt
    assert "前线态势更新" in prompt


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
