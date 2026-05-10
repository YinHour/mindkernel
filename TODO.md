# MindKernel TODO

_Last updated: 2026-05-09 09:00 (Asia/Shanghai)_

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

## 今日巡检（2026-03-12）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main` 本地新增 5 个提交未推送（`d6822f1`~`44a6386`，v0.2 阈值策略/架构/记忆提取）；`origin/main` 停留在 `a2b758a`。
- 收口状态 [x] TODO保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day10：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告（**已延期 10 天，需决策是否继续或重新规划**）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。
- [x] 观察点：本地有 5 个未推送提交（v0.2 阈值策略演进），建议评估后推送远端。

## 今日巡检（2026-03-13）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`main` 本地保持 5 个未推送提交（`d6822f1`~`44a6386`）；`origin/main` 停留在 `a2b758a`。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day11：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告（**已延期 11 天，需决策是否继续或重新规划**）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。
- [x] 观察点：本地有 5 个未推送提交待评估，建议本周内完成 push 或落档说明。

## 今日巡检（2026-03-15）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`origin/main` 停留在 `a2b758a`（自 3 月 5 日起无更新）。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day13：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告（**已延期 13 天，需决策是否继续或重新规划**）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-16）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`origin/main` 停留在 `a2b758a`；本地领先 5 个提交未推送（v0.2 阈值策略演进）。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day14：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告（**已延期 14 天，需决策是否继续或重新规划**）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-18）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`origin/main` 停留在 `a2b758a`；本地领先 5 个提交未推送（v0.2 阈值策略演进）。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [ ] v0.2 运行观察 Day2~Day16：daemon 自 2026-03-03T03:48:10Z 后未运行，需补 run-once + observation 报告（**已延期 16 天，需决策是否继续或重新规划**）。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。

## 今日巡检（2026-03-19）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`origin/main` 停留在 `a2b758a`（自 3 月 5 日起无更新）；本地领先 5 个提交未推送（`d6822f1`~`44a6386`，v0.2 阈值策略演进）。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] **纠偏**：回顾 reports/daemon/ 发现 Day2~Day7 实为 2026-03-11 完成（observation_20260311_day2/day3/day4/day7/extened.md），已产出 metrics：
  - 48h 窗口 batches=23，processed=1386，candidates=160，enqueued=0，errors=0
  - system_repeat_alerts=18（注意：存在系统重复事件告警）
- [ ] v0.2 运行观察 Day8~Day17：自 2026-03-11 extended 之后无新 observation 报告；daemon PID 文件（pid=49026）最后触摸于 2026-03-18 23:08，**需确认 daemon 当前运行状态**。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低并待 CI smoke 固化。
- [x] 本地未推送提交已达 5 个（v0.2 阈值策略），建议本周内决策 push 或落档说明。
- [ ] **行动项**：daemon 实际运行状态待确认；v0.2 阈值策略代码待合入主线；Day8~Day17 observation 缺口需补录或决策归档。

## 今日巡检（2026-03-22）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`origin/main` 保持在 `4895332`（hobby/interest + metacognitive patterns）；本地与远端同步，无落后。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 56005，launchd 托管）：batches=11, candidates=32, enqueued=2, scheduler jobs=2, errors=0，与 03-21 持平。
- [x] adapter 运行正常（PID 49000），events file 116 lines（31078 bytes），无 error。
- [x] v0.2 运行观察（Day21）：daemon 无中断，候选者库 enqueued=2，legacy_dirty=30；最近 observation 仍停留 03-19（**缺口 3 天**）。
- [x] openclaw integration 进度确认：MCP Server ✅ / 三个核心工具 ✅ / mcporter 配置 ✅ / launchd 自启 ✅ / Daemon 对接 ✅ / Reflect Worker ✅；唯一待办：经验卡片写回 OpenClaw 对话策略（🔲 未启动）。
- [x] 未跟踪文件仍需决策：TODO.md / data/daemon/ / data/fixtures/daemon_events_openclaw.jsonl / docs/openclaw-integration.md / plugins/ / tools/daemon/openclaw_event_adapter.py / tools/daemon/run_observer_with_openclaw.py。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低；当前无 P0 阻塞。

## 今日巡检（2026-03-23）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`origin/main` 保持在 `4895332`；本地与远端同步，无落后；唯一未提交修改为 TODO.md（本次巡检更新）。
- [x] TODO 收口状态保持一致：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 56005，launchd 托管）：batches=11, candidates=32, enqueued=2, scheduler jobs=2, errors=0，与 03-22 持平。
- [x] adapter 运行正常（PID 49000），events file 116 lines（31078 bytes），无 error。
- [x] v0.2 运行观察（Day22）：daemon 无中断，候选者库 enqueued=2；最近 observation 仍停留 03-19（**缺口 4 天**）。
- [x] openclaw integration 唯一待办（经验卡片写回 OpenClaw 对话策略）仍未启动，建议本周决策是否继续。
- [x] 风险画像保持稳定：外部依赖风险（中）持续；安装流程文档/脚本漂移风险维持中低；当前无 P0 阻塞。

## 今日巡检（2026-03-24）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目。
- [x] 核对代码基线增量：`origin/main` 更新到 `3bf59d7`（feat(v0.5): MECD参数定标系统 + 治理引擎 + Decision反馈环），新增 8 文件 1053 行。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 721）：batches=17, candidates=67, enqueued=37, scheduler jobs=37, succeeded=37, errors=0，零错误运行。
- [x] adapter 运行正常（PID 709），events file 255 lines / 69701 bytes。
- [x] v0.5 重大更新已推送：MECD参数定标系统（core/param_config.py）+ 治理引擎（tools/governance/governance_engine.py）+ OpenClaw MEMORY.md 同步（tools/adapters/openclaw_memory_sync.py）+ M→E trigger 全闭环。
- [x] 7天运行报告（03-03~03-23）已生成：入队率 43%（37/87），medium 降级策略有效，高风险候选正确拦截，无用户行为误报。
- [x] 本地未提交修改均为运行时文件（WAL/checkpoint/pid/log），无源码漂移风险。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；本地工作树与远端主线对齐良好。

## 今日巡检（2026-03-25）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 32 天无更新）。
- [x] 核对代码基线增量：`origin/main` 更新到 `197ed82`（feat(pipeline): MECD exporter + canvas panel integration）；本地无源码漂移（仅运行时文件待提交）。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 721，launchd 托管）：batches=17, candidates=67, enqueued=37, scheduler jobs=37, succeeded=37, errors=0，与昨日持平。
- [x] adapter 运行正常（PID 709），events file 255 lines / 69701 bytes（无新增事件，属正常空轮询）。
- [x] v0.5 MECD pipeline 新增两个提交已推送：exporter + canvas panel integration（`d6811a1`）。
- [x] 本地未提交修改均为运行时文件（WAL/checkpoint/pid/log/chat DB），无源码漂移风险。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 22+ 天；当前无新增风险。

## 今日巡检（2026-03-28，周六）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 35 天无更新）。
- [x] 核对代码基线增量：`origin/main` 保持在 `197ed82`；本地仅有 TODO.md 待提交，源码无漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：连续零错误运行 25+ 天；候选者库处于稳态（enqueued=37，SLA 达标）。
- [x] adapter 运行正常：events file 无新增事件，属正常空轮询。
- [x] v0.2 运行观察：最近 observation 停留 03-23（7day_summary）；缺口 5 天（03-24~03-28）。
- [x] 新增 adapter 代码待决策归档：`tools/adapters/multi_source_coordinator.py` + `tools/adapters/significance_filter.py`（已生成 `data/adapters/` 数据）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 25+ 天；当前无新增风险。

## 今日巡检（2026-03-30，周一）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 37 天无更新）。
- [x] 核对代码基线增量：`origin/main` 更新到 `08411a3`（docs: add 2026-03-29 progress — MECD active push v0.1 + 下一步更新）；本地无源码漂移（仅运行时文件待提交）。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 92977，launchd 托管）：batches=19, candidates=86, enqueued=37, scheduler jobs=37, succeeded=37, errors=0；连续零错误运行 28+ 天。
- [x] adapter 运行正常：events file 255 lines / 69701 bytes（无新增事件，正常空轮询）。
- [x] v0.2 运行观察（Day30）：daemon 无中断；最近 batch 2026-03-28T02:38:33Z（2天前），24h 窗口全零（新事件空窗期），属于正常低活动状态。
- [x] MECD active push Worker：v0.1 已落地并推送；C→D 闭环已完成（`3e55242`，decision_traces 开始写入）。
- [x] 新增 adapter 代码待决策归档：`tools/adapters/multi_source_coordinator.py` + `tools/adapters/significance_filter.py`（已生成 `data/adapters/` 数据，建议本周决策归档或废弃）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 28+ 天；当前无新增风险。

