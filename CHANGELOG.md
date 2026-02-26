# Changelog

## v0.1.1-stabilized

_Date: 2026-02-26 (Asia/Shanghai)_

### Release gate status
- `v0.1.1-r2-r6` quick gate：**16/16 PASS**。
- `v0.1.1-r2-r6-full` full gate：**19/19 PASS**。
- 证据文件：
  - `reports/release_check_v0_1.json`
  - `reports/release_check_v0_1.md`

### Key additions in v0.1.1-stabilized
- R2（lease renew）：
  - `scheduler_v0_1.py` 新增 `renew_lease` + `renew-lease` CLI。
  - reflect/temporal worker 接入 `--lease-renew-sec` heartbeat 续租能力。
  - 验证：`validate_scheduler_lease_renew_v0_1.py`。
- R3（temporal 扩展）：
  - `temporal_governance_worker_v0_1.py` 扩展动作至 `verify/revalidate/decay/archive/reinstate-check`。
  - 验证：`validate_temporal_verify_revalidate_v0_1.py`。
- R5（吞吐基线）：
  - 新增 `benchmark_scheduler_throughput_v0_1.py` + `validate_scheduler_benchmark_v0_1.py`。
  - 首版基线：throughput `160215.847 jobs/min`、lag p95 `0.483s`、retry `0.0%`（synthetic profile）。
- R6（向量检索评估）：
  - 新增 `evaluate_vector_retrieval_readiness_v0_1.py` + `validate_vector_readiness_v0_1.py`。
  - 当前结论：`NO_GO_KEEP_FTS`（规模/流量未达触发阈值）。
- CI 门禁更新：
  - 主 workflow 追加 R2/R3/R5/R6 验证。
  - `critical-path-validation` 超时窗口提升到 20 分钟。

### Compatibility / rollback
- 兼容性：v0.1.1 以治理能力增强与验证覆盖扩展为主，无 schema 破坏性变更。
- 回滚建议：
  1. 优先回退到 `v0.1.0-usable`；
  2. 重新执行 `release_check_v0_1.py` 验证基线；
  3. 逐项恢复 R2~R6 能力，定位风险来源。

## v0.1.0-usable（release prep）

_Date: 2026-02-25 (Asia/Shanghai)_

### Release gate status
- `v0.1.0-usable` 已完成全量发布前总检：**14/14 PASS**。
- 证据文件：
  - `reports/release_check_v0_1.json`
  - `reports/release_check_v0_1.md`

### Key additions in v0.1.0-usable
- Reflect scheduler worker loop（`tools/scheduler/reflect_scheduler_worker_v0_1.py`）与回归验证（`tools/validation/validate_scheduler_worker_v0_1.py`）。
- Scheduler 多 worker 租约/锁机制（`lease_token` / `lease_expires_at` + 过期回收 + action filter）。
- Temporal governance worker（`tools/scheduler/temporal_governance_worker_v0_1.py`）：支持 `decay/archive/reinstate-check` 执行与审计落账。
- 新增治理验证：`validate_scheduler_multi_worker_lock_v0_1.py`、`validate_temporal_governance_worker_v0_1.py`、`validate_scheduler_workspace_replay_v0_1.py`（真实 workspace 回放 + 恢复路径）。
- Opinion conflict clustering + polarity 增强（`memory_index_v0_1.py`）。
- Recall 质量基线回放验证（`tools/validation/validate_recall_quality_v0_1.py`）。
- Memory JSONL 导入器（`tools/memory/import_memory_objects_v0_1.py`、`core/memory_importer_v0_1.py`）与幂等回放验证。
- Apply compensation 失败补偿链路（`reflect_apply_compensations` + 管理命令）。
- 发布前总检聚合器（`tools/release/release_check_v0_1.py`）与发布手册。

### RC delta（rc1 → rc3）
- `rc1 -> rc2`
  - `52e8eca` docs: refresh quickstart path and expand naming origin note
  - `6e2b1c8` fix: stabilize scheduler worker validation timing
  - `aef0e5a` docs: finalize daily plan and mark S10/S11 rc1 completed
- `rc2 -> rc3`
  - `c530efb` refactor: layer tools into pipeline/memory/scheduler/release and fix references
  - `019d899` refactor: organize validation scripts under `tools/validation`

### Compatibility / rollback
- 兼容性：本次以工具分层与验证路径稳定化为主，无 schema 破坏性变更。
- 回滚建议：若正式发布后发现回归，优先回退到 `v0.1.0-usable-rc3` 或 `v0.1.0-usable-rc2`，并重新执行 `release_check_v0_1.py` 确认基线。