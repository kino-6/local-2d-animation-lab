class_name AssetManifest
extends RefCounted


static func load_manifest(manifest_path: String) -> Dictionary:
	var resolved_manifest := ProjectSettings.globalize_path(manifest_path)
	if not FileAccess.file_exists(resolved_manifest):
		resolved_manifest = manifest_path
	if not FileAccess.file_exists(resolved_manifest) and not manifest_path.is_absolute_path():
		var repo_relative := ProjectSettings.globalize_path("res://").get_base_dir().path_join(manifest_path)
		if FileAccess.file_exists(repo_relative):
			resolved_manifest = repo_relative
	if not FileAccess.file_exists(resolved_manifest) and not manifest_path.is_absolute_path():
		var parent_relative := ProjectSettings.globalize_path("res://../" + manifest_path)
		if FileAccess.file_exists(parent_relative):
			resolved_manifest = parent_relative
	if not FileAccess.file_exists(resolved_manifest):
		return {"ok": false, "error": "manifest not found: %s" % manifest_path}

	var file := FileAccess.open(resolved_manifest, FileAccess.READ)
	if file == null:
		return {"ok": false, "error": "cannot open manifest: %s" % resolved_manifest}

	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return {"ok": false, "error": "manifest is not a JSON object: %s" % resolved_manifest}

	parsed["_manifest_path"] = resolved_manifest
	parsed["_manifest_dir"] = resolved_manifest.get_base_dir()
	parsed["_repo_root"] = _find_repo_root(resolved_manifest.get_base_dir())
	parsed["ok"] = true
	return parsed


static func frame_paths(manifest: Dictionary, prefer_composited := true) -> PackedStringArray:
	var outputs: Dictionary = manifest.get("outputs", {})
	var paths: Array = []
	if prefer_composited:
		paths = outputs.get("composited_frame_paths", [])
	if paths.is_empty():
		paths = outputs.get("frame_paths", [])

	var resolved := PackedStringArray()
	for path in paths:
		resolved.append(resolve_asset_path(str(path), manifest))
	return resolved


static func validate(manifest: Dictionary, prefer_composited := true) -> Dictionary:
	if not manifest.get("ok", false):
		return {"ok": false, "error": manifest.get("error", "manifest load failed")}

	var spec: Dictionary = manifest.get("spec", {})
	var expected_count := int(spec.get("frame_count", 0))
	var paths := frame_paths(manifest, prefer_composited)
	if expected_count <= 0:
		return {"ok": false, "error": "spec.frame_count must be positive"}
	if paths.size() != expected_count:
		return {
			"ok": false,
			"error": "frame count mismatch: expected %d, got %d" % [expected_count, paths.size()],
		}

	var first_size := Vector2i.ZERO
	for index in range(paths.size()):
		var path := paths[index]
		if not FileAccess.file_exists(path):
			return {"ok": false, "error": "frame missing: %s" % path}
		var image := Image.new()
		var error := image.load(path)
		if error != OK:
			return {"ok": false, "error": "frame load failed: %s error=%d" % [path, error]}
		var size := image.get_size()
		if size.x <= 0 or size.y <= 0:
			return {"ok": false, "error": "invalid frame size: %s" % path}
		if index == 0:
			first_size = size
		elif size != first_size:
			return {
				"ok": false,
				"error": "frame size mismatch at %d: expected %s, got %s" % [index, first_size, size],
			}

	return {
		"ok": true,
		"frame_count": paths.size(),
		"frame_size": {"width": first_size.x, "height": first_size.y},
		"action": spec.get("action", ""),
		"character_id": spec.get("character_id", ""),
		"using_composited": prefer_composited and not manifest.get("outputs", {}).get("composited_frame_paths", []).is_empty(),
	}


static func build_sprite_frames(manifest: Dictionary, fps := 8.0, prefer_composited := true) -> SpriteFrames:
	var sprite_frames := SpriteFrames.new()
	sprite_frames.remove_animation("default")
	sprite_frames.add_animation("asset")
	sprite_frames.set_animation_speed("asset", fps)
	sprite_frames.set_animation_loop("asset", bool(manifest.get("spec", {}).get("loop", true)))

	for path in frame_paths(manifest, prefer_composited):
		var image := Image.new()
		var error := image.load(path)
		if error != OK:
			push_error("Failed to load frame: %s" % path)
			continue
		sprite_frames.add_frame("asset", ImageTexture.create_from_image(image))

	return sprite_frames


static func single_sprite_frame_paths(manifest: Dictionary) -> PackedStringArray:
	var frames: Array = manifest.get("frames", [])
	var resolved := PackedStringArray()
	for entry in frames:
		var file_path := ""
		if typeof(entry) == TYPE_DICTIONARY:
			file_path = str(entry.get("file", ""))
		else:
			file_path = str(entry)
		if file_path != "":
			resolved.append(resolve_asset_path(file_path, manifest))
	return resolved