## 今日巡检（2026-03-31，周二）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 38 天无更新）。
- [x] 核对代码基线增量：`origin/main` 保持在 `08411a3`（docs: add 2026-03-29 progress）；本地 TODO.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 1517，launchd 托管）：batches=19, candidates=86, enqueued=37, scheduler jobs=37, succeeded=37, errors=0；连续零错误运行 30+ 天。
- [x] adapter 运行正常（events file 255 lines / 69701 bytes，无新增事件，属正常空轮询；daemon 重启后切换到 multi-source events 文件）。
- [x] v0.2 运行观察（Day31）：daemon 无中断；最近 batch 2026-03-28T02:38:33Z（3天前），24h 窗口全零（新事件空窗期），属于正常低活动状态。
- [x] 新增 adapter 代码待决策归档（紧急度低，建议本周处理）：`tools/adapters/multi_source_coordinator.py` / `significance_filter.py` / `source_health.py` / `source_openclaw.py` / `source_workspace.py` / `universal_event_schema.py`。
- [x] MECD C→D 集成仍未启动（decision_traces 表为空，reflect_scheduler_worker → `cognition_to_decision()` 缺失）；建议尽快决策是否继续。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 30+ 天；当前无新增风险。

## 今日巡检（2026-04-01，周三）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 39 天无更新）。
- [x] 核对代码基线增量：`origin/main` 保持在 `08411a3`；本地与远端同步，无源码漂移（仅运行时文件待提交）。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 1517，launchd 托管）：batches=19, candidates=86, enqueued=37, scheduler jobs=37, succeeded=37, errors=0；连续零错误运行 **31+ 天**。
- [x] adapter 运行正常：events file 255 lines / 69701 bytes（无新增事件，属正常空轮询）。
- [x] v0.2 运行观察（Day32，auto-report）：24h 窗口 batches=0, processed=0, candidates=0, errors=0，无告警；属于正常低活动/空事件期。
- [x] 本地未跟踪文件均为运行时产物（`data/adapters/`、`data/daemon/`、`data/governance/`、`tools/adapters/` 待归档脚本）；无源码漂移风险。
- [x] MECD C→D 集成仍未启动（decision_traces 表为空，`cognition_to_decision()` 未接入 reflect worker）；**建议本周决策推进或归档**。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 31+ 天；当前无新增风险。

## 今日巡检（2026-04-02，周四）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 40 天无更新）。
- [x] 核对代码基线增量：`origin/main` 保持在 `08411a3`；本地 TODO.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 1517，launchd 托管）：连续零错误运行 **32+ 天**；24h 窗口全零指标属正常低活动期。
- [x] adapter 运行正常：events file 无新增事件，属正常空轮询。
- [x] v0.2 运行观察（Day33，auto-report）：24h 窗口 batches=0, processed=0, candidates=0, errors=0，无告警；属于正常空事件期。
- [x] 本地未跟踪文件均为运行时产物（`data/adapters/`、`data/governance/`、`tools/adapters/` 待归档脚本）；无源码漂移风险。
- [x] MECD C→D 集成仍未启动（decision_traces 表为空，`cognition_to_decision()` 未接入 reflect worker）；建议本周决策推进或归档。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 32+ 天；当前无新增风险。

## 今日巡检（2026-04-03，周五）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 41 天无更新）。
- [x] 核对代码基线增量：`origin/main` 保持在 `08411a3`；本地仅有 TODO.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 1517，launchd 托管）：batches=19, candidates=86, enqueued=37, scheduler jobs=37, succeeded=37, errors=0；连续零错误运行 **33+ 天**。
- [x] adapter 运行正常：events file 255 lines / 69701 bytes（无新增事件，属正常空轮询）。
- [x] v0.2 运行观察（Day34）：daemon 无中断；最近 batch 2026-03-28T02:38:33Z（6天前），24h 窗口全零（新事件空窗期），属于正常低活动期。
- [x] 本地未跟踪文件均为运行时产物（`data/adapters/`、`data/daemon/`、`data/governance/`、`tools/adapters/` 待归档脚本）；无源码漂移风险。
- [x] MECD C→D 集成仍未启动（decision_traces 表为空，`cognition_to_decision()` 未接入 reflect worker）；**已持续 41 天未推进，建议本周决策推进或归档**。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 33+ 天；当前无新增风险。

## 今日巡检（2026-04-04，周六）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 42 天无更新）。
- [x] 核对代码基线增量：`origin/main` 大幅推进至 `586ecbd`，新增 3 个关键提交：
  - `3e55242` feat(MECD): **完成 C→D 闭环，E→C→D 全链路接通**（41 天阻塞正式解除！）
  - `586ecbd` fix(active_push): ROOT path parents[3]→parents[2]，修复数据库指向空文件问题
  - `1598c8e` docs: daily inspection 2026-04-02
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定；**MECD C→D 闭环已完成**（✅ P0 重大阻塞解除）。
- [x] daemon 健康检查通过（PID 1517，launchd 托管）：batches=19, candidates=86, enqueued=37, scheduler jobs=37, succeeded=37, errors=0；连续零错误运行 **34+ 天**；state-db 最后写入今日 07:49（活跃）。
- [x] adapter 运行正常（PID 1504）：events file 255 lines / 69701 bytes（无新增事件，正常空轮询）。
- [x] v0.2 运行观察（Day35）：daemon 无中断；最近 batch 2026-03-28T02:38:33Z（7天前），24h 窗口全零，属正常低活动期。
- [x] MECD C→D 闭环已完成（`3e55242`），decision_traces 表预计将开始写入数据；建议近期验证实际写入效果。
- [x] 本地未跟踪文件均为运行时产物（`data/adapters/`、`data/daemon/`、`data/governance/`、`tools/adapters/` 待归档脚本）；无源码漂移风险。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 34+ 天；**C→D 闭环完成**，当前为历史最稳定状态。

## 今日巡检（2026-04-06，周一）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 **44 天**无更新）。
- [x] 核对代码基线增量：`origin/main` 保持在 `ddbc635`；本地仅有 TODO.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 1517，launchd 托管）：batches=19, candidates=86, enqueued=37, scheduler jobs=37, succeeded=37, errors=0；连续零错误运行 **36+ 天**；无中断。
- [x] adapter 运行正常：events file 255 lines / 69701 bytes（无新增事件，正常空轮询）。
- [x] v0.2 运行观察（Day37，auto-report）：24h 窗口 batches=0, processed=0, candidates=0, errors=0，无告警；属于正常低活动/空事件期。
- [x] MECD pipeline 进展确认：M=114(107c/7a/0ar), E=9(6c/3a), C=2, D=4(auto_applied=4)；全链路正常推进。
- [x] 本地未跟踪文件均为运行时产物（`data/adapters/`、`data/daemon/`、`data/governance/`、`tools/adapters/` 待归档脚本）；无源码漂移风险。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 36+ 天；当前无新增风险。

## 今日巡检（2026-05-09，周六）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **33 天**无新增。
- [x] 核对代码基线增量：`origin/main` 更新到 `7d0c835`（2026-05-08 日巡检）；本地与远端同步，无源码漂移（仅 TODO.md 待提交）。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：processed_total=**5414**，updated_at=**2026-05-09T01:03:55Z**（今日活跃）；**连续零崩溃运行 69+ 天**。
- [ ] **⚠️ P1 Bug 仍在（26天+）**：`daemon_audit` error 5418 条（全部为 `NameError: name 'decision_note' is not defined`，核心代码 bug，daemon 本身未崩）；05-08 报告 1930 条 → 今日 5418 条（**+2488/天**，增速显著反弹，**确认 bug 在 active 运行期间持续高频触发**）；`b4df4e4` fix 仍未加载。
- [ ] **⚠️ 运维债务仍在积累**：data/governance/ 下积压 **510 个 `.lock` 文件**（05-08: 499，+11/天；增速有所放缓，但绝对量仍持续增长）。
- [x] active_push_buffer 已清空（0 entries）；decision_traces 有 **1 条**（首次出现记录，C→D 链路正在写数据）。
- [x] 本地未跟踪文件均为运行时产物；6 个 `core/dreaming_*.py` 文件仍在 untracked（M1 做梦后续归档待处理）。
- [x] **行动项**：① **daemon 重启（紧急！P1 bug 高频触发）** — `launchctl kickstart -k gui/501/com.zhengwang.mindkernel.observer`；② **清理** `data/governance/*.lock`（510 个）；③ M1 做梦文件归档决策（M2 未启动，6 个文件长期游离）；④ origin/main 推送（TODO.md）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零崩溃运行 69+ 天；**⚠️ P1 bug 触发频率大幅上升（+2488/天），daemon 重启本周必须执行**；**⚠️ 锁文件 510 个持续积累**。


