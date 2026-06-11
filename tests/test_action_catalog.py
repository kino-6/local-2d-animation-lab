from natural_sprite_lab.action_catalog import DEFAULT_ASSET_RECIPES
from natural_sprite_lab.action_catalog import DEFAULT_PDCA_CONFIGS
from natural_sprite_lab.action_catalog import detect_attack_variant
from natural_sprite_lab.action_catalog import detect_hit_variant


def test_default_pdca_catalog_has_expected_assets() -> None:
    names = [recipe.name for recipe in DEFAULT_ASSET_RECIPES]

    assert names == [
        "walk",
        "run",
        "idle",
        "attack_sword",
        "attack_axe",
        "attack_bow",
        "hit_light",
        "hit_heavy",
        "hit_knockback",
    ]
    assert [config.name for config in DEFAULT_PDCA_CONFIGS] == ["balanced", "strong_pose"]


def test_detect_attack_variant_from_prompt() -> None:
    assert detect_attack_variant("quick sword slash") == "sword"
    assert detect_attack_variant("draw a bow and release an arrow") == "bow"
    assert detect_attack_variant("heavy axe overhead chop") == "axe"
    assert detect_attack_variant("\u5f13\u3067\u653b\u6483") == "bow"


def test_detect_hit_variant_from_prompt() -> None:
    assert detect_hit_variant("small stagger") == "light"
    assert detect_hit_variant("heavy large damage recoil") == "heavy"
    assert detect_hit_variant("knockback, blown away backward") == "knockback"
    assert detect_hit_variant("\u5927\u30c0\u30e1\u30fc\u30b8") == "heavy"
