# Changelog

## v0.1.0-usable (draft)

### Added
- Reflect scheduler worker loop (`tools/reflect_scheduler_worker_v0_1.py`) and validation (`tools/validate_scheduler_worker_v0_1.py`).
- Opinion conflict clustering + polarity enhancements in `memory_index_v0_1.py`.
- Recall quality baseline replay validation (`tools/validate_recall_quality_v0_1.py`).
- Memory JSONL importer (`tools/import_memory_objects_v0_1.py`, `core/memory_importer_v0_1.py`) with idempotent replay validation.
- Apply compensation flow (`reflect_apply_compensations`) and CLI management commands.
- Release check aggregator (`tools/release_check_v0_1.py`) and release runbook.

### Changed
- `critical-path-validation` workflow now includes recall baseline, memory import replay, scheduler worker, and compensation validations.
- TODO/RTM/validation docs aligned to S4~S10 progress.

### Notes
- Current next milestone: finalize release candidate tag and package (`S11`).
