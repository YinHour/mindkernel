# MindKernel TODO

_Last updated: 2026-02-25 16:03 (Asia/Shanghai)_

## P0（近期必须推进）

- [x] 将 memory index 从草案升级为可用模块（**增量 reindex**、错误恢复、去重策略）
- [x] 为 memory-index 增加 CI 校验步骤（并入现有 `critical-path-validation` workflow）
- [x] 增补 RTM：把 retain/recall/reflect + opinion evolution 的实现映射进 MR/CR/FR/NFR
- [x] 设计并实现 `memory.md` -> memory objects 的安全迁移脚本（行级 source_ref + 敏感项分级）
- [x] 建立外部 LLM 记忆处理核心对象 `LLMMemoryProcessor`（含 mock 验证与 CI 门禁）

## P1（稳定性与治理）

- [x] 将 reflect 作业接入 scheduler（建议式写回，默认 dry-run）
  - [x] 已接入 Agent-first 闸门路由原型：`scheduler_v0_1.py route-proposals`（low 自动、medium 抽检、high 必审）
  - [x] 已将验证通过的闸门核心逻辑下沉到 `core/reflect_gate_v0_1.py`
  - [x] 已将 session->memory 解析核心逻辑下沉到 `core/session_memory_parser_v0_1.py`（修复 tool_call 事件 ID 冲突）
  - [x] 已将 Memory->Experience 核心逻辑下沉到 `core/memory_experience_core_v0_1.py`（tools 保留 CLI 壳）
  - [x] 已建立 `test/` 目录并落地关键回归用例（reflect gate / session parser / memory->experience）
  - [x] 已新增人格冲突确认事件队列核心模块：`core/persona_confirmation_queue_v0_1.py`（含 enqueue/list/ask/resolve/timeout）
  - [x] 已接入 reflect apply 计划生成：仅放行 `auto_applied + human approved`，其余进入 blocked 队列
  - [x] 已接入 reflect apply 执行：`apply-exec` 按计划写回并落幂等账本（重复执行去重）
  - [x] `apply-exec` 已联动输出 DecisionTrace + AuditEvent（每条写回可追溯）
  - [x] 已接入 reflect scheduler worker loop（`reflect_scheduler_worker_v0_1.py`，默认 dry-run）
  - [x] 已补 C4 失败补偿队列（`reflect_apply_compensations` + `compensations/resolve-compensation`）
- [x] 建立 opinion 冲突聚类与更稳健的极性判定（`opinion_conflict_groups` + `validate_opinion_conflicts_v0_1.py`）
- [x] 增加回放测试：验证 recall fact-pack 对 M→E 输入质量的影响（`validate_recall_quality_v0_1.py`）
- [x] 冻结数据入口契约（ingest contract，S4：`docs/02-design/ingest-contract-v0.1.md`）
- [x] 补 `memory JSONL -> objects` 导入器与幂等回放验证（S5/S6：`import_memory_objects_v0_1.py` + `validate_memory_import_v0_1.py`）
- [x] 增加发布前总检脚本雏形（S10：`release_check_v0_1.py`，输出 release check JSON/Markdown）

## P2（后续演进）

- [ ] 评估向量检索作为 FTS 的补充（仅在规模达到阈值后）
- [ ] 形成 weekly governance report（质量指标、回滚率、升级率、学习收益）

## 今日巡检（2026-02-25）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），暂无新增讨论条目。
- [x] 核对代码基线增量：存在 2 个新提交（`019d899` 校验脚本归档到 `tools/validation`；`c530efb` 工具分层重构并修复引用），主线推进恢复。
- [x] P0 保持全部完成且无回退；已完成正式版本收口（本地 tag：`v0.1.0-usable`）。
- [x] 已完成 `v0.1.0-usable` 全量发布前总检（含新增治理门禁）：`14/14 PASS`，结果已冻结到 `reports/release_check_v0_1.json` 与 `reports/release_check_v0_1.md`。
- [x] 已完成真实 workspace 回放验证（`validate_scheduler_workspace_replay_v0_1.py`）：覆盖失败恢复路径，产物可审计。
- [x] 已完成多 worker 租约/锁机制（`scheduler_v0_1.py` 新增 `lease_token/lease_expires_at` + 过期回收 + action filter）并通过多 worker 验证。
- [x] 已完成遗忘执行层 worker 化（`temporal_governance_worker_v0_1.py`：decay/archive/reinstate-check），并通过状态迁移验证。
- [x] 已完成远端发布动作：`main` 与 `v0.1.0-usable` tag 已推送至 origin。
- [x] 项目复盘复核完成：`release_check_v0_1.py --release-target v0.1.1-review-full` 结果 `14/14 PASS`。

