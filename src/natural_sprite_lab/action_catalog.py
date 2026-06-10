from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AssetRecipe:
    name: str
    prompt: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PDCARunConfig:
    name: str
    steps: int
    cfg: float
    controlnet_strength: float
    seed_step: int = 0

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


DEFAULT_ASSET_RECIPES: tuple[AssetRecipe, ...] = (
    AssetRecipe(
        name="walk",
        prompt=(
            "Create an 8-frame side-view walking animation, facing right. Interpret the reference as a "
            "character design and generate new full-body frames of the same character walking."
        ),
    ),
    AssetRecipe(
        name="idle",
        prompt=(
            "Create an 8-frame calm idle breathing animation, facing right. Interpret the reference as a "
            "character design and generate new full-body frames of the same character standing naturally."
        ),
    ),
    AssetRecipe(
        name="attack_sword",
        prompt=(
            "Create an 8-frame quick sword slash attack animation, facing right. Interpret the reference as a "
            "character design. Generate one new full-body game animation frame per output image, showing the "
            "same character using a sword slash attack."
        ),
    ),
    AssetRecipe(
        name="attack_axe",
        prompt=(
            "Create an 8-frame heavy axe swing attack animation, facing right. Interpret the reference as a "
            "character design. Generate one new full-body game animation frame per output image, showing the "
            "same character holding a large axe and performing a heavy overhead chop."
        ),
    ),
    AssetRecipe(
        name="attack_bow",
        prompt=(
            "Create an 8-frame bow attack animation, facing right. Interpret the reference as a character "
            "design. Generate one new full-body game animation frame per output image, showing the same "
            "character drawing a bow, aiming, and releasing an arrow."
        ),
    ),
    AssetRecipe(
        name="hit_light",
        prompt=(
            "Create an 8-frame light hit reaction animation, facing right. Interpret the reference as a "
            "character design. Generate one new full-body game animation frame per output image, showing the "
            "same character making a small stagger from a weak hit."
        ),
    ),
    AssetRecipe(
        name="hit_heavy",
        prompt=(
            "Create an 8-frame heavy damage reaction animation, facing right. Interpret the reference as a "
            "character design. Generate one new full-body game animation frame per output image, showing the "
            "same character taking big damage with a strong recoil."
        ),
    ),
    AssetRecipe(
        name="hit_knockback",
        prompt=(
            "Create an 8-frame knockback damage reaction animation, facing right. Interpret the reference as a "
            "character design. Generate one new full-body game animation frame per output image, showing the "
            "same character being blown away backward by a powerful hit."
        ),
    ),
)


DEFAULT_PDCA_CONFIGS: tuple[PDCARunConfig, ...] = (
    PDCARunConfig(name="balanced", steps=24, cfg=6.0, controlnet_strength=0.75, seed_step=0),
    PDCARunConfig(name="strong_pose", steps=24, cfg=6.0, controlnet_strength=0.9, seed_step=0),
)


ATTACK_VARIANT_TOKENS: dict[str, tuple[str, ...]] = {
    "bow": ("bow", "arrow", "archer", "\u5f13", "\u77e2"),
    "axe": ("axe", "hatchet", "\u65a7"),
}

HIT_VARIANT_TOKENS: dict[str, tuple[str, ...]] = {
    "knockback": ("knockback", "blown away", "launch", "\u5439\u304d\u98db\u3070\u3057", "\u5439\u304d\u98db\u3076"),
    "heavy": ("heavy", "big damage", "large damage", "\u5927\u30c0\u30e1\u30fc\u30b8", "\u5f37\u653b\u6483"),
}


def detect_attack_variant(prompt: str) -> str:
    text = prompt.lower()
    for variant, tokens in ATTACK_VARIANT_TOKENS.items():
        if _contains_any(text, tokens):
            return variant
    return "sword"


def detect_hit_variant(prompt: str) -> str:
    text = prompt.lower()
    for variant, tokens in HIT_VARIANT_TOKENS.items():
        if _contains_any(text, tokens):
            return variant
    return "light"


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token.lower() in text for token in tokens)
