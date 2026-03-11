# MindKernel TODO

_Last updated: 2026-03-10 09:00 (Asia/Shanghai)_

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

- [x] 评估向量检索作为 FTS 的补充（当前结论：`NO_GO_KEEP_FTS`，达到规模阈值后再启动 pilot）
- [x] 形成 weekly governance report（质量指标、回滚率、升级率、学习收益）

## 今日巡检（2026-02-26）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：自昨日以来新增 1 个提交（`f8e823d`，v0.1.1 稳定化路线评审与计划落档）；治理实现提交（`c3c16c6`）已在主线。
- [x] P0 任务保持全部完成且无回退；`v0.1.0-usable` 发布基线稳定。
- [x] 已完成复盘与稳定化计划落档，`docs/06-execution/v0.1.1-stabilization-plan.md` 作为后续执行主参考。
- [x] 风险画像未恶化：当前主要风险集中在 CI 主 workflow 覆盖不足、lease 长任务续约缺口、外部 LLM 依赖波动。
- [x] R1 已完成：新增 weekly governance report 生成脚本（JSON + Markdown）与验证脚本。
- [x] R4 已完成：主 CI workflow 已纳入 multi-worker lock / temporal worker / weekly-report 验证；workspace replay 拆分至夜间/手动 workflow。
- [x] R2 已完成：scheduler 增加 lease renew 接口（CLI + 函数）并通过 `validate_scheduler_lease_renew_v0_1.py`。
- [x] R3 已完成：temporal worker 扩展 `verify/revalidate` 并通过 `validate_temporal_verify_revalidate_v0_1.py`。
- [x] R5 已完成：新增吞吐/延迟 benchmark 脚本（`benchmark_scheduler_throughput_v0_1.py`）与验证脚本。
- [x] R6 已完成：新增向量检索就绪度评估脚本（`evaluate_vector_retrieval_readiness_v0_1.py`），当前决策 `NO_GO_KEEP_FTS`。
- [x] 已完成本轮稳定化代码推送（`main` 更新到 `ae6b9e5`）。
- [x] 已完成稳定化版本标签：`v0.1.1-stabilized`（已推送远端）。
- [x] 已新增 v0.1.1 发布手册与周报定时 workflow，进入运行期观测阶段。

## 今日巡检（2026-02-27）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：新增 3 个关键提交（`a9d097a` TODO 收口同步、`bbecca8` v0.2 daemon 执行计划、`8db6643` installer + README 安装指引）。
- [x] TODO 收口状态一致：v0.1.1 稳定化闭环仍保持完成，运行期观察主线未偏移。
- [x] v0.2 D1 前置文档已完成，当前主阻塞切换为“D1 代码骨架与 smoke 验证尚未落地”。
- [x] 风险画像小幅改善：发布/治理风险维持低位；外部依赖风险仍为中；新增“安装流程文档与脚本漂移”中低风险需纳入 CI smoke。

## 今日巡检（2026-02-28）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main`/`origin/main` 仍停留在 `8db6643`，自昨日以来无新增提交。
- [x] TODO 收口状态保持一致：v0.1.1 稳定化闭环完成状态未回退。
- [x] v0.2 主阻塞未变化：D1 代码骨架与最小 smoke（含 checkpoint/recover）仍未落地。
- [x] 风险画像总体稳定：外部依赖风险（中）持续，安装流程文档/脚本漂移风险处于中低并待 CI smoke 固化。

## 今日巡检（2026-03-01）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main`/`origin/main` 仍停留在 `8db6643`，自昨日以来无新增提交。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] v0.2 主阻塞未变化：D1 代码骨架与最小 smoke（含 checkpoint/recover）仍未落地。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-02）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main`/`origin/main` 仍停留在 `8db6643`，自昨日以来无新增提交。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] v0.2 主阻塞未变化：D1 代码骨架与最小 smoke（含 checkpoint/recover）仍未落地。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-04）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：新增 1 个提交（`a2b758a`，LLM 韧性增强 + observation 报告能力强化）。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] v0.2 运行观察：Day1 已完成，Day2 需执行 run-once + observation 报告。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-03）