static func validate_single_sprite_asset(manifest: Dictionary) -> Dictionary:
	if not manifest.get("ok", false):
		return {"ok": false, "error": manifest.get("error", "manifest load failed")}
	if str(manifest.get("asset_kind", "")) != "2d_game_sprite":
		return {"ok": false, "error": "not a 2d_game_sprite manifest"}

	var expected_count := int(manifest.get("frame_count", 0))
	var paths := single_sprite_frame_paths(manifest)
	if expected_count <= 0:
		return {"ok": false, "error": "frame_count must be positive"}
	if paths.size() != expected_count:
		return {
			"ok": false,
			"error": "frame count mismatch: expected %d, got %d" % [expected_count, paths.size()],
		}

	var first_size := Vector2i.ZERO
	for index in range(paths.size()):
		var path := paths[index]
		if not FileAccess.file_exists(path):
			return {"ok": false, "error": "frame missing: %s" % path}
		var image := Image.new()
		var error := image.load(path)
		if error != OK:
			return {"ok": false, "error": "frame load failed: %s error=%d" % [path, error]}
		var size := image.get_size()
		if size.x <= 0 or size.y <= 0:
			return {"ok": false, "error": "invalid frame size: %s" % path}
		if index == 0:
			first_size = size
		elif size != first_size:
			return {
				"ok": false,
				"error": "frame size mismatch at %d: expected %s, got %s" % [index, first_size, size],
			}

	return {
		"ok": true,
		"asset_kind": manifest.get("asset_kind", ""),
		"asset_name": manifest.get("asset_name", ""),
		"animation": manifest.get("animation", ""),
		"status": manifest.get("status", ""),
		"frame_count": paths.size(),
		"frame_size": {"width": first_size.x, "height": first_size.y},
		"fps": float(manifest.get("fps", 8.0)),
		"pivot": manifest.get("pivot", {}),
	}


static func build_single_sprite_frames(manifest: Dictionary) -> SpriteFrames:
	var animation := str(manifest.get("animation", "asset"))
	if animation == "":
		animation = "asset"
	var sprite_frames := SpriteFrames.new()
	sprite_frames.remove_animation("default")
	sprite_frames.add_animation(animation)
	sprite_frames.set_animation_speed(animation, float(manifest.get("fps", 8.0)))
	sprite_frames.set_animation_loop(animation, true)

	for path in single_sprite_frame_paths(manifest):
		var image := Image.new()
		var error := image.load(path)
		if error != OK:
			push_error("Failed to load single sprite frame: %s" % path)
			continue
		sprite_frames.add_frame(animation, ImageTexture.create_from_image(image))

	return sprite_frames


static func pack_action_names(manifest: Dictionary) -> PackedStringArray:
	var names := PackedStringArray()
	var actions: Dictionary = manifest.get("actions", {})
	for action in actions.keys():
		names.append(str(action))
	return names


static func pack_frame_paths(manifest: Dictionary, action: String) -> PackedStringArray:
	var actions: Dictionary = manifest.get("actions", {})
	var action_info: Dictionary = actions.get(action, {})
	var paths: Array = action_info.get("frames", [])
	var resolved := PackedStringArray()
	for path in paths:
		resolved.append(resolve_asset_path(str(path), manifest))
	return resolved


