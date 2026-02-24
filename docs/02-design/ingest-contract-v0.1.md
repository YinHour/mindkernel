# Ingest Contract v0.1（S4 冻结）

> 适用范围：`memory JSONL -> objects` 导入链路（S4/S5/S6）。

## 1. 输入契约

### 1.1 输入文件
- 格式：JSONL（每行一个 JSON object）
- 编码：UTF-8
- 每行对象必须满足 `schemas/memory.schema.json`

### 1.2 最低必填字段
- `id`
- `kind` (`event|fact`)
- `content`
- `source.source_type`
- `source.source_ref`
- `evidence_refs`（>=1）
- `confidence`
- `risk_tier`
- `impact_tier`
- `status`
- `created_at`
- `review_due_at`
- `next_action_at`

## 2. 导入模式

### 2.1 `upsert`（默认）
- 目标不存在：插入
- 目标存在且 payload 相同（sha1 相同）：NOOP（`skipped_noop`）
- 目标存在且 payload 不同：更新（`updated`）

### 2.2 `insert-only`
- 目标不存在：插入
- 目标存在：报错并进入失败清单（不覆盖）

## 3. 幂等与重放

### 3.1 幂等判定
- 按 `id` 定位对象
- `payload_sha1` 相同 => NOOP

### 3.2 回放行为
- 同一 JSONL 重复导入（`upsert`）应收敛为：
  - `inserted=0`
  - `updated=0`
  - `skipped_noop=total`

## 4. 错误隔离

- 单行错误不阻断全量导入（`strict=false`）
- 每条错误记录：`line / id / error`
- 错误行不得污染 `memory_items` 主表

## 5. 审计要求

导入成功的 insert/update 必须写 `audit_events`：
- `event_type=state_transition`
- `object_type=memory`
- `reason`: `memory imported (insert|upsert update)`
- `correlation_id`: import run id

## 6. 运行产物

- 表：`memory_items`
- 表：`memory_import_runs`
- 表：`audit_events`

## 7. CLI 约定

```bash
python3 tools/import_memory_objects_v0_1.py \
  --db data/mindkernel_v0_1.sqlite \
  --input /path/to/memory.jsonl \
  --mode upsert \
  --out reports/memory_import_report.json
```

## 8. 验证与门禁

- 回放验证：`tools/validate_memory_import_v0_1.py`
- 单测：`test/test_validate_memory_import_v0_1.py`
- CI：`critical-path-validation.yml` 应执行回放验证脚本
