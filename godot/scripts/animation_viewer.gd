extends Control

const AssetManifest = preload("res://scripts/asset_manifest.gd")

@export_file("*.json") var manifest_path := "../outputs_action_variants_effect_pdca/anima_00013/attack/attack_bow_balanced/manifest.json"
@export var prefer_composited := true
@export var fps := 8.0

@onready var sprite: AnimatedSprite2D = $Stage/Sprite
@onready var info: Label = $Info


func _ready() -> void:
	var manifest := AssetManifest.load_manifest(manifest_path)
	var validation := AssetManifest.validate(manifest, prefer_composited)
	if not validation.get("ok", false):
		info.text = "Validation failed: %s" % validation.get("error", "unknown")
		push_error(info.text)
		return

	sprite.sprite_frames = AssetManifest.build_sprite_frames(manifest, fps, prefer_composited)
	sprite.animation = "asset"
	sprite.play()
	var size: Dictionary = validation.get("frame_size", {})
	var width := float(size.get("width", 1))
	var height := float(size.get("height", 1))
	var max_extent = max(width, height)
	if max_extent > 0:
		sprite.scale = Vector2.ONE * min(0.55, 520.0 / max_extent)

	info.text = "%s / %s / %d frames / %dx%d" % [
		validation.get("character_id", ""),
		validation.get("action", ""),
		validation.get("frame_count", 0),
		int(width),
		int(height),
	]
