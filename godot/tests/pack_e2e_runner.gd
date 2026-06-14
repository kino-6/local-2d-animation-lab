extends SceneTree

const AssetManifest = preload("res://scripts/asset_manifest.gd")


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var manifest_path := _arg_value(args, "--manifest", "")
	if manifest_path == "":
		_fail("missing --manifest <path>")
		return

	var manifest := AssetManifest.load_manifest(manifest_path)
	var validation := AssetManifest.validate_pack(manifest)
	if not validation.get("ok", false):
		_fail(str(validation.get("error", "pack validation failed")))
		return

	var frames := AssetManifest.build_pack_sprite_frames(manifest)
	var action_names := AssetManifest.pack_action_names(manifest)
	if action_names.is_empty():
		_fail("no pack actions")
		return

	var player := AnimatedSprite2D.new()
	player.sprite_frames = frames
	get_root().add_child(player)

	var action_payload := {}
	for action in action_names:
		if not frames.has_animation(action):
			_fail("missing SpriteFrames animation: %s" % action)
			return
		var expected_count := int(validation["actions"][action].get("playback_frame_count", validation["actions"][action]["frame_count"]))
		var actual_count := frames.get_frame_count(action)
		if actual_count != expected_count:
			_fail("%s SpriteFrames count mismatch: expected %d, got %d" % [action, expected_count, actual_count])
			return
		player.play(action)
		await process_frame
		if not player.is_playing():
			_fail("%s did not start playback" % action)
			return
		action_payload[action] = {
			"frame_count": actual_count,
			"loop": frames.get_animation_loop(action),
			"speed": frames.get_animation_speed(action),
		}

	var result := {
		"ok": true,
		"manifest": ProjectSettings.globalize_path(manifest_path),
		"action_count": action_names.size(),
		"actions": action_payload,
		"frame_size": validation["frame_size"],
		"production_ready": validation["production_ready"],
	}
	print(JSON.stringify(result))
	quit(0)


func _arg_value(args: PackedStringArray, name: String, default_value: String) -> String:
	for index in range(args.size() - 1):
		if args[index] == name:
			return args[index + 1]
	return default_value


func _fail(message: String) -> void:
	var result := {"ok": false, "error": message}
	printerr(JSON.stringify(result))
	quit(1)
