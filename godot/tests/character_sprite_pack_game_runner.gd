extends SceneTree

const CharacterSpritePackPlayer = preload("res://scripts/character_sprite_pack_player.gd")


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var manifest_path := _arg_value(args, "--manifest", "")
	if manifest_path == "":
		_fail("missing --manifest <path>")
		return

	var player := CharacterBody2D.new()
	player.set_script(CharacterSpritePackPlayer)
	var sprite := AnimatedSprite2D.new()
	sprite.name = "Sprite"
	player.add_child(sprite)
	var collision := CollisionShape2D.new()
	collision.name = "CollisionShape2D"
	player.add_child(collision)
	get_root().add_child(player)

	await process_frame
	var validation: Dictionary = player.load_pack(manifest_path)
	if not validation.get("ok", false):
		_fail(str(validation.get("error", "pack load failed")))
		return

	var observed := []
	_drive(player, observed, 0.0, false, false, false, false)
	_drive(player, observed, 1.0, false, false, false, false)
	_drive(player, observed, 1.0, false, true, false, false)
	_drive(player, observed, 0.0, true, false, false, false)
	player.sprite.stop()
	_drive(player, observed, 0.0, false, false, true, false)
	player.sprite.stop()
	_drive(player, observed, 0.0, false, false, false, true)

	var required := ["idle", "walk", "run", "jump", "attack_sword_light", "hurt"]
	for action in required:
		if not observed.has(action):
			_fail("missing gameplay action transition: %s observed=%s" % [action, str(observed)])
			return

	var summary: Dictionary = player.gameplay_summary()
	summary["ok"] = true
	summary["observed_actions"] = observed
	summary["action_count"] = validation.get("action_count", 0)
	print(JSON.stringify(summary))
	quit(0)


func _drive(
	player: CharacterBody2D,
	observed: Array,
	move_axis: float,
	jump_pressed: bool,
	run_pressed: bool,
	attack_pressed: bool,
	hurt_pressed: bool
) -> void:
	player.apply_gameplay_input(move_axis, jump_pressed, run_pressed, attack_pressed, hurt_pressed, 1.0 / 60.0, true)
	if not observed.has(player.current_action):
		observed.append(player.current_action)


func _arg_value(args: PackedStringArray, name: String, default_value: String) -> String:
	for index in range(args.size() - 1):
		if args[index] == name:
			return args[index + 1]
	return default_value


func _fail(message: String) -> void:
	var result := {"ok": false, "error": message}
	printerr(JSON.stringify(result))
	quit(1)