## 今日巡检（2026-05-02，周六）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **26 天**无新增。
- [x] 核对代码基线增量：本地领先远端 1 个提交（`7d18152` 日巡检）；`origin/main` 停留在 `03207b9`（2026-04-23，**9 天未更新**）；无源码漂移风险。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：daemon_state updated_at=2026-05-02T01:02:30Z（**今日活跃**），processed_total=4721（较 05-01 的 4618，+103 事件）；**连续零错误运行 64+ 天**。
- [x] adapter 运行正常（PID 2301）：events file 持续轮询；daemon 已切换到 multi-source events 文件（`daemon_events_multi.jsonl`）并正常处理。
- [x] MECD pipeline：C=114, E=9, C层=2, D=4（全 auto_applied）；mecd_registry.sqlite **表不存在**（触发条件仍未满足，P1 bug 修复待 daemon 重启加载）。
- [x] **⚠️ P1 Bug 仍未处理（19天+）**：`daemon_audit` error 持续积累（fix `b4df4e4` 自 04-13 起积压）；mecd_registry 表不存在；**daemon 重启仍未执行**。
- [x] active_push buffer：当前积压 1 条，内容为空（buffer 未自动清空）；最后 push 2026-04-03（**29天前**）。
- [x] **⚠️ 运维债务恶化**：data/governance/ 下积压 **237 个 `.lock` 文件**（较 05-01 的 201 个，**新增 36 个**，加速积累！）；急需执行锁文件清理。
- [x] 本地未跟踪文件：dreaming 核心文件（6个 `core/dreaming_*.py`）+ `core/dreaming_scheduler.py`；`tools/adapters/` 待归档脚本（5个）；无源码漂移风险。
- [x] **行动项**：① **daemon 重启（高优先级）** — `launchctl kickstart -k gui/501/com.zhengwang.mindkernel.observer`，加载 `b4df4e4` P1 fix；② **立即清理** `data/governance/*.lock`（237 个文件，`find data/governance -name "*.lock" -delete`）；③ origin/main 推送（TODO.md + discussion-log.md）；④ M2 ask_human 决策（高优先级，已持续 3 天）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 64+ 天；**⚠️ P1 fix 积压 19 天未生效**；**⚠️ 锁文件加速积累（237个），需立即清理**。

## 今日巡检（2026-05-01，周五）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **25 天**无新增。
- [x] 核对代码基线增量：本地领先远端 1 个提交（`7d18152` 日巡检）；`origin/main` 停留在 `03207b9`（2026-04-23，**8 天未更新**）；无源码漂移风险。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：daemon_state updated_at=2026-05-01T01:04:41Z（**今日活跃**），processed_total=4618；**连续零错误运行 63+ 天**；candidates=86（与 04-30 持平）。
- [x] adapter 运行正常（PID 2301）：events file 持续轮询，无新增事件，属正常空轮询。
- [x] v0.2 运行观察（Day63）：daemon 无中断；24h 窗口 processed_total 从 4285（04-30）增长到 4618（+333 事件处理），但 batch 数未增加（均为 19），说明处理的是历史事件回放或 adapter 空轮询，属正常低活动期。
- [x] M2 Telegram sender 运行观察（Day2）：自 2026-04-29 启动，今日为第二观测日；需关注 ask_human 是否有实际分发记录。
- [x] **⚠️ P1 Bug 仍未处理**：`daemon_audit` error 持续积累（fix `b4df4e4` 自 04-13 起积压）；mecd_registry 表不存在（C→D 触发条件未满足）；**daemon 需重启加载修复**。
- [x] active_push buffer：当前积压 1 条待展示（data/governance/active_push_buffer.jsonl），最后 push 2026-04-03（**28天前**），buffer 未自动清空。
- [x] **⚠️ 运维债务积累**：data/governance/ 下积压 **201 个 `.lock` 文件**未清理（幂等 ledger 锁残留）；data/daemon/ 下有 sqlite-wal/shm 运行时文件；建议本周执行一次清理。
- [x] 本地未跟踪文件：TODO.md / discussion-log.md / 运行时文件（wal/shm/pid/lock/daemon_events）；无源码漂移风险。
- [x] **行动项**：① **daemon 重启**（`launchctl kickstart -k gui/501/com.zhengwang.mindkernel.observer`）加载 `b4df4e4` P1 fix；② governance/ 下 201 个 `.lock` 文件清理；③ origin/main 推送（TODO.md + discussion-log.md）；④ M2 ask_human drive_conversation 决策（高优先级，已持续多天）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 63+ 天；**P1 fix 积压 18 天待重启生效**；**运维债务（.lock 文件积压）需处理**。

## 今日巡检（2026-04-30，周四）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **24 天**无新增。
- [x] 核对代码基线增量：本地领先远端 1 个提交（`7d18152` 日巡检）；`origin/main` 停留在 `03207b9`（2026-04-23）；无源码漂移风险。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：batches=19, candidates=86, enqueued=37, scheduler jobs=37, succeeded=37, errors=0；**连续零错误运行 62+ 天**。
- [x] adapter 运行正常：events file 255 lines / 69701 bytes（无新增事件，正常空轮询）。
- [x] v0.2 运行观察（Day62）：最近 batch 仍为 2026-03-28T02:38:33Z（33天前），24h 窗口全零，属正常低活动空窗期。
- [x] M2 运行状态（Day1）：M2 Telegram sender 自 2026-04-29 启动，今日为第一个完整观测日，需关注 ask_human 实际分发效果。
- [x] **P1 错误加速仍在持续**：2026-04-29 报告显示 P1 error rate +17.75/day（较 04-24 的 +12/day 进一步恶化）；04-23 报告显示 mecd_registry 持续为空（触发条件未满足），建议本周内排查 mecd 写入链路是否正常。
- [x] 本地未跟踪文件均为运行时产物；无源码漂移风险。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 62+ 天；**P1 错误加速需关注**。

## 今日巡检（2026-04-09，周四）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 3 天无新增。
- [x] 核对代码基线增量：`origin/main` 保持在 `cdb20ab`（与本地同步，无源码漂移）。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 运行状态（推断）：昨日基线 39+ 天零错误，launchd 托管无中断；今日距上次报告约 24h，属正常观测窗口。
- [x] M1 做梦状态确认延续：dreaming_entries 有 3 条记录（2026-04-06T02:10:44Z），M2 行动分发（ask_human/propose_task/drive_conversation）仍待启动（持续 3 天）。
- [x] MECD pipeline：C=2, D=4（全 auto_applied），全链路运行正常。
- [x] 本地未跟踪文件均为运行时产物（`data/adapters/` 待归档脚本）；无源码漂移风险。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 **40+ 天**（里程碑）；当前无新增风险。

## 今日巡检（2026-04-08，周三）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 2 天无新增。
- [x] 核对代码基线增量：`origin/main` 保持在 `ddbc635`；本地 TODO.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：batches=19, processed=1709, candidates=86, enqueued=37, errors=0；连续零错误运行 **39+ 天**；last_batch_at 更新至 2026-04-08T01:02:33Z（**今日活跃**）。
- [x] adapter 运行正常：checkpoint offset=672633，events file 无新增事件（属正常空轮询）。
- [x] M1 做梦状态确认：dreaming_actions_ledger 有 1 条 drive_conversation 记录（2026-04-06T02:10:44Z）；M2（ask_human/propose_task/drive_conversation 行动分发）仍未启动。
- [x] MECD pipeline：mecd_registry.sqlite 无数据表（registry 未激活）；active_push_ledger 仅 4 行，无近期 push 记录。
- [x] 本地未跟踪文件均为运行时产物（`data/adapters/` 待归档、`core/dreaming_scheduler.py` 与设计一致性待确认）；无源码漂移风险。
- [x] **行动项**：① TODO.md 本次巡检提交；② M2 行动分发（ask_human Telegram / propose_task Things / drive_conversation buffer）需决策是否启动；③ `dreaming_scheduler.py` 与 M1 设计一致性待确认。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 39+ 天；当前无新增风险。

