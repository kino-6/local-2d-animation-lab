class_name CharacterSpritePackPlayer
extends CharacterBody2D

const AssetManifest = preload("res://scripts/asset_manifest.gd")

@export_file("*.json") var manifest_path := "../outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json"
@export var require_production_ready := true
@export var walk_speed := 120.0
@export var run_speed := 190.0
@export var jump_velocity := -320.0
@export var gravity := 980.0

@onready var sprite: AnimatedSprite2D = $Sprite
@onready var collision_shape: CollisionShape2D = $CollisionShape2D

var manifest: Dictionary = {}
var validation: Dictionary = {}
var current_action := ""
var _locked_action := ""


func _ready() -> void:
	load_pack(manifest_path)


func load_pack(path: String) -> Dictionary:
	manifest = AssetManifest.load_manifest(path)
	validation = AssetManifest.validate_pack(manifest)
	if not validation.get("ok", false):
		return validation
	if require_production_ready and not bool(validation.get("production_ready", false)):
		validation = {
			"ok": false,
			"error": "pack is not production_ready",
			"production_ready": false,
		}
		return validation

	sprite.sprite_frames = AssetManifest.build_pack_sprite_frames(manifest)
	_play_action("idle")
	return validation


func apply_gameplay_input(
	move_axis: float,
	jump_pressed: bool,
	run_pressed: bool,
	attack_pressed: bool,
	hurt_pressed: bool,
	delta: float,
	on_floor_override := true
) -> void:
	var grounded := on_floor_override or is_on_floor()
	var target_speed := run_speed if run_pressed else walk_speed
	velocity.x = move_axis * target_speed
	if jump_pressed and grounded:
		velocity.y = jump_velocity
	elif not grounded:
		velocity.y += gravity * delta
	else:
		velocity.y = 0.0

	_update_action_from_state(move_axis, jump_pressed, run_pressed, attack_pressed, hurt_pressed, grounded)


func _physics_process(delta: float) -> void:
	var move_axis := Input.get_axis("ui_left", "ui_right")
	var jump_pressed := Input.is_action_just_pressed("ui_accept")
	var run_pressed := Input.is_key_pressed(KEY_SHIFT)
	var attack_pressed := Input.is_key_pressed(KEY_J)
	var hurt_pressed := Input.is_key_pressed(KEY_H)
	apply_gameplay_input(move_axis, jump_pressed, run_pressed, attack_pressed, hurt_pressed, delta, is_on_floor())
	move_and_slide()


func _update_action_from_state(
	move_axis: float,
	jump_pressed: bool,
	run_pressed: bool,
	attack_pressed: bool,
	hurt_pressed: bool,
	grounded: bool
) -> void:
	if hurt_pressed:
		_play_one_shot("hurt")
	elif attack_pressed:
		_play_one_shot("attack_sword_light")
	elif jump_pressed or not grounded:
		_play_one_shot("jump")
	elif absf(move_axis) > 0.1:
		_locked_action = ""
		_play_action("run" if run_pressed else "walk")
	else:
		if _locked_action != "" and sprite.is_playing():
			return
		_locked_action = ""
		_play_action("idle")


func _play_one_shot(action: String) -> void:
	_locked_action = action
	_play_action(action)


func _play_action(action: String) -> void:
	if sprite.sprite_frames == null or not sprite.sprite_frames.has_animation(action):
		return
	if current_action == action and sprite.is_playing():
		return
	current_action = action
	_apply_runtime_metadata(action)
	sprite.play(action)


func _apply_runtime_metadata(action: String) -> void:
	var action_info: Dictionary = manifest.get("actions", {}).get(action, {})
	var runtime: Dictionary = action_info.get("runtime", {})
	var origin: Dictionary = runtime.get("origin", {})
	sprite.centered = false
	sprite.offset = Vector2(-float(origin.get("x", 0.0)), -float(origin.get("y", 0.0)))

	var collision: Dictionary = runtime.get("collision_box", {})
	if collision_shape != null and not collision.is_empty():
		var shape := RectangleShape2D.new()
		shape.size = Vector2(
			float(collision.get("width", 1.0)),
			float(collision.get("height", 1.0))
		)
		collision_shape.shape = shape
		collision_shape.position = Vector2(
			float(collision.get("x", 0.0)) + shape.size.x * 0.5 - float(origin.get("x", 0.0)),
			float(collision.get("y", 0.0)) + shape.size.y * 0.5 - float(origin.get("y", 0.0))
		)


func gameplay_summary() -> Dictionary:
	var shape_size := Vector2.ZERO
	if collision_shape.shape is RectangleShape2D:
		shape_size = (collision_shape.shape as RectangleShape2D).size
	return {
		"ok": bool(validation.get("ok", false)),
		"production_ready": bool(validation.get("production_ready", false)),
		"current_action": current_action,
		"sprite_frame_count": sprite.sprite_frames.get_frame_count(current_action) if sprite.sprite_frames != null and current_action != "" else 0,
		"collision_size": {"width": shape_size.x, "height": shape_size.y},
	}
