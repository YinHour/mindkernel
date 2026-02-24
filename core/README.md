# Core Modules

本目录存放**验证通过后的核心功能程序**（可被 tools/ 与后续服务层复用）。

目录治理规则见：`core/CONVENTIONS.md`。

## 当前模块

- `reflect_gate_v0_1.py`
  - Agent-first 风险分流核心逻辑
  - 输入：reflect proposals（JSON/JSONL）
  - 输出：machine-readable 决策（auto_apply / sample_review / mandatory_review）
  - 策略：low 自动、medium 抽检、high 必审 + hard rules

- `session_memory_parser_v0_1.py`
  - 会话 JSONL -> memory events 核心解析逻辑
  - 修复了 `tool_call` 事件 ID 冲突（按 tool 序号+参数哈希生成稳定 ID）

- `memory_experience_core_v0_1.py`
  - Memory/Experience 核心对象处理与审计逻辑
  - 包含 ingest、promote、Markdown front matter 解析与 DB 操作

- `persona_confirmation_queue_v0_1.py`
  - 人格冲突确认事件队列核心逻辑
  - 支持从 routed proposals 入队、待确认查询、人工决策回写、超时关闭
  - 支持 `apply_plan` 与 `apply_exec`（仅放行 auto_applied + human approved，含幂等账本）
  - `apply_exec` 写回时同步产出 DecisionTrace + AuditEvent
  - 失败路径会进入 `reflect_apply_compensations`（pending -> resolved）补偿队列

- `memory_importer_v0_1.py`
  - memory JSONL 导入核心逻辑
  - 支持 upsert/insert-only、payload_sha1 幂等 NOOP、错误隔离、导入 run 统计

> CLI 入口仍在 `tools/scheduler_v0_1.py route-proposals`、`tools/parse_session_jsonl_v0_1.py`、`tools/memory_experience_v0_1.py`、`tools/persona_confirmation_queue_v0_1.py`、`tools/import_memory_objects_v0_1.py`，内部已调用本目录核心模块。