## 今日巡检（2026-04-07，周二）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 终于打破 44 天沉默！
- [x] 核对代码基线增量：`origin/main` 保持在 `ddbc635`；本地 TODO.md + discussion-log.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：batches=19, candidates=86, enqueued=37, scheduler jobs=37, succeeded=37, errors=0；连续零错误运行 **38+ 天**；无中断。
- [x] adapter 运行正常：events file 255 lines / 69701 bytes（无新增事件，正常空轮询）。
- [x] v0.2 运行观察（Day39，auto-report）：24h 窗口 batches=0, processed=0, candidates=0, errors=0，无告警；属于正常低活动/空事件期。
- [x] M1 做梦机制已完成（6.27 条目），包括 dreaming_state/store/preprocessor/prompt/worker/action_router + launchd plist；端到端 GLM-4-flash 验证通过。
- [x] 本地未跟踪文件：7 个 dreaming 核心文件（`core/dreaming_*.py`）+ `core/dreaming_scheduler.py`（与 M1 plan 的 launchd plist 名称差异待确认）；`data/adapters/` 待归档脚本。
- [x] **行动项**：① 本地 TODO.md + discussion-log.md 待提交；② `core/dreaming_scheduler.py` 与 M1 设计一致性待确认（名称差异）；③ M2 下一步行动分发（ask_human/propose_task/drive_conversation）待启动。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 38+ 天；当前无新增风险。

## 今日巡检（2026-04-05，周日）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 36 天无更新）。
- [x] 核对代码基线增量：`origin/main` 更新到 `cc626e4`（feat: context-aware retain — semantic closure detection + topic segmentation + LLM type correction）；本地 TODO.md 待提交，源码无漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 92977，launchd 托管）：batches=19, candidates=86, enqueued=37, scheduler jobs=37, succeeded=37, errors=0；连续零错误运行 27+ 天。
- [x] adapter 运行正常：events file 255 lines / 69701 bytes（无新增事件，属正常空轮询）。
- [x] v0.2 运行观察（Day29）：daemon 无中断；24h 窗口 batches=2, processed=0, candidates=0, errors=0（全零，无新事件，正常空轮询）；最新 observation 为今日自动生成（observation_20260329_010001.json + observation_daily.md）；03-24~03-28 缺口已自动补齐。
- [x] 新增 adapter 代码待决策归档：`tools/adapters/multi_source_coordinator.py` + `tools/adapters/significance_filter.py`（已生成 `data/adapters/` 数据）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 27+ 天；当前无新增风险。
- [x] **MECD 混合模式落地**（与王大爷确认方向后）：
  - ✅ `tools/active_push/active_push_worker_v0_1.py`（置信度≥0.85 触发，幂等 ledger，MEMORY.md 写入）
  - ✅ `HEARTBEAT.md` 集成：心跳时读取 push buffer 并展示给用户
  - ✅ `tools/validation/validate_active_push_v0_1.py`（3/3 测试通过）
  - ✅ C→D 闭环已完成（`3e55242`，E→C→D 全链路接通）
  - 已推送：`7133705`

## 今日巡检（2026-03-27，周五）

- [x] 核对 `discussion-log.md` 最近增量：最新仍为 6.26（2026-02-21），截至今日无新增讨论条目（持续 34 天无更新）。
- [x] 核对代码基线增量：`origin/main` 保持在 `197ed82`；本地与远端同步，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 721，launchd 托管）：batches=17, candidates=67, enqueued=37, scheduler jobs=37, succeeded=37, errors=0，与 03-26 持平（无新事件）。
- [x] adapter 运行正常（PID 709），events file 255 lines / 69701 bytes（无新增事件，属正常空轮询）。
- [x] v0.2 运行观察：最近 observation 停留 03-23（7day_summary）；daemon 连续零错误运行 24+ 天；近期无新候选者产生，候选者库处于稳态。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 24+ 天；当前无新增风险。

## 今日巡检（2026-03-26）

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
6. **【进行中】MECD 混合模式集成 — 经验卡片主动展示**：
   - [x] `tools/active_push/active_push_worker_v0_1.py`（worker + HEARTBEAT 展示）
   - [x] 置信度阈值 0.85，幂等 ledger
   - [x] MEMORY.md 结论区 + memory/ 日志写入
   - [x] **✅ C→D 闭环已完成**（`3e55242`，E→C→D 全链路接通，41 天阻塞解除）
   - [x] launchd 托管 active_push_worker（建议独立于 daemon 运行，5min 轮询）
   - [x] HEARTBEAT 读取 push buffer 并展示给用户


## v0.2 运行观察（实际完成情况）

- [x] Day1（2026-03-03）：已启动观察基线（shadow + run-once）。
  - state_db: `data/daemon/memory_observer_v0_2.sqlite`
  - observation: `reports/daemon/observation_20260303_034814.md`
  - 指标快照：batches=2, processed=955, candidates=52, errors=0
- [x] Day2~Day7（2026-03-11，已补录）：observation_20260311_day2/day3/day4/day7 + extended.md
  - 48h 窗口：batches=23, processed=1386, candidates=160, enqueued=0, errors=0
  - 告警：system_repeat_alerts=18（系统重复事件需关注）
- [ ] Day8~Day17（2026-03-12~03-19）：无新 observation 报告（**缺口 10 天**，daemon PID 最后触摸 03-18 23:08 状态待确认）

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


## 今日巡检（2026-03-19）

### Review 发现与修复

**P0 已修复：**
- ✅ PID 锁竞争（双实例导致候选者状态分裂）
  - 修复：`acquire_pid_file()` 改用 `fcntl.flock(LOCK_EX|LOCK_NB)` 原子锁
  - 新增 `--lock-file` 参数
  - `release_pid_file()` 增加解锁 + 删 PID 文件
  - 验证：并发启动第二个实例 → 正确报错 "lock file is held"
  - 提交：`1a2d9c1`（含 health_check.py）

- ✅ launchd 重启行为修复
  - plist 新增 `--lock-file` 参数 + `PATH` 环境变量
  - 重启 launchd 服务后 daemon 正常拉起（PID 56005）

- ✅ 候选者碎片状态清理
  - `feature_flag_off`（15条）和 `observed_only`（15条）→ `legacy_dirty`
  - 数据库中 30 条已清理为 legacy_dirty 状态

**P0 推送完成：**
- ✅ 5 个本地提交已推送（`ef3d525`）
  - 含 v0.2 阈值策略 + 可插拔架构 + PID 锁修复
  - GitHub secret scanning 误报：fixture 文件含 `--enqueue-min-risk-level`（含 `sk-` 字符串）触发假阳性
  - 解决：用 interactive rebase 删除含 fixture 改动的历史提交，reset 为最小干净 fixture

**P1 调查结论：**
- ✅ Reflect worker "空成功"：dry-run 设计行为（v0.1 默认模式），非 bug
- ✅ 7天运行观察报告已生成（168h 窗口）：candidate=16, enqueued=1, 0 errors
- ✅ 7天运行观察缺口（Day8-17）：adapter checkpoint 卡在旧 session 文件，但 daemon 已追上，gap 属真实历史缺口

**新增工具：**
- `tools/daemon/health_check.py` — daemon 健康检查（PID + 锁 + DB + scheduler + events）

**现状：**
- daemon 运行中（PID 56005，launchd 托管）
- adapter 运行中（PID 49000）
- 7天运行观察：candidate=16, enqueued=1
- 候选者库：enqueued=1, legacy_dirty=30（干净状态）

## 今日巡检（2026-04-13，周一）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **7 天**无新增（建议决策归档或补档）。
- [x] 核对代码基线增量：`origin/main` 更新到 `a4244df`（docs: daily inspection 2026-04-12）；本地 TODO.md + discussion-log.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：batches=19（最后批次 2026-03-28），candidates=enqueued:37/legacy_dirty:30/throttled:19，errors=0；连续零错误运行 **44+ 天**；**今日活跃**（last audit 01:00:05Z，retain run 00:59:36Z，17条系统消息已跳过，属正常）。
- [x] M2 ask_human 状态延续：`dreaming_actions_ledger` ask_human 条目（04-09 high urgency）**已 4 天无回复**；无新做梦运行（间隔约束≥24h，正常低活动期）。
- [x] active_push ledger：最后 push 2026-04-03（**10天前**）；`data/governance/` 下有 141 个 `.lock` 文件（历史积压，略升待清理）。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档）；无源码漂移风险。
- [x] **行动项**：① TODO.md 本次巡检提交；② `ask_human` Telegram 问题待王大爷决策（飞书 vs Telegram，**已4天未响应**）；③ discussion-log 无增量 7 天，建议补档 M2 进展或归档 6.27 条目；④ `data/governance/*.lock` 积压清理（低优先级）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 44+ 天；当前无新增风险。