- [x] 已落地 v0.2 D1：`tools/daemon/memory_observer_daemon_v0_2.py`（poll/tail、pid/lock、checkpoint/recover、graceful shutdown）。
- [x] 已新增验证脚本：`tools/validation/validate_daemon_skeleton_v0_2.py`。
- [x] 已将 D1 验证接入门禁：`tools/release/release_check_v0_1.py` 与 `.github/workflows/critical-path-validation.yml`。
- [x] 已完成 D2/D3 最小闭环：event normalize + dedupe/throttle + realtime candidate enqueue（reflect_job）。
- [x] 已新增闭环验证：`tools/validation/validate_daemon_closed_loop_v0_2.py`（events -> daemon -> scheduler -> reflect worker）。
- [x] 已完成 D5：feature flag（off/shadow/partial/on）+ 一键回退脚本 `scripts/daemon_v0_2_control.sh` + runbook。
- [x] 已完成 D6：门禁分层（quick/full）+ 夜间 daemon 回放 workflow（`governance-daemon-nightly.yml`）。
- [x] 已完成外部依赖韧性原型：LLM 熔断/重试/降级（`core/llm_resilience_v0_2.py` + `validate_llm_resilience_v0_2.py`）。
- [x] 已完成 daemon 观测报告能力：`generate_daemon_observation_report_v0_2.py` + `validate_daemon_observation_report_v0_2.py`。
- [x] 门禁更新后复核：`release_check_v0_1.py --quick` 20/20 PASS；full 24/24 PASS。
- [x] 已手动补写本日巡检记录（自动更新失败后人工确认）。
- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：已完成 v0.2 D1~D6 原型提交并推送，`main`/`origin/main` 更新到 `40d9021`。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] v0.2 D1~D6 已形成可闭环原型并完成门禁验证（当前主线切换到运行观察 + 外部依赖熔断降级设计）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-05）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：新增 1 个提交（`a2b758a`，LLM 韧性增强 + observation 报告能力强化），`main`/`origin/main` 更新到 `a2b758a`。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2/Day3：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-06）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main`/`origin/main` 仍停留在 `a2b758a`，自昨日以来无新增提交。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day4：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告。

## 今日巡检（2026-03-07）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main`/`origin/main` 仍停留在 `a2b758a`，自 3 月 5 日以来无新增提交。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day5：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-08）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main`/`origin/main` 仍停留在 `a2b758a`，自 3 月 5 日以来无新增提交。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day6：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告（**已延期 6 天**）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-09）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main`/`origin/main` 仍停留在 `a2b758a`，自 3 月 5 日以来无新增提交。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day7：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告（**已延期 7 天，进入阈值固化复盘阶段**）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。
- [x] 观察点：本地有未提交修改（realtime_memory_candidate_v0_2.py、daemon_v0_2.py、observation_report_v0_2.py），建议尽快合入或落档说明。

## 今日巡检（2026-03-10）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main`/`origin/main` 仍停留在 `a2b758a`，自 3 月 5 日以来无新增提交。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] v0.2 运行观察 Day2~Day8：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告（**已延期 8 天，进入阈值固化复盘阶段**）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。
- [x] 观察点：本地有未提交修改（realtime_memory_candidate_v0_2.py、daemon_v0_2.py、observation_report_v0_2.py、TODO.md），建议尽快合入或落档说明。

## 今日巡检（2026-03-11）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main`/`origin/main` 仍停留在 `a2b758a`，自 3 月 5 日以来无新增提交。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day9：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告（**已延期 9 天，需决策是否继续或重新规划**）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。
- [x] 观察点：本地有未提交修改（realtime_memory_candidate_v0_2.py、daemon_v0_2.py、observation_report_v0_2.py、TODO.md、checklists/），建议尽快合入或落档说明。

## 下一步（运行期）

> 参考：`docs/06-execution/release-runbook-v0.1.1-stabilized.md`

1. 连续 1 周运行 weekly governance report，沉淀趋势基线与告警阈值。
2. 按运行数据复核 `NO_GO_KEEP_FTS` 触发条件（规模/QPS/质量退化）。
3. v0.2 daemon 计划 D1~D6（已完成，进入运行观察）：
   - [x] 计划文档已落档：`docs/06-execution/v0.2-daemon-memory-observer-plan.md`
   - [x] 完成 D1 代码骨架与最小可运行 smoke（含 checkpoint/recover）
   - [x] 拆分并落地最小任务包：daemon loop / signal handling / checkpoint store / recover path
   - [x] 新增 D1 smoke 脚本并纳入 CI（至少覆盖 start -> checkpoint -> restart recover -> graceful shutdown）
   - [x] 完成 D2：事件标准化与去重节流（`core/event_normalizer_v0_2.py`）。
   - [x] 完成 D3：实时候选提炼与治理入队（`core/realtime_memory_candidate_v0_2.py`）。
   - [x] 完成 D4（原型级）：批次指标落盘与运行统计输出（processed/normalized/deduped/candidates/enqueued/throttled/skipped_hwm）。
   - [x] 完成 D5：运行策略与回退（feature flag / runbook）。
   - [x] 完成 D6：门禁分层与夜间回放策略固化。
4. 准备下一阶段（v0.2）需求梳理：外部依赖熔断/降级与长期稳定性观测（韧性原型已落地，待运行观察与阈值固化）。
5. 将 installer + README 安装指引纳入发布手册与 CI smoke 安装验证（避免文档/脚本漂移）。


## v0.2 运行观察（7天）

- [x] Day1（2026-03-03）：已启动观察基线（shadow + run-once）。
  - state_db: `data/daemon/memory_observer_v0_2.sqlite`
  - observation: `reports/daemon/observation_20260303_034814.md`
  - 指标快照：batches=2, processed=955, candidates=52, errors=0
- [ ] Day2：增量 run-once + observation 报告
- [ ] Day3：增量 run-once + observation 报告
- [ ] Day4：增量 run-once + observation 报告
- [ ] Day5：增量 run-once + observation 报告
- [ ] Day6：增量 run-once + observation 报告
- [ ] Day7：增量 run-once + observation 报告 + 阈值固化复盘

## 风险追踪

- **发布风险（低）**：v0.1.1 稳定化已闭环并推送远端，当前以运行期观测风险为主。
- **并发治理风险（低）**：lease 锁 + 过期回收 + renew/heartbeat 已接入，剩余风险主要是长时间运行稳定性观察周期不足。
- **CI 覆盖风险（低）**：新增治理验证已并入主 workflow；workspace replay 已按时长分层到夜间/手动 workflow。
- **数据风险（中-低）**：workspace 回放与恢复路径已覆盖，且已有吞吐/lag 基线；剩余风险在真实生产负载波动。
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

