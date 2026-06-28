extends Control

const AssetManifest = preload("res://scripts/asset_manifest.gd")

@export_file("*.json") var manifest_path := "../outputs/adoptable/nun_skirt_boots_character_sprite_asset_pack/manifest.json"
@export var start_action := "walk"

@onready var sprite: AnimatedSprite2D = $Stage/Sprite
@onready var body_sprite: AnimatedSprite2D = $Stage/BodySprite
@onready var weapon_sprite: AnimatedSprite2D = $Stage/WeaponSprite
@onready var effect_sprite: AnimatedSprite2D = $Stage/EffectSprite
@onready var info: Label = $Info
@onready var controls: Label = $Controls
@onready var action_buttons: HBoxContainer = $ActionButtons
@onready var speed_buttons: HBoxContainer = $SpeedButtons
@onready var action_meta: Label = $ActionMeta
@onready var frame_meta: Label = $FrameMeta
@onready var stage: Node2D = $Stage

var manifest: Dictionary = {}
var validation: Dictionary = {}
var current_action := ""
var action_order: PackedStringArray = []
var layer_sprites: Dictionary = {}
var playback_speed_multiplier := 1.0

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
	var args := OS.get_cmdline_user_args()
	manifest_path = _arg_value(args, "--manifest", manifest_path)
	start_action = _arg_value(args, "--action", start_action)

	manifest = AssetManifest.load_manifest(manifest_path)
	validation = AssetManifest.validate_pack(manifest)
	if not validation.get("ok", false):
		info.text = "Pack validation failed: %s" % validation.get("error", "unknown")
		push_error(info.text)
		return

	sprite.sprite_frames = AssetManifest.build_pack_sprite_frames(manifest)
	body_sprite.sprite_frames = AssetManifest.build_pack_layer_sprite_frames(manifest, "body")
	weapon_sprite.sprite_frames = AssetManifest.build_pack_layer_sprite_frames(manifest, "weapon")
	effect_sprite.sprite_frames = AssetManifest.build_pack_layer_sprite_frames(manifest, "effect")
	layer_sprites = {
		"body": body_sprite,
		"weapon": weapon_sprite,
		"effect": effect_sprite,
	}
	_scale_sprite()
	action_order = _ordered_action_names()
	_build_action_buttons()
	_build_speed_buttons()
	controls.text = "1-8: action  /  Left-Right: previous-next  /  Space: pause  /  R: restart  /  Z-X-C: speed"

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


func _build_speed_buttons() -> void:
	for child in speed_buttons.get_children():
		child.queue_free()

	for speed in [0.5, 1.0, 2.0]:
		var button := Button.new()
		button.text = "%sx" % speed
		button.tooltip_text = "Set preview playback speed to %sx" % speed
		button.pressed.connect(func() -> void: _set_playback_speed(speed))
		speed_buttons.add_child(button)


func _set_playback_speed(speed: float) -> void:
	playback_speed_multiplier = speed
	_apply_playback_speed()
	_update_frame_meta()


func _apply_playback_speed() -> void:
	sprite.speed_scale = playback_speed_multiplier
	for layer_sprite in layer_sprites.values():
		layer_sprite.speed_scale = playback_speed_multiplier