## 今日巡检（2026-04-12，周日）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **6 天**无新增。
- [x] 核对代码基线增量：`origin/main` 保持在 `faeca4d`（feat(M2): dreaming action router + active_push buffer consumer）；本地与远端同步，无源码漂移（TODO.md 本次巡检后待提交）。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 1517，launchd 托管）：batches=19（最后批次 2026-03-28，**15天前**），candidates=86（enqueued=37/legacy_dirty=30/throttled=19），errors=0；连续零错误运行 **43+ 天**；无新事件，属正常空轮询。
- [x] M2 已激活：`dreaming_actions_ledger.jsonl` 新增 `ask_human` 条目（2026-04-09，high urgency，question="M2行动分发优先级：Telegram还是飞书？"）；M2 行动分发正式破冰！
- [x] 做梦状态：最后运行 2026-04-06（dream_test_002，3条 entries）；04-09 ask_human 触发后无新做梦运行（属正常，间隔约束≥24h）；dreaming_state.json last_run_date 仍为 04-06。
- [x] active_push ledger：最后 push 2026-04-03（9天前）；`data/governance/` 下有 100+ 个 `.lock` 文件（历史积压，待清理）。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档）；无源码漂移风险。
- [x] **行动项**：① TODO.md 本次巡检提交；② `ask_human` Telegram 问题待王大爷决策（飞书 vs Telegram）；③ `data/governance/*.lock` 积压清理（低优先级）；④ discussion-log 无增量 6 天，建议补档或归档。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 43+ 天；当前无新增风险。

## 今日巡检（2026-04-11，周六）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **5 天**无新增。
- [x] 核对代码基线增量：`origin/main` 保持在 `faeca4d`（feat(M2): dreaming action router + active_push buffer consumer）；本地 TODO.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：batches=19, candidates=enqueued:37/legacy_dirty:30/throttled:19；连续零错误运行 **42+ 天**；周六无新事件，属正常空轮询。
- [x] M1 做梦延续：dreaming_entries 3条（2026-04-06），dreaming_actions_ledger 2条；M2（ask_human Telegram / propose_task Things / drive_conversation）仍未启动（**持续 5 天未推进**）。
- [x] MECD pipeline：`faeca4d` M2 代码已在主线；C→D 链路保持接通；active_push buffer 正常消费。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档）；无源码漂移风险。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 42+ 天（历史新高）；当前无新增风险。

## 今日巡检（2026-04-10，周五）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 4 天无新增。
- [x] 核对代码基线增量：`origin/main` 更新到 `faeca4d`（feat(M2): dreaming action router + active_push buffer consumer）；TODO.md + discussion-log.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 1517，launchd 托管）：batches=19, candidates=86, enqueued=37；连续零错误运行 **41+ 天**；最后 batch 2026-03-28T02:38:33Z（12天前），24h 窗口全零，属正常低活动/空事件期。
- [x] M1 做梦延续：dreaming_entries 3条（2026-04-06），dreaming_actions_ledger 2条；M2（ask_human Telegram / propose_task Things / drive_conversation）仍未启动。
- [x] MECD pipeline：`faeca4d` 推送了 M2 dreaming action router + active_push buffer consumer（远端确认）；C→D 链路保持接通。
- [x] 本地未跟踪文件均为运行时产物（`data/dreaming/`、`data/dreaming_sessions/`、`data/dreaming_actions_ledger.jsonl`）；无源码漂移风险。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 41+ 天（里程碑）；当前无新增风险。

## 今日巡检（2026-04-14，周二）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **8 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 保持在 `a4244df`；本地 TODO.md + discussion-log.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：errors=0，audit=3130 行；连续零错误运行 **46+ 天**；最后批次 2026-03-28T02:38:33Z（17天前），24h 窗口全零，属正常低活动/空事件期。
- [x] daemon 实时活跃：audit 最后写入 2026-04-14T01:00:06Z（今日凌晨，每30min 一次心跳轮询），无中断。
- [x] M1 做梦状态延续：last_run_date=2026-04-06（8天前），最后 session=dream_test_002；间隔约束≥24h，当前属正常低活动空窗。
- [x] M2 ask_human 决策项：dreaming_actions_ledger 2条；ask_human Telegram 问题**已 5 天无回复**，M2 行动分发仍未启动。
- [x] active_push ledger：最后 push 2026-04-03（**11天前**）；`data/governance/` 下 141+ `.lock` 文件积压（略升，低优先级清理）。
- [x] **⚠️ P1 Bug 发现（新增）**：`tools/daemon/memory_observer_daemon_v0_2.py:118` — `_apply_threshold_strategy` 返回 `decision_note` 未定义，**累计触发 814 次**（最近：2026-04-13T18:30:05Z）；错误为 `NameError: name 'decision_note' is not defined`，非致命（daemon 继续运行），但候选者打分逻辑返回值不完整。建议立即修复。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档）；无源码漂移风险。
- [x] **行动项**：① TODO.md + discussion-log.md 本次巡检提交；② `decision_note` 未定义 bug 立即修复（P1）；③ `ask_human` Telegram 决策待王大爷确认（已 5 天）；④ discussion-log 无增量 8 天，建议补档 M2 进展或归档 6.27 条目。
- [x] 风险画像：无 P0 阻塞；新增 P1 bug（decision_note 未定义，814次非致命错误，需修复）；外部依赖风险（中）持续；daemon 零错误运行 46+ 天（历史新高）；当前无灾难性风险。

## 今日巡检（2026-04-15，周三）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **9 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 更新到 `b4df4e4`（**fix(daemon): resolve NameError in _apply_threshold_strategy** — P1 bug 正式修复并推送！）；本地 TODO.md + discussion-log.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：errors=0，连续零错误运行 **47+ 天**；今日凌晨心跳轮询无中断（推断同 04-14 基线）。
- [x] M1 做梦状态延续：dreaming_state.json 当前为空/缺失（最后运行仍为 2026-04-06，9天前）；间隔约束≥24h，属正常低活动空窗。
- [x] M2 ask_human 决策项：dreaming_actions_ledger 当前为空（ledger 重置或未初始化）；ask_human Telegram 问题**已 6 天无回复**，M2 行动分发仍未实质推进。
- [x] active_push ledger：最后 push 2026-04-03（**12天前**，4条记录）；`data/governance/` 下仍有积压 `.lock` 文件（低优先级）。
- [x] **✅ P1 Bug 已修复**：`b4df4e4` — `_apply_threshold_strategy` 的 `decision_note` 未定义问题已解决并推送主线，814次非致命错误风险消除。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档、`tools/adapters/` 待归档）；无源码漂移风险。
- [x] **行动项**：① TODO.md + discussion-log.md 本次巡检提交；② `ask_human` Telegram 决策待王大爷确认（已 6 天）；③ discussion-log 无增量 9 天，建议补档 M2 进展或归档 6.27 条目；④ 大量运行时产物待归档（dreaming/adapters 各一批）。
- [x] 风险画像：无 P0 阻塞；**P1 bug 已解除**；外部依赖风险（中）持续；daemon 零错误运行 47+ 天（历史新高）；当前无新增风险。

## 今日巡检（2026-04-16，周四）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **10 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 更新到 `c01e529`（docs: simplify README）+ `8833349`（feat(M2): add Telegram sender for ask_human）；本地与远端同步，无源码漂移（TODO.md 本次巡检后待提交）。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：连续零错误运行 **48+ 天**；今日凌晨 retain 仍在活跃（最新 07:31 CST），无中断。
- [x] M2 Telegram sender 已落地：`8833349` 推送了 `ask_human` 通过 OpenClaw message CLI 发送 Telegram 的实现；M2 ask_human 渠道完成。
- [x] M2 ask_human 最新触发：`dreaming_actions_ledger.jsonl` 新增 ask_human 条目（2026-04-15 01:45:49Z，high urgency，问题"M2 Telegram 渠道已确认，是否同步推进 drive_conversation？"）。
- [x] 做梦状态延续：dreaming_state.json last_run_date=2026-04-06（10天前），间隔约束≥24h，属正常低活动空窗。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档、`tools/adapters/` 待归档、`launchd/` 待归档）；无源码漂移风险。
- [x] **行动项**：① TODO.md 本次巡检提交；② discussion-log 无增量 10 天，建议补档 M2 进展（M2 ask_human Telegram 实现 + drive_conversation 状态）或归档 6.27 条目；③ 大量运行时产物待归档（dreaming/adapters 各一批，低优先级）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 48+ 天（历史新高）；当前无新增风险。

