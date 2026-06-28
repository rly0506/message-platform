from app import rule_config
from app.pipeline import local_analyze


def test_rule_config_loads_media_tiers_and_entities():
    data = rule_config.load_rule_config()

    assert "media_source_tiers" in data
    assert "entity_aliases" in data
    assert local_analyze._source_tier("Reuters") == "wire"
    assert local_analyze.MEDIA_TIER_LABELS["wire"] == "通讯社"

    aliases = local_analyze.ENTITY_ALIASES
    assert aliases["特朗普"][0] == "person"
    assert "Trump" in aliases["特朗普"][1]
    assert aliases["伊斯兰革命卫队"][0] == "organization"