func _play_action(action: String) -> void:
	if sprite.sprite_frames == null or not sprite.sprite_frames.has_animation(action):
		return
	current_action = action

	var actions: Dictionary = manifest.get("actions", {})
	var action_info: Dictionary = actions.get(action, {})
	var runtime: Dictionary = action_info.get("runtime", {})
	var origin: Dictionary = runtime.get("origin", {})
	var action_is_layered := _has_layered_action(action)
	_configure_sprite_origin(sprite, origin)
	for layer_sprite in layer_sprites.values():
		_configure_sprite_origin(layer_sprite, origin)
	_set_layer_visibility(action_is_layered)
	if action_is_layered:
		for layer_name in ["body", "weapon", "effect"]:
			var layer_sprite: AnimatedSprite2D = layer_sprites[layer_name]
			if layer_sprite.sprite_frames != null and layer_sprite.sprite_frames.has_animation(action):
				layer_sprite.animation = action
				layer_sprite.frame = 0
				layer_sprite.play(action)
	else:
		sprite.animation = action
		sprite.frame = 0
		sprite.play(action)
	_apply_playback_speed()

	_center_stage_for_action(action_info)
	var frame_size: Dictionary = action_info.get("frame_size", {})
	var visual_quality: Dictionary = validation.get("visual_quality", {})
	var action_visual: Dictionary = visual_quality.get("actions", {}).get(action, {})
	var quality_text := "production_ready" if bool(validation.get("production_ready", false)) else str(visual_quality.get("decision", "quality_not_available"))
	info.text = "%s / %d frames / %dx%d / %s / %s" % [
		action,
		int(action_info.get("frame_count", 0)),
		int(frame_size.get("width", 0)),
		int(frame_size.get("height", 0)),
		"loop" if bool(runtime.get("loop", true)) else "once",
		"layered body+weapon+effect" if action_is_layered else "composited",
	]
	action_meta.text = "fps=%s origin=%s collision=%s" % [
		str(runtime.get("fps", "")),
		str(runtime.get("origin", {})),
		str(runtime.get("collision_box", {})),
	]
	if not bool(validation.get("production_ready", false)):
		action_meta.text += " quality=%s %s" % [
			quality_text,
			str(action_visual.get("findings", [])),
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
			if _active_sprite_is_playing():
				_pause_active_sprites()
			else:
				_play_active_sprites()
		elif key.keycode == KEY_R:
			_play_action(current_action)
		elif key.keycode == KEY_Z:
			_set_playback_speed(0.5)
		elif key.keycode == KEY_X:
			_set_playback_speed(1.0)
		elif key.keycode == KEY_C:
			_set_playback_speed(2.0)


func _play_relative_action(offset: int) -> void:
	if action_order.is_empty() or current_action == "":
		return
	var index := action_order.find(current_action)
	if index < 0:
		index = 0
	index = wrapi(index + offset, 0, action_order.size())
	_play_action(action_order[index])


func _update_frame_meta() -> void:
	var active_sprite := _active_frame_sprite()
	if active_sprite == null or active_sprite.sprite_frames == null or current_action == "":
		return
	var frame_count := active_sprite.sprite_frames.get_frame_count(current_action)
	frame_meta.text = "%s frame %02d / %02d speed %.1fx %s" % [
		"playing" if _active_sprite_is_playing() else "paused",
		active_sprite.frame + 1,
		frame_count,
		playback_speed_multiplier,
		"loop" if _active_action_loops() else "once",
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


func _arg_value(args: PackedStringArray, name: String, default_value: String) -> String:
	for index in range(args.size() - 1):
		if args[index] == name:
			return args[index + 1]
	return default_value


func _scale_sprite() -> void:
	var frame_size: Dictionary = validation.get("frame_size", {})
	var width := float(frame_size.get("width", 1))
	var height := float(frame_size.get("height", 1))
	var max_extent: float = max(width, height)
	if max_extent > 0:
		var scale_factor: float = min(1.0, 520.0 / max_extent)
		var display_scale: Vector2 = Vector2.ONE * scale_factor
		sprite.scale = display_scale
		body_sprite.scale = display_scale
		weapon_sprite.scale = display_scale
		effect_sprite.scale = display_scale


func _configure_sprite_origin(target: AnimatedSprite2D, origin: Dictionary) -> void:
	target.centered = false
	target.offset = Vector2(-float(origin.get("x", 0.0)), -float(origin.get("y", 0.0)))


func _set_layer_visibility(action_is_layered: bool) -> void:
	sprite.visible = not action_is_layered
	body_sprite.visible = action_is_layered
	weapon_sprite.visible = action_is_layered
	effect_sprite.visible = action_is_layered
	if not action_is_layered:
		for layer_sprite in layer_sprites.values():
			layer_sprite.stop()
	else:
		sprite.stop()


func _has_layered_action(action: String) -> bool:
	if body_sprite.sprite_frames == null:
		return false
	return body_sprite.sprite_frames.has_animation(action)


func _active_frame_sprite() -> AnimatedSprite2D:
	if _has_layered_action(current_action):
		return body_sprite
	return sprite


func _active_sprite_is_playing() -> bool:
	var active_sprite := _active_frame_sprite()
	return active_sprite != null and active_sprite.is_playing()


func _active_action_loops() -> bool:
	var actions: Dictionary = manifest.get("actions", {})
	var action_info: Dictionary = actions.get(current_action, {})
	var runtime: Dictionary = action_info.get("runtime", {})
	return bool(runtime.get("loop", true))


func _pause_active_sprites() -> void:
	if _has_layered_action(current_action):
		for layer_sprite in layer_sprites.values():
			layer_sprite.pause()
	else:
		sprite.pause()


func _play_active_sprites() -> void:
	if _has_layered_action(current_action):
		for layer_sprite in layer_sprites.values():
			layer_sprite.play(current_action)
	else:
		sprite.play(current_action)
	_apply_playback_speed()


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