## 下一步（建议按顺序执行）

> 参考：`docs/06-execution/v0.1.1-stabilization-plan.md`（R1~R6）

1. R1：落地 weekly governance report（首版 JSON + Markdown，形成周维度趋势基线）。
2. R4：CI 门禁对齐（把 multi-worker lock / temporal worker 验证纳入主 workflow；workspace replay 走 nightly/手动）。
3. R2：为 lease 增加续约（renew）与长任务保护，降低误回收风险。
4. R3：扩展 temporal worker 支持 `verify/revalidate`，补齐治理执行器覆盖面。
5. R5 + R6：建立吞吐/延迟 benchmark，并完成向量检索补充评估（给出 go/no-go 结论）。

## 风险追踪

- **发布风险（低）**：`main` 与 `v0.1.0-usable` 已推送远端，当前以稳定化治理风险为主。
- **并发治理风险（中-低）**：已落地 lease 锁与过期回收；长任务 lease 续约（heartbeat）尚未接入。
- **CI 覆盖风险（中）**：新增治理验证已在 release_check 中，但尚未全部进入主 workflow。
- **数据风险（中-低）**：workspace 回放与恢复路径已覆盖；剩余风险在真实规模下的持续吞吐与抖动表现。
- **外部依赖风险（中）**：LLM 线上调用受 API 可用性/成本影响，尚未接入熔断与降级策略。

MindKernel 记忆治理验收清单 v1（20 条）

### A. 可观测性与失败治理（1-4）

- A1. 禁止静默失败：所有异常必须有错误事件（含 error_code）
- A2. 回退可见：QMD→SQLite、模型降级等必须显式记录
- A3. 关键链路有耗时/成功率指标（retain/recall/reflect）
- A4. 每次任务有 trace_id，可串联日志、决策、写回结果

### B. Reflect 调度与人审闸门（5-8）【P1-1 核心】

- B1. scheduler 可触发 reflect dry-run（定时/手动）
- B2. dry-run 仅产 proposal，不直接写回
- B3. 有 approve/reject 流程（支持 partial approve）
- B4. 审批动作写入 AuditEvent + DecisionTrace

### C. 写回安全与幂等（9-12）

- C1. proposal 有幂等键（job_id + proposal_id + target_id）
- C2. 重复 apply 不产生重复写入/副作用
- C3. 冲突写回默认“挂起待审”，不自动覆盖
- C4. 支持回滚或补偿记录（至少可审计重放）

### D. Recall 质量与回归基线（13-16）【P1-2 核心】

- D1. 固化回放样本集（覆盖实体/时间/冲突/多跳）
- D2. 固化指标（Hit@K、MRR、证据覆盖率）
- D3. 有一键回归脚本，输出与基线差异报告
- D4. 发生退化时可阻断合入或触发告警

### E. 结构化记忆演化（17-20）【P1-3/P1-4 核心】

- E1. opinion 冲突可聚类并给极性判定 + 证据
- E2. JSONL→objects 导入器支持 schema 校验
- E3. 导入支持 replay（全量/窗口）并验证幂等一致性
- E4. User Memory 与 Agent Memory 边界清晰（字段/权限/用途）

────────────────────────────────────────────────────────────────────────────────

通过标准（建议）

- MVP 通过线： 至少完成 B1-B4 + C1-C2 + D1-D3（9 项）
- 本周通过线： 20 项完成 ≥ 14 项，且无 A 类阻断问题