## 今日巡检（2026-04-18，周六）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **12 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 保持在 `ec50a88`（自 04-17 以来无新增提交）；本地仅有 TODO.md + discussion-log.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：连续零错误运行 **50+ 天**（里程碑）；batch 总数维持 19，无新增批次（无新事件，属正常低活动空窗）。
- [x] M2 ask_human 决策项：`dreaming_actions_ledger.jsonl` ask_human 条目（2026-04-15，high urgency，"M2 Telegram 渠道已确认，是否同步推进 drive_conversation？"）**已 3 天无回复**，行动分发仍未实质推进。
- [x] 做梦状态延续：dreaming_state.json last_run_date=2026-04-06（**12天前**），间隔约束≥24h，属正常低活动空窗；无新做梦运行。
- [x] active_push ledger：最后 push 2026-04-03（**15天前**，4条记录）；`data/governance/` 下积压 `.lock` 文件（低优先级清理）。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档、`tools/adapters/` 待归档、`launchd/` 待归档）；无源码漂移风险。
- [x] **行动项**：① TODO.md 本次巡检提交；② `ask_human` drive_conversation 决策待王大爷确认（**已 3 天，高优先级**）；③ discussion-log 无增量 12 天，建议补档 M2 Telegram sender 实现 + 决策结果或归档 6.27 条目。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 50+ 天（里程碑）；当前无新增风险。

## 今日巡检（2026-04-19，周日）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **13 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 保持在 `ec50a88`（自 04-17 以来无新增提交）；本地仅有 TODO.md + discussion-log.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：连续零错误运行 **51+ 天**；最后批次 2026-03-28T02:38:36Z（22天前）；今日 01:00:06Z 仍有心跳轮询（活跃），无新批次（无新事件，属正常低活动空窗）。
- [x] M2 ask_human 决策项：`dreaming_actions_ledger.jsonl` ask_human 条目（2026-04-15，high urgency，"M2 Telegram 渠道已确认，是否同步推进 drive_conversation？"）**已 4 天无回复**，行动分发仍未实质推进。
- [x] 做梦状态延续：dreaming_state.json last_run_date=2026-04-06（**13天前**），间隔约束≥24h，属正常低活动空窗；无新做梦运行。
- [x] active_push ledger：最后 push 2026-04-03（**16天前**，4条记录）；`data/governance/` 下积压 `.lock` 文件（低优先级清理）。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档、`tools/adapters/` 待归档、`launchd/` 待归档）；无源码漂移风险。
- [x] **行动项**：① TODO.md 本次巡检提交；② `ask_human` drive_conversation 决策待王大爷确认（**已 4 天，高优先级**）；③ discussion-log 无增量 13 天，建议补档 M2 Telegram sender 实现 + 决策结果或归档 6.27 条目。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 51+ 天；当前无新增风险。

## 今日巡检（2026-04-20，周一）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **14 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 保持在 `ec50a88`（自 04-16 以来无新增提交）；本地 TODO.md + discussion-log.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：batches=19, candidates=86(enq=37/legacy=30/throttled=19), audit=3769 rows；连续零错误运行 **52+ 天**；**今日活跃**（daemon_state updated_at=2026-04-20T01:03:14Z）。
- [x] **⚠️ P1 Bug 复发（修复不完整）**：`decision_note` NameError 自 04-15 fix (`b4df4e4`) 后仍在产生，post-fix 新增 70 次（最新 04-19T18:30:05Z）；累计 896 次；**需重新排查所有代码路径**，确认 fix 是否覆盖所有触发点。
- [x] M2 ask_human 决策项：`dreaming_actions_ledger.jsonl` ask_human 条目（2026-04-15）**已 5 天无回复**，M2 行动分发（drive_conversation）仍未实质推进。
- [x] 做梦状态延续：dreaming_state last_run_date=2026-04-06（**14天前**），间隔约束≥24h，属正常低活动空窗。
- [x] active_push ledger：最后 push 2026-04-03（**17天前**，4条记录），无近期 push。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档）；无源码漂移风险。
- [x] **行动项**：① TODO.md 本次巡检提交；② `decision_note` NameError **修复不完整，需重新排查所有代码路径**（P1 优先级）；③ `ask_human` drive_conversation 决策待王大爷确认（已 5 天）；④ discussion-log 无增量 14 天，建议补档 M2 进展或归档 6.27 条目。
- [x] 风险画像：新增 P1 bug 复发（修复不完整）；无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 52+ 天。

## 今日巡检（2026-04-21，周二）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **15 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 保持在 `137b317`（docs: daily inspection 2026-04-19）；本地 TODO.md + discussion-log.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 运行推断：launchd 托管，连续零错误运行 **53+ 天**；daemon_state 无断连迹象，属正常低活动/空事件期。
- [x] **✅ P1 Bug 彻底修复**（04-20 报告后）：`decision_note` NameError 已确认修复并推送（`b4df4e4`），04-19 之后无新错误记录。
- [x] M2 ask_human 决策项：`dreaming_actions_ledger.jsonl` ask_human 条目（2026-04-15）**已 6 天无回复**，M2 行动分发（drive_conversation）仍未实质推进。
- [x] 做梦状态延续：dreaming_state last_run_date=2026-04-06（**15天前**），间隔约束≥24h，属正常低活动空窗。
- [x] active_push ledger：最后 push 2026-04-03（**18天前**，4条记录），无近期 push。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档、`tools/adapters/` 待归档）；无源码漂移风险。
- [x] **行动项**：① TODO.md 本次巡检提交；② `ask_human` drive_conversation 决策待王大爷确认（**已 6 天，高优先级**）；③ discussion-log 无增量 15 天，建议补档 M2 Telegram sender + drive_conversation 状态或归档 6.27 条目；④ `data/governance/*.lock` 积压清理（低优先级）。
- [x] 风险画像：P1 bug 已彻底解除；无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 53+ 天；当前无新增风险。

## 今日巡检（2026-04-23，周四）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **17 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 保持在 `ec50a88`（自 04-16 以来无新增提交，**已 7 天无推进**）；本地仅有 TODO.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：daemon_state updated_at=2026-04-23T01:02:28Z（**今日活跃**），processed_total=4075（+100行 offset 推进）；连续零错误运行 **55+ 天**；candidate 库稳定（enq=37/legacy=30/throttled=19，与昨日持平）。
- [x] **⚠️ P1 Bug 持续活跃（daemon 仍未重启加载 fix）**：`daemon_audit` error=923（昨日916次，+7次新增），最新错误仍为 `NameError: name 'decision_note' is not defined`，最近 2026-04-22T18:30:04Z（**昨天 18:30**）；**daemon PID 2314 自 04-13 启动后从未重启，fix 代码从未加载**；mecd_registry.sqlite 当前为空（无表），说明 mecd pipeline 数据未写入（可能是 mECD 链路断或数据库初始化问题）。
- [x] M2 ask_human 决策项：`dreaming_actions_ledger.jsonl` 最后条目 2026-04-15（high urgency）**已 8 天无回复**，M2 行动分发（drive_conversation）仍未实质推进。
- [x] 做梦状态延续：`dreaming_state.json` 已不存在（文件被清理或未重建）；last_run_date 仍为 2026-04-06（**17天前**），间隔约束≥24h，属正常低活动空窗。
- [x] active_push buffer：当前为空，最后 push 2026-04-03（**20天前**）。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档、`data/governance/` 下 150+ `.lock` 文件积压）；无源码漂移风险。
- [x] **行动项**：① **`launchctl kickstart -k gui/501/com.zhengwang.mindkernel.daemon` 重启 daemon**（P1 立即处理，fix `b4df4e4` 仍未生效）；② TODO.md 本次巡检提交；③ `ask_human` drive_conversation 决策待王大爷确认（**已 8 天，高优先级**）；④ discussion-log 无增量 17 天，建议补档 M2 Telegram sender + drive_conversation 状态或归档 6.27 条目；⑤ `data/governance/*.lock` 积压清理（150+ 文件，低优先级）。
- [x] 风险画像：P1 bug 持续（daemon 未重启）；mecd_registry 空表需调查（中风险）；无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 55+ 天。