static func validate_pack(manifest: Dictionary) -> Dictionary:
	if not manifest.get("ok", false):
		return {"ok": false, "error": manifest.get("error", "manifest load failed")}
	if str(manifest.get("route", "")) != "character_sprite_asset_pack":
		return {"ok": false, "error": "not a character_sprite_asset_pack manifest"}

	var actions: Dictionary = manifest.get("actions", {})
	if actions.is_empty():
		return {"ok": false, "error": "pack has no actions"}

	var visual_quality := pack_visual_quality(manifest)
	var action_results := {}
	var first_size := Vector2i.ZERO
	for action in actions.keys():
		var action_name := str(action)
		var action_info: Dictionary = actions[action]
		var expected_count := int(action_info.get("frame_count", 0))
		var paths := pack_frame_paths(manifest, action_name)
		if expected_count <= 0:
			return {"ok": false, "error": "%s.frame_count must be positive" % action_name}
		if paths.size() != expected_count:
			return {
				"ok": false,
				"error": "%s frame count mismatch: expected %d, got %d" % [action_name, expected_count, paths.size()],
			}

		var action_size := Vector2i.ZERO
		for index in range(paths.size()):
			var path := paths[index]
			if not FileAccess.file_exists(path):
				return {"ok": false, "error": "%s frame missing: %s" % [action_name, path]}
			var image := Image.new()
			var error := image.load(path)
			if error != OK:
				return {"ok": false, "error": "%s frame load failed: %s error=%d" % [action_name, path, error]}
			var size := image.get_size()
			if size.x <= 0 or size.y <= 0:
				return {"ok": false, "error": "%s invalid frame size: %s" % [action_name, path]}
			if index == 0:
				action_size = size
			elif size != action_size:
				return {
					"ok": false,
					"error": "%s frame size mismatch at %d: expected %s, got %s" % [action_name, index, action_size, size],
				}

		if first_size == Vector2i.ZERO:
			first_size = action_size
		elif action_size != first_size:
			return {
				"ok": false,
				"error": "%s action canvas mismatch: expected %s, got %s" % [action_name, first_size, action_size],
			}

		var runtime: Dictionary = action_info.get("runtime", {})
		var playback_indices: Array = runtime.get("playback_frame_indices", [])
		var playback_count := playback_indices.size()
		if playback_count == 0:
			playback_count = paths.size()
		action_results[action_name] = {
			"frame_count": paths.size(),
			"playback_frame_count": playback_count,
			"frame_size": {"width": action_size.x, "height": action_size.y},
			"fps": float(runtime.get("fps", 8.0)),
			"loop": bool(runtime.get("loop", true)),
			"origin": runtime.get("origin", {}),
			"collision_box": runtime.get("collision_box", {}),
			"visual_quality": visual_quality.get("actions", {}).get(action_name, {}),
		}

	var manifest_production_ready := bool(manifest.get("production_ready", false))
	var visual_production_ready := bool(visual_quality.get("production_ready", manifest_production_ready))
	return {
		"ok": true,
		"route": manifest.get("route", ""),
		"production_ready": manifest_production_ready and visual_production_ready,
		"action_count": actions.size(),
		"actions": action_results,
		"frame_size": {"width": first_size.x, "height": first_size.y},
		"visual_quality": visual_quality,
	}


static func pack_visual_quality(manifest: Dictionary) -> Dictionary:
	var visual_gate: Dictionary = manifest.get("visual_gate", {})
	var report_path := str(visual_gate.get("report", ""))
	if report_path == "":
		report_path = "pack_review/visual_gate_report.json"
	var resolved_path := resolve_asset_path(report_path, manifest)
	if not FileAccess.file_exists(resolved_path):
		return {
			"available": false,
			"production_ready": bool(manifest.get("production_ready", false)),
			"decision": "not_available",
			"report": report_path,
			"blocking_actions": [],
			"actions": {},
		}

	var file := FileAccess.open(resolved_path, FileAccess.READ)
	if file == null:
		return {
			"available": false,
			"production_ready": false,
			"decision": "report_open_failed",
			"report": report_path,
			"blocking_actions": [],
			"actions": {},
		}
	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return {
			"available": false,
			"production_ready": false,
			"decision": "report_parse_failed",
			"report": report_path,
			"blocking_actions": [],
			"actions": {},
		}

	var report: Dictionary = parsed
	var action_payload := {}
	var report_actions: Dictionary = report.get("actions", {})
	for action in report_actions.keys():
		var action_name := str(action)
		var entry: Dictionary = report_actions[action]
		action_payload[action_name] = {
			"decision": str(entry.get("decision", "")),
			"findings": entry.get("findings", []),
			"metrics": entry.get("metrics", {}),
		}

	return {
		"available": true,
		"production_ready": bool(report.get("production_ready", false)),
		"decision": str(report.get("decision", "")),
		"report": report_path,
		"blocking_actions": report.get("blocking_actions", []),
		"actions": action_payload,
	}


static func build_pack_sprite_frames(manifest: Dictionary) -> SpriteFrames:
	var sprite_frames := SpriteFrames.new()
	sprite_frames.remove_animation("default")
	var actions: Dictionary = manifest.get("actions", {})
	for action in actions.keys():
		var action_name := str(action)
		var action_info: Dictionary = actions[action]
		var runtime: Dictionary = action_info.get("runtime", {})
		sprite_frames.add_animation(action_name)
		sprite_frames.set_animation_speed(action_name, float(runtime.get("fps", 8.0)))
		sprite_frames.set_animation_loop(action_name, bool(runtime.get("loop", true)))

		var paths := pack_frame_paths(manifest, action_name)
		var playback_indices: Array = runtime.get("playback_frame_indices", [])
		if playback_indices.is_empty():
			for index in range(paths.size()):
				playback_indices.append(index)

		for index_value in playback_indices:
			var frame_index := int(index_value)
			if frame_index < 0 or frame_index >= paths.size():
				push_error("Invalid playback frame index %d for action %s" % [frame_index, action_name])
				continue
			var path := paths[frame_index]
			var image := Image.new()
			var error := image.load(path)
			if error != OK:
				push_error("Failed to load pack frame: %s" % path)
				continue
			sprite_frames.add_frame(action_name, ImageTexture.create_from_image(image))

	return sprite_frames


