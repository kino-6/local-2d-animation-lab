extends SceneTree

const AssetManifest = preload("res://scripts/asset_manifest.gd")


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var manifest_path := _arg_value(args, "--manifest", "")
	if manifest_path == "":
		_fail("missing --manifest <path>")
		return

	var manifest := AssetManifest.load_manifest(manifest_path)
	var validation := AssetManifest.validate_single_sprite_asset(manifest)
	if not validation.get("ok", false):
		_fail(str(validation.get("error", "single sprite validation failed")))
		return

	var frames := AssetManifest.build_single_sprite_frames(manifest)
	var animation := str(validation.get("animation", "asset"))
	if animation == "":
		animation = "asset"
	if not frames.has_animation(animation):
		_fail("missing SpriteFrames animation: %s" % animation)
		return
	if frames.get_frame_count(animation) != int(validation["frame_count"]):
		_fail("SpriteFrames count mismatch")
		return

	var player := AnimatedSprite2D.new()
	player.sprite_frames = frames
	player.animation = animation
	get_root().add_child(player)
	player.play()

	await process_frame
	await create_timer(0.25).timeout

	if not player.is_playing():
		_fail("AnimatedSprite2D did not start playback")
		return

	var result := {
		"ok": true,
		"manifest": ProjectSettings.globalize_path(manifest_path),
		"frame_count": validation["frame_count"],
		"frame_size": validation["frame_size"],
		"asset_name": validation["asset_name"],
		"animation": validation["animation"],
		"status": validation["status"],
		"current_frame": player.frame,
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
