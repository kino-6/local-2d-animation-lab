import importlib.util
import sys
from pathlib import Path


def test_inventory_control_models_classifies_sidecar_candidates(tmp_path: Path) -> None:
    module = _load_module()
    controlnet_root = tmp_path / "controlnet"
    sdxl = controlnet_root / "SDXL"
    sdxl.mkdir(parents=True)
    (sdxl / "OpenPoseXL2.safetensors").write_bytes(b"pose")
    (sdxl / "t2i-adapter_diffusers_xl_lineart.safetensors").write_bytes(b"lineart")

    report = module.inventory_control_models(controlnet_root)

    assert report["model_count"] == 2
    assert "lineart" in report["sidecar_tags_present"]
    lineart = next(item for item in report["candidate_status"] if item["key"] == "t2i_lineart_sdxl")
    assert lineart["present"] is True


def test_download_candidate_skips_existing_file(tmp_path: Path) -> None:
    module = _load_module()
    candidate = module.CANDIDATES["t2i_lineart_sdxl"]
    target = tmp_path / "SDXL" / candidate.filename
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing")

    report = module.download_candidate(candidate, tmp_path, subdir="SDXL")

    assert report["status"] == "already_present"
    assert report["bytes"] == len(b"existing")
    assert report["target"].endswith(candidate.filename)


def _load_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "manage_sidecar_control_models.py"
    spec = importlib.util.spec_from_file_location("manage_sidecar_control_models", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
