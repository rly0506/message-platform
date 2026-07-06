from app.pipeline import categorization, prefilter, scoring


def test_ascii_terms_require_word_boundaries():
    assert categorization.infer_report_category("Iran warns retaliation") == "各方回应"
    assert "war" not in scoring._matched_impact_terms("Iran warns retaliation")
    assert scoring._impact_hits("Iran warns retaliation") == 0

    assert categorization.infer_stance("Bank shares rise after earnings") == "中性观察"
    assert prefilter.relevance("Bank shares rise after earnings", ["ban"]) == 0

    assert "war" in scoring._matched_impact_terms("US war risk rises")


def test_cjk_and_hyphenated_terms_keep_substring_matching():
    assert categorization.infer_stance("监管部门发布新规") == "政策/监管"
    assert "gpt-4" in scoring._matched_impact_terms("A new gpt-4 class model launches")