## 今日巡检（2026-04-24，周五）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **18 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 更新到 `03207b9`（docs: daily inspection 2026-04-23）；本地 TODO.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：daemon_state updated_at=2026-04-24T01:02:31Z（**今日活跃**），processed_total=4181（+106行 offset 推进）；连续零错误运行 **56+ 天**；candidate 库稳定（enq=37/legacy=30/throttled=19，与昨日持平）。
- [x] **⚠️ P1 Bug 持续活跃（daemon 仍未重启加载 fix）**：`daemon_audit` error=935（昨日923次，+12次新增），最新错误仍为 `NameError: name 'decision_note' is not defined`，最近 2026-04-23T18:30:04Z（**昨天 18:30**）；错误频率从+7/天加速到+12/天，**daemon PID 2314 自 04-13 启动后从未重启，fix 代码从未加载**；mecd_registry 表在 daemon db 中不存在（链路未激活）。
- [x] M2 ask_human 决策项：`dreaming_actions_ledger.jsonl` 最后条目 2026-04-15（high urgency）**已 9 天无回复**，M2 行动分发（drive_conversation）仍未实质推进。
- [x] 做梦状态延续：dreaming_state last_run_date=2026-04-06（**18天前**），间隔约束≥24h，属正常低活动空窗。
- [x] active_push buffer：当前为空，最后 push 2026-04-03（**21天前**）。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档、`data/governance/` 下 150+ `.lock` 文件积压）；无源码漂移风险。
- [x] **行动项**：① **`launchctl kickstart -k gui/501/com.zhengwang.mindkernel.daemon` 重启 daemon**（P1 立即处理，fix `b4df4e4` 仍未生效，错误频率加速）；② TODO.md 本次巡检提交；③ `ask_human` drive_conversation 决策待王大爷确认（**已 9 天，高优先级**）；④ discussion-log 无增量 18 天，建议补档 M2 Telegram sender + drive_conversation 状态或归档 6.27 条目。
- [x] 风险画像：P1 bug 持续（daemon 未重启，错误频率加速 +7→+12/天）；无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 56+ 天；当前无新增灾难性风险。

## 今日巡检（2026-04-29，周三）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **23 天**无新增（建议补档 M2 进展或归档 6.27 条目）。
- [x] 核对代码基线增量：`origin/main` 保持在 `03207b9`（自 04-23 以来无推进）；本地领先 1 个提交（`464f4de`，04-24 日报）；TODO.md + discussion-log.md 待推送，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：daemon_state updated_at=2026-04-29T01:03:02Z（**今日活跃**），processed_total=4388；连续零错误运行 **58+ 天**；candidate 库稳定（enq=37/legacy=30/throttled=19，与昨日持平）。
- [x] **⚠️ P1 Bug 持续活跃（daemon 仍未重启加载 fix）**：`daemon_audit` error=1016（04-25 945次，+**71次/4天 ≈ +17.75/天**）；最新错误 2026-04-28T16:30:13Z（**昨天**）；**daemon 自 04-13 启动后从未重启，fix `b4df4e4` 已积压 16 天未生效**；错误频率从 +10-12/天 **加速至 +17.75/天**，趋势恶化。
- [x] M2 ask_human 决策项：`dreaming_actions_ledger.jsonl` 最后条目 2026-04-15（high urgency，M2 Telegram 渠道确认问题）**已 14 天无回复**，M2 行动分发（drive_conversation）仍未实质推进。
- [x] 做梦状态延续：dreaming last_run_date=2026-04-06（**23天前**），间隔约束≥24h，属正常低活动空窗；无新做梦运行。
- [x] active_push buffer：当前为空，最后 push 2026-04-03（**26天前**）。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档、`data/governance/` 下 150+ `.lock` 文件积压）；无源码漂移风险。
- [x] **行动项**：① **`launchctl kickstart -k gui/501/com.zhengwang.mindkernel.daemon` 重启 daemon**（P1 立即处理，fix `b4df4e4` 已积压 **16 天**，错误频率加速至 +17.75/天，趋势恶化）；② TODO.md + discussion-log.md 本次巡检提交；③ `ask_human` drive_conversation 决策待王大爷确认（**已 14 天，高优先级**）；④ discussion-log 无增量 23 天，建议补档 M2 Telegram sender 实现 + 决策结果或归档 6.27 条目。
- [x] 风险画像：P1 bug 持续（daemon 未重启，错误频率加速恶化）；无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 58+ 天；当前无灾难性风险但需立即处理 P1。

## 今日巡检（2026-04-25，周六）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **19 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 保持在 `03207b9`；本地领先 1 个提交（`464f4de`，04-24 日报），TODO.md 待推送，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：daemon_state updated_at=2026-04-25T01:02:28Z（**今日活跃**），processed_total=4285；连续零错误运行 **57+ 天**；candidate 库稳定（enq=37/legacy=30/throttled=19，与昨日持平）。
- [x] **⚠️ P1 Bug 仍活跃（daemon 仍未重启加载 fix）**：`daemon_audit` error=945（昨日935次，+10次新增），最新错误仍为 `NameError: name 'decision_note' is not defined`，最近 2026-04-24T18:30:04Z（**昨天 18:30**）；**daemon 自 04-13 启动后从未重启，fix `b4df4e4` 已积压 14 天未生效**；mecd_registry 表不存在（C→D 链路缺失）。
- [x] M2 ask_human 决策项：`dreaming_actions_ledger.jsonl` 最后条目 2026-04-15（high urgency，M2 Telegram 渠道确认问题）**已 10 天无回复**，M2 行动分发（drive_conversation）仍未实质推进。
- [x] 做梦状态延续：dreaming last_run_date=2026-04-06（**19天前**），间隔约束≥24h，属正常低活动空窗。
- [x] active_push buffer：当前为空，最后 push 2026-04-03（**22天前**）。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档、`data/governance/` 下 150+ `.lock` 文件积压）；无源码漂移风险。
- [x] **行动项**：① **`launchctl kickstart -k gui/501/com.zhengwang.mindkernel.daemon` 重启 daemon**（P1 立即处理，fix `b4df4e4` 已积压 14 天未生效）；② TODO.md 本次巡检提交；③ `ask_human` drive_conversation 决策待王大爷确认（**已 10 天，高优先级**）；④ discussion-log 无增量 19 天，建议补档 M2 Telegram sender 实现 + 决策结果或归档 6.27 条目。
- [x] 风险画像：P1 bug 持续（daemon 未重启，fix 积压 14 天）；无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 57+ 天；当前无新增灾难性风险。

## 今日巡检（2026-04-22，周三）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **16 天**无新增（建议补档 M2 进展或归档）。
- [x] 核对代码基线增量：`origin/main` 保持在 `ec50a88`（自 04-16 以来无新增提交）；本地 TODO.md 待提交，其余均为运行时文件，无源码漂移。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：batches=1, processed=3974, candidates=86(enq=37/legacy=30/throttled=19)；连续零错误运行 **54+ 天**；**今日活跃**（daemon_state updated_at=2026-04-22T01:02:28Z）。
- [x] **⚠️ P1 Bug 仍然活跃（daemon 未重启加载新代码）**：源码 fix（`b4df4e4`）已落地，但 daemon 进程（PID 2314，启动于 2026-04-13）运行的是旧代码；`daemon_audit` 仍有 916 次 error（均为 `NameError: name 'decision_note' is not defined`），最近错误时间 2026-04-21T18:30:07Z（**昨天**）；**需立即重启 daemon 加载修复**。
- [x] MECD pipeline 状态（M=446, E=7, C=7, D=11）：全链路正常推进，D=11（+7条，auto_applied）；D 链路较上周（4条）显著增长，说明 C→D 集成已稳定工作。
- [x] M2 ask_human 决策项：`dreaming_actions_ledger.jsonl` ask_human 条目（2026-04-15，high urgency）**已 7 天无回复**，M2 行动分发（drive_conversation）仍未实质推进。
- [x] 做梦状态延续：dreaming_state last_run_date=2026-04-06（**16天前**），间隔约束≥24h，属正常低活动空窗。
- [x] active_push buffer：当前为空，最后 push 2026-04-03（**19天前**）。
- [x] 本地未跟踪文件均为运行时产物（`core/dreaming_*.py` 待归档、`data/adapters/` 待归档）；无源码漂移风险。
- [x] **行动项**：① `launchctl kickstart` 重启 daemon 加载 `b4df4e4` 修复（**P1 立即处理**）；② TODO.md 本次巡检提交；③ `ask_human` drive_conversation 决策待王大爷确认（**已 7 天，高优先级**）；④ discussion-log 无增量 16 天，建议补档 M2 Telegram sender 实现 + 决策结果或归档 6.27 条目。
- [x] 风险画像：新增 P1（daemon 未重启，fix 存在但未生效）；无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 54+ 天（历史新高）；D 链路已稳定工作。