static func build_pack_layer_sprite_frames(manifest: Dictionary, layer: String) -> SpriteFrames:
	var sprite_frames := SpriteFrames.new()
	sprite_frames.remove_animation("default")
	var actions: Dictionary = manifest.get("actions", {})
	for action in actions.keys():
		var action_name := str(action)
		var action_info: Dictionary = actions[action]
		var layered_value = action_info.get("layered", {})
		if typeof(layered_value) != TYPE_DICTIONARY:
			continue
		var layered: Dictionary = layered_value
		if layered.is_empty():
			continue
		var layers: Array = layered.get("layers", [])
		if not layers.has(layer):
			continue

		var layer_manifest := load_pack_layer_manifest(manifest, action_name)
		if layer_manifest.is_empty():
			continue
		var layer_artifacts: Dictionary = layer_manifest.get("layer_artifacts", {})
		var artifact: Dictionary = layer_artifacts.get(layer, {})
		var local_paths: Array = artifact.get("frames", [])
		if local_paths.is_empty():
			continue

		var runtime: Dictionary = action_info.get("runtime", {})
		sprite_frames.add_animation(action_name)
		sprite_frames.set_animation_speed(action_name, float(runtime.get("fps", 8.0)))
		sprite_frames.set_animation_loop(action_name, bool(runtime.get("loop", true)))

		var resolved_paths := PackedStringArray()
		var layer_base := _layer_manifest_base_path(manifest, action_name, layered)
		for local_path in local_paths:
			resolved_paths.append(layer_base.path_join(str(local_path)))

		var playback_indices: Array = runtime.get("playback_frame_indices", [])
		if playback_indices.is_empty():
			for index in range(resolved_paths.size()):
				playback_indices.append(index)

		for index_value in playback_indices:
			var frame_index := int(index_value)
			if frame_index < 0 or frame_index >= resolved_paths.size():
				push_error("Invalid layer playback frame index %d for action %s layer %s" % [frame_index, action_name, layer])
				continue
			var path := resolved_paths[frame_index]
			var image := Image.new()
			var error := image.load(path)
			if error != OK:
				push_error("Failed to load pack layer frame: %s" % path)
				continue
			sprite_frames.add_frame(action_name, ImageTexture.create_from_image(image))

	return sprite_frames


static func load_pack_layer_manifest(manifest: Dictionary, action: String) -> Dictionary:
	var actions: Dictionary = manifest.get("actions", {})
	var action_info: Dictionary = actions.get(action, {})
	var layered_value = action_info.get("layered", {})
	if typeof(layered_value) != TYPE_DICTIONARY:
		return {}
	var layered: Dictionary = layered_value
	if layered.is_empty():
		return {}
	var manifest_path := str(layered.get("manifest", ""))
	if manifest_path == "":
		return {}
	var resolved_path := resolve_asset_path(manifest_path, manifest)
	if not FileAccess.file_exists(resolved_path):
		return {}
	var file := FileAccess.open(resolved_path, FileAccess.READ)
	if file == null:
		return {}
	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	return parsed


static func _layer_manifest_base_path(manifest: Dictionary, action: String, layered: Dictionary) -> String:
	var manifest_path := str(layered.get("manifest", ""))
	if manifest_path != "":
		var resolved_path := resolve_asset_path(manifest_path, manifest)
		if resolved_path != "":
			return resolved_path.get_base_dir()
	var repo_root := str(manifest.get("_repo_root", ""))
	return repo_root.path_join("outputs/adoptable/character_sprite_asset_pack/actions").path_join(action)


static func resolve_asset_path(path_text: String, manifest: Dictionary) -> String:
	if path_text.is_absolute_path():
		return path_text
	var repo_root := str(manifest.get("_repo_root", ""))
	if repo_root != "":
		var repo_candidate := repo_root.path_join(path_text)
		if FileAccess.file_exists(repo_candidate):
			return repo_candidate
	var manifest_candidate := str(manifest.get("_manifest_dir", "")).path_join(path_text)
	if FileAccess.file_exists(manifest_candidate):
		return manifest_candidate
	return ProjectSettings.globalize_path(path_text)


static func _find_repo_root(start_dir: String) -> String:
	var current := start_dir
	while current != "" and current != current.get_base_dir():
		if FileAccess.file_exists(current.path_join("pyproject.toml")) and DirAccess.dir_exists_absolute(current.path_join("src")):
			return current
		current = current.get_base_dir()
	return start_dir
