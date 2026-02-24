# Tools Overview

本目录存放 v0.1 原型脚本。

## 核心链路脚本

- `memory_experience_v0_1.py`
  - Memory ingest + Memory→Experience
  - 核心逻辑已抽取到 `core/memory_experience_core_v0_1.py`
- `experience_cognition_v0_1.py`
  - Experience→Cognition + Persona Gate（最小实现）
- `cognition_decision_v0_1.py`
  - Cognition→DecisionTrace
- `full_path_v0_1.py`
  - M→E→C→D 一键全链路

## 基础能力脚本

- `scheduler_v0_1.py`
  - 到期调度原型（enqueue/pull/ack/fail/stats）
  - Agent-first 提案闸门路由（`route-proposals`，支持 low/medium/high 分流与 medium 抽检）
  - `route-proposals` 的核心逻辑已抽取到 `core/reflect_gate_v0_1.py`
- `validate_scenarios_v0_1.py`
  - fixtures + 业务断言校验
- `system_smoke_report_v0_1.py`
  - 一键执行烟测并输出报告
- `schema_runtime.py`
  - 轻量运行时 schema 校验模块
- `memory_index_v0_1.py`
  - 离线记忆索引草案（retain/recall/reflect，含 opinion 置信度演化）
- `validate_memory_index_v0_1.py`
  - 记忆索引演化与写回验证脚本
- `validate_opinion_conflicts_v0_1.py`
  - opinion 冲突聚类与极性判定验证脚本（冲突簇 + mandatory_review 建议）
- `validate_recall_quality_v0_1.py`
  - recall 质量回放基线（accuracy/recall/noise + M→E 输入质量）
- `migrate_memory_md_to_objects_v0_1.py`
  - `memory.md` 到 memory objects 的安全迁移 dry-run（行级 source_ref + 敏感项分级）
- `import_memory_objects_v0_1.py`
  - `memory JSONL -> objects` 导入器（upsert/insert-only，行级错误隔离，幂等 NOOP）
- `parse_session_jsonl_v0_1.py`
  - 解析 OpenClaw session JSONL，产出 memory-event 候选（directive/request/milestone/discovery，可选 tool_call）
  - 核心解析逻辑已抽取到 `core/session_memory_parser_v0_1.py`
- `persona_confirmation_queue_v0_1.py`
  - 人格冲突确认队列 CLI（enqueue/list/ask/resolve/timeout-scan/apply-plan/apply-exec）
  - `apply-exec` 写回时会同步产出 DecisionTrace + AuditEvent，并写入幂等账本
  - 核心逻辑在 `core/persona_confirmation_queue_v0_1.py`
- `llm_memory_processor_v0_1.py`
  - 核心对象 `LLMMemoryProcessor`：调用外部 LLM（OpenAI-compatible）做记忆抽取，输出 memory.schema 兼容对象
- `validate_ingest_tools_v0_1.py`
  - 校验迁移与会话解析链路（`memory.md` dry-run + session->memory JSONL + schema 校验）
- `validate_memory_import_v0_1.py`
  - 校验 memory JSONL 导入器（幂等回放 + 错误隔离 + 导入统计）
- `validate_llm_memory_processor_v0_1.py`
  - 校验 LLM 记忆处理核心对象（mock backend + schema 校验）

## 备注

- 所有脚本默认数据库路径：`data/mindkernel_v0_1.sqlite`
- 运行中生成的 `.sqlite` 与 `reports/` 内容默认不入库。
