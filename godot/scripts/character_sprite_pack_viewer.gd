extends Control

const AssetManifest = preload("res://scripts/asset_manifest.gd")

@export_file("*.json") var manifest_path := "../outputs/adoptable/character_sprite_asset_pack/manifest.json"
@export var start_action := "walk"

@onready var sprite: AnimatedSprite2D = $Stage/Sprite
@onready var info: Label = $Info
@onready var controls: Label = $Controls
@onready var action_buttons: HBoxContainer = $ActionButtons
@onready var action_meta: Label = $ActionMeta
@onready var frame_meta: Label = $FrameMeta
@onready var stage: Node2D = $Stage

var manifest: Dictionary = {}
var validation: Dictionary = {}
var current_action := ""
var action_order: PackedStringArray = []

const PREFERRED_ACTION_ORDER := [
	"idle",
	"walk",
	"run",
	"jump",
	"hurt",
	"dodge_backstep",
	"parry_sword",
	"attack_sword_light",
]


func _ready() -> void:
	manifest = AssetManifest.load_manifest(manifest_path)
	validation = AssetManifest.validate_pack(manifest)
	if not validation.get("ok", false):
		info.text = "Pack validation failed: %s" % validation.get("error", "unknown")
		push_error(info.text)
		return

	sprite.sprite_frames = AssetManifest.build_pack_sprite_frames(manifest)
	_scale_sprite()
	action_order = _ordered_action_names()
	_build_action_buttons()
	controls.text = "1-8: action  /  Left-Right: previous-next  /  Space: pause  /  R: restart"

	var action := start_action
	if not action_order.has(action):
		action = action_order[0]
	_play_action(action)


func _build_action_buttons() -> void:
	for child in action_buttons.get_children():
		child.queue_free()

	for index in range(action_order.size()):
		var action := action_order[index]
		var button := Button.new()
		button.text = "%d %s" % [index + 1, action]
		button.tooltip_text = _action_tooltip(action)
		button.pressed.connect(func() -> void: _play_action(action))
		action_buttons.add_child(button)


func _play_action(action: String) -> void:
	if sprite.sprite_frames == null or not sprite.sprite_frames.has_animation(action):
		return
	current_action = action
	sprite.animation = action
	sprite.frame = 0
	sprite.play(action)

	var actions: Dictionary = manifest.get("actions", {})
	var action_info: Dictionary = actions.get(action, {})
	var runtime: Dictionary = action_info.get("runtime", {})
	var origin: Dictionary = runtime.get("origin", {})
	sprite.centered = false
	sprite.offset = Vector2(-float(origin.get("x", 0.0)), -float(origin.get("y", 0.0)))
	_center_stage_for_action(action_info)
	var frame_size: Dictionary = action_info.get("frame_size", {})
	info.text = "%s / %d frames / %dx%d / %s" % [
		action,
		int(action_info.get("frame_count", 0)),
		int(frame_size.get("width", 0)),
		int(frame_size.get("height", 0)),
		"loop" if bool(runtime.get("loop", true)) else "once",
	]
	action_meta.text = "fps=%s origin=%s collision=%s" % [
		str(runtime.get("fps", "")),
		str(runtime.get("origin", {})),
		str(runtime.get("collision_box", {})),
	]
	_update_frame_meta()


func _process(_delta: float) -> void:
	if current_action != "":
		_update_frame_meta()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var key := event as InputEventKey
		if key.keycode >= KEY_1 and key.keycode <= KEY_8:
			var index := key.keycode - KEY_1
			if index < action_order.size():
				_play_action(action_order[index])
		elif key.keycode == KEY_RIGHT:
			_play_relative_action(1)
		elif key.keycode == KEY_LEFT:
			_play_relative_action(-1)
		elif key.keycode == KEY_SPACE:
			if sprite.is_playing():
				sprite.pause()
			else:
				sprite.play(current_action)
		elif key.keycode == KEY_R:
			_play_action(current_action)


func _play_relative_action(offset: int) -> void:
	if action_order.is_empty() or current_action == "":
		return
	var index := action_order.find(current_action)
	if index < 0:
		index = 0
	index = wrapi(index + offset, 0, action_order.size())
	_play_action(action_order[index])


func _update_frame_meta() -> void:
	if sprite.sprite_frames == null or current_action == "":
		return
	var frame_count := sprite.sprite_frames.get_frame_count(current_action)
	frame_meta.text = "%s frame %02d / %02d" % [
		"playing" if sprite.is_playing() else "paused",
		sprite.frame + 1,
		frame_count,
	]


func _ordered_action_names() -> PackedStringArray:
	var available := AssetManifest.pack_action_names(manifest)
	var ordered := PackedStringArray()
	for action in PREFERRED_ACTION_ORDER:
		if available.has(action):
			ordered.append(action)
	for action in available:
		if not ordered.has(action):
			ordered.append(action)
	return ordered


func _action_tooltip(action: String) -> String:
	var actions: Dictionary = manifest.get("actions", {})
	var action_info: Dictionary = actions.get(action, {})
	var runtime: Dictionary = action_info.get("runtime", {})
	var phase_names: Array = action_info.get("phase_names", [])
	var phases := PackedStringArray()
	for phase in phase_names:
		phases.append(str(phase))
	return "%s frames, %s, phases: %s" % [
		str(action_info.get("frame_count", "?")),
		"loop" if bool(runtime.get("loop", true)) else "one-shot",
		", ".join(phases),
	]


func _scale_sprite() -> void:
	var frame_size: Dictionary = validation.get("frame_size", {})
	var width := float(frame_size.get("width", 1))
	var height := float(frame_size.get("height", 1))
	var max_extent = max(width, height)
	if max_extent > 0:
		sprite.scale = Vector2.ONE * min(1.0, 520.0 / max_extent)


func _center_stage_for_action(action_info: Dictionary) -> void:
	var runtime: Dictionary = action_info.get("runtime", {})
	var origin: Dictionary = runtime.get("origin", {})
	var visible_bbox: Dictionary = runtime.get("visible_bbox", {})
	var bbox_center := Vector2(
		float(visible_bbox.get("x", 0.0)) + float(visible_bbox.get("width", 0.0)) * 0.5,
		float(visible_bbox.get("y", 0.0)) + float(visible_bbox.get("height", 0.0)) * 0.5
	)
	var origin_point := Vector2(float(origin.get("x", 0.0)), float(origin.get("y", 0.0)))
	var visual_center_from_origin := (bbox_center - origin_point) * sprite.scale
	var viewport_center := get_viewport_rect().size * 0.5
	stage.position = viewport_center - visual_center_from_origin


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED and current_action != "":
		var actions: Dictionary = manifest.get("actions", {})
		_center_stage_for_action(actions.get(current_action, {}))
