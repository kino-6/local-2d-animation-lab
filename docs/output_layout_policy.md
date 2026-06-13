# Output Layout Policy

New generated artifacts must be written under one timestamp session:

```text
outputs/<YYYYMMDD_HHMMSS>/<category>/<run-label>/
```

Each run directory should include `run_profile.json` and `memo.md` next to its workflow JSON, reports, previews, frames, and packages.

Do not add new default output roots such as `outputs_*`, `review_packages`, or `source_probe_packages`. Historical folders may remain as archived evidence, but new tools and commands should use `--output-root outputs` unless intentionally writing non-generated source assets such as `pose_templates/` or `weapon_guides/`.
