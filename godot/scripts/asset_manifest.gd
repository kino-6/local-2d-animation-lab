class_name AssetManifest
extends RefCounted


static func load_manifest(manifest_path: String) -> Dictionary:
	var resolved_manifest := ProjectSettings.globalize_path(manifest_path)
	if not FileAccess.file_exists(resolved_manifest):
		resolved_manifest = manifest_path
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
