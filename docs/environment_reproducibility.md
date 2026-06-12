# Environment Reproducibility

Generated animation quality depends on the local model set, ComfyUI nodes, and exact checkpoint files. Treat PDCA results as valid only for the recorded environment unless a new snapshot proves the same model/node assumptions.

## Snapshot Command

Run this before major generation batches, after installing or replacing models, and before archiving a result as current best:

```bash
uv run python scripts/snapshot_local_environment.py \
  --comfy-url http://127.0.0.1:8188 \
  --comfy-root C:/LocalWork/StabilityMatrix/Data/Packages/ComfyUI
```

The script writes:

- `environment_snapshot.json`
- `environment_snapshot_summary.md`

under `outputs_environment_snapshot/`.

Latest local smoke snapshot:

- `outputs_environment_snapshot/environment_snapshot_20260612_230715/environment_snapshot_summary.md`

## What Is Recorded

- Git branch, commit, and dirty status
- Python/platform information
- ComfyUI `/object_info` availability, important node presence, and model choices
- Local model file inventory for checkpoints, ControlNet, diffusion models, UNets, VAE, CLIP, LoRA, and background-removal models
- ComfyUI `extra_model_paths.yaml` entries, including StabilityMatrix shared model directories such as `Data/Models/StableDiffusion`
- SHA256 for important models such as `novaOrangeXL_v120`, `OpenPoseXL2`, Wan i2v/Fun/VACE models, SDPose, BiRefNet, and SDXL VAE

## Policy

- Do not compare quality conclusions across model changes without recording a new snapshot.
- Do not switch the default still-image checkpoint away from `novaOrangeXL_v120.safetensors` without a documented checkpoint comparison and matching environment snapshot.
- For large exploratory cleanup, generated outputs may be deleted after the durable report is written, but the environment snapshot should remain referenced by the report.
- If a model is too large to hash under the configured limit, record its name, size, and mtime, then rerun with a larger `--hash-max-mb` if exact reproducibility matters.
- Before calling a result "current best", rerun the snapshot with a high enough `--hash-max-mb` to hash the exact model files used by that result, or explicitly record why size/mtime is the accepted fingerprint.