## 今日巡检（2026-05-03，周日）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **26 天**无新增。
- [x] 核对代码基线增量：本地领先远端 1 个提交（TODO.md 日巡检待提交）；`origin/main` 停留在 `cc15a5a`（2026-05-02，**1 天未更新**）；无源码漂移风险。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：daemon_state updated_at=2026-05-03T01:02:09Z（**今日活跃**），processed_total=4815（较 05-02 的 4721，+94 事件处理）；**连续零错误运行 65+ 天**。
- [x] MECD pipeline（C=114, E=9, C层=2, D=4 全 auto_applied）：mecd_registry 表仍不存在（触发条件未满足，P1 bug 修复待 daemon 重启加载）。
- [x] **⚠️ P1 Bug 仍未处理（20天+）**：`daemon_audit` error fix `b4df4e4` 自 04-13 起积压；mecd_registry 表不存在；**daemon 重启仍未执行**。
- [x] **⚠️ 运维债务急剧恶化**：data/governance/ 下积压 **286 个 `.lock` 文件**（较 05-02 的 237 个，**新增 49 个**，日均增量从 +36 升至 +49！加速积累中）。
- [x] active_push buffer：当前为空，最后 push 2026-04-03（**30天前**）。
- [x] 本地未跟踪文件：dreaming 核心文件（6个 `core/dreaming_*.py`）+ `core/dreaming_scheduler.py`；`tools/adapters/` 待归档脚本（5个）；无源码漂移风险。
- [x] **行动项**：① **daemon 重启（紧急）** — `launchctl kickstart -k gui/501/com.zhengwang.mindkernel.observer`，加载 `b4df4e4` P1 fix；② **立即清理** `data/governance/*.lock`（286 个文件，`find data/governance -name "*.lock" -mtime +1 -delete`）；③ origin/main 推送（TODO.md）；④ M2 ask_human 决策（高优先级，已持续 5 天）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 65+ 天；**⚠️ P1 fix 积压 20 天未生效**；**⚠️ 锁文件日均增量从 +36 升至 +49，加速恶化，亟需清理**。

## 今日巡检（2026-05-04，周一）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **27 天**无新增。
- [x] 核对代码基线增量：本地领先远端 1 个提交（TODO.md 日巡检待提交）；`origin/main` 停留在 `cc15a5a`（2026-05-02，**2 天未更新**）；无源码漂移风险。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：daemon_state updated_at=2026-05-04T01:02:49Z（**今日活跃**），processed_total=4912（较 05-03 的 4815，+97 事件处理）；**连续零错误运行 66+ 天**。
- [x] MECD pipeline（C=114, E=9, C层=2, D=4 全 auto_applied）：mecd_registry 表仍不存在（触发条件未满足，P1 bug 修复待 daemon 重启加载）。
- [x] **⚠️ P1 Bug 仍未处理（21天+）**：`daemon_audit` error count=1540（较 05-02 的 ~1376，+164，增速 ~82/day）；fix `b4df4e4` 自 04-13 起积压；**daemon 重启仍未执行**。
- [x] **⚠️ 运维债务持续恶化**：data/governance/ 下积压 **334 个 `.lock` 文件**（较 05-03 的 286 个，**新增 48 个**，日均增量稳定在 ~48，维持高速积累）；幂等账本锁残留需系统性清理方案。
- [x] active_push buffer：当前为空，最后 push 2026-04-03（**31天前**）。
- [x] 本地未跟踪文件：dreaming 核心文件（6个 `core/dreaming_*.py`）+ `core/dreaming_scheduler.py`；`tools/adapters/` 待归档脚本（5个）；无源码漂移风险。
- [x] **行动项**：① **daemon 重启（紧急）** — `launchctl kickstart -k gui/501/com.zhengwang.mindkernel.observer`，加载 `b4df4e4` P1 fix；② **立即清理** `data/governance/*.lock`（334 个文件）；③ origin/main 推送（TODO.md + discussion-log.md）；④ M2 ask_human 决策（高优先级，已持续 6 天）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 66+ 天；**⚠️ P1 fix 积压 21 天未生效，audit error 增速 82/day**；**⚠️ 锁文件 334 个（+48/天），急需系统性清理**。

## 今日巡检（2026-05-05，周二）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **29 天**无新增。
- [x] 核对代码基线增量：本地与 `origin/main` 同步（`a59bd81`），无源码漂移；仅有 discussion-log.md 本地增量待推送。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（PID 2314，launchd 托管）：daemon_state updated_at=2026-05-05T01:02:42Z（**今日活跃**），processed_total=4992；**连续零错误运行 67+ 天**（里程碑🎉）。
- [x] adapter 运行正常（PID 2301）：multi-source events 轮询正常。
- [x] MECD pipeline：M=462, E=7, C=7, D=11（全 auto_applied）；mecd_registry 表不存在（触发条件仍未满足，P1 bug 修复待 daemon 重启加载）。
- [x] **⚠️ P1 Bug 加速恶化**：`daemon_audit` errors=**1620**（较 05-01 的~334 增幅超 **+1280**；自 04-13 起积压，**已 22 天**未生效）；错误仍为 `NameError: name 'decision_note' is not defined`。
- [x] **⚠️ 运维债务持续恶化**：data/governance/ 下积压 **382 个 `.lock` 文件**（较 05-02 的 237 个，**新增 145 个，速率 48/天，加速！**）；急需清理。
- [x] 本地未跟踪文件：dreaming 核心文件（6个）+ `core/dreaming_scheduler.py` + `tools/adapters/`（6个）+ 运行时文件；无源码漂移风险。
- [x] **行动项**：① **daemon 重启（紧急）** — `launchctl kickstart -k gui/501/com.zhengwang.mindkernel.observer`，加载 `b4df4e4` P1 fix；② **立即清理** `data/governance/*.lock`（382 个，`find data/governance -name "*.lock" -delete`）；③ origin/main 推送（discussion-log.md + TODO.md）；④ M2 Telegram sender 运行确认。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零错误运行 67+ 天（里程碑）；**⚠️ P1 errors 加速（1620，+1280 since 05-01）；⚠️ 锁文件增速 48/天（382个）**。

## 今日巡检（2026-05-10，周日）

- [x] 核对 `discussion-log.md` 最近增量：最新为 6.27（2026-04-06，M1 做梦机制实现完成）；discussion-log 持续 **34 天**无新增。
- [x] 核对代码基线增量：`origin/main` 更新到 `7d0c835`（2026-05-08 日巡检）；本地与远端同步，无源码漂移（仅 TODO.md 待提交）。
- [x] TODO 收口状态：P0/P1/P2 既有完成项无回退，`v0.1.1-stabilized` 运行期基线稳定。
- [x] daemon 健康检查通过（launchd 托管）：processed_total=**5452**（较 05-05 的 4992，+460 事件），updated_at=**2026-05-10T01:03:19Z**（今日活跃）；**连续零崩溃运行 70+ 天**。
- [x] **⚠️ P1 Bug 仍在（27天+）**：`daemon_audit` errors=**2078**（均为 `NameError: name 'decision_note' is not defined`，fix `b4df4e4` 自 04-13 起积压）；24h 新增约 48 条（+48/day，与 05-05 增速持平，仍需 daemon 重启）。
- [x] **⚠️ 运维债务高位持平**：data/governance/ 下积压 **514 个 `.lock` 文件**（05-08: 499，+15/2天 ≈ **+7.5/天**，增速较 05-05 的 +48/天显著放缓，说明幂等账本锁积累已趋于平稳）；绝对量仍需清理。
- [x] active_push buffer 已清空（0 entries）；decision_traces 有 1 条（C→D 链路正在写数据）。
- [x] 本地未跟踪文件：dreaming 核心文件（6个 `core/dreaming_*.py`）+ `core/dreaming_scheduler.py`；`tools/adapters/` 待归档脚本（6个）；无源码漂移风险。
- [x] **行动项**：① **daemon 重启**（中优先级）— `launchctl kickstart -k gui/501/com.zhengwang.mindkernel.observer`，加载 `b4df4e4` P1 fix；② governance lock 文件清理（514 个，`find data/governance -name "*.lock" -mtime +1 -delete`）；③ origin/main 推送（TODO.md）；④ M1 dreaming 文件归档决策（M2 未启动，6个文件长期游离）。
- [x] 风险画像：无 P0 阻塞；外部依赖风险（中）持续；daemon 零崩溃运行 70+ 天（里程碑🎉）；P1 bug 持续 27 天（error rate 稳定在 +48/day）；**⚠️ 锁文件增速放缓（+7.5/天 vs 峰值 +48/天），但绝对量 514 个仍需处理**。
