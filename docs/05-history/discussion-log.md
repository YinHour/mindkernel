# Discussion Log — 2026-02-14

> 目的：记录本次从 `memory-v2` 演进到 `mindkernel` 的关键讨论与决策轨迹。
> 状态：归档文档（讨论记录），非主规范。

---

## 1) 讨论主线（摘要）

本次讨论从“记忆系统不好用”出发，逐步升级为“智能体心智系统工程”问题。核心演进：

1. 记忆问题不只是检索，而是缺少工程闭环。
2. 记忆应从事实中心升级为事件/时间/关联中心。
3. 遗忘是默认机制，巩固是条件触发。
4. 会话连续性与人格连续性应分离（双边界）。
5. 架构主干确定为：人格-认知-记忆。
6. 补入 Experience 作为记忆到认知的中间层。
7. 引入社会认知冲突治理与认知失调信号。
8. 引入反欺骗（记忆注入）调查与级联回滚。
9. 引入反偏执红队机制，避免系统保守僵化。
10. 引入情绪-冲动-行动快回路，与认知慢回路合流。
11. 项目改名为 **MindKernel（心智内核）**，重启主规范。
12. 需求工程基线建立（MR/CR/FR/NFR + Traceability）。
13. 进一步确认：认知不是“对/错”二值，必须支持未知态与分流策略。
14. 引入时间轴驱动遗忘机制，明确遗忘效率不应依赖全量扫描。
15. 将未知态治理与遗忘调度联动，避免无限挂起与学习停滞。

---

## 2) 关键决策时间线（按讨论阶段）

### 阶段 A：问题重定义（约 12:37-13:00）

- 用户指出：当前记忆体系存在明显问题，需要新项目。
- 共识：不是“记忆检索调参”，而是“心智架构重建”。
- 共识：人类记忆以事件、时间、关联为中心；遗忘是核心机制。

### 阶段 B：理论框架扩展（约 13:00-13:50）

- 共识：人机记忆应“同构能力 + 异构实现”。
- 共识：人格连续性 ≠ 会话连续性。
- 共识：采用“人格-认知-记忆”三层结构。
- 新增：Experience 层与人格冲突闸门。
- 新增：社会认知优先与认知失调治理。
- 新增：反欺骗调查与反馈闭环。
- 新增：偏执风险红队验证与控制。

### 阶段 C：行为动力学补充（约 15:05-15:10）

- 共识：事件刺激不仅转经验，还会经情绪产生冲动并影响行动。
- 新增：Affect-Impulse-Action 快回路，并要求行动前闸门调节。

### 阶段 D：项目重启与需求工程化（约 15:14-15:33）

- 决策：采用新项目名 **mindkernel**（心智内核）。
- 动作：旧文档迁移为 legacy，建立新主规范文档。
- 动作：先做“一页项目说明 + 需求工程基线”。
- 发现：当前版本可能导致心智僵化、自驱不足。
- 动作：新增反僵化与自驱学习的 MR/CR/FR/NFR 条款。

### 阶段 E：未知态深化（约 15:38-15:50）

- 问题：CR-9 过多人工介入可能降低效率。
- 优化：改为“分级自动验证 + 条件升级人工”。
- 共识：认知非二元，未知态需细分。
- 新增未知态分类：
  - `multipath`（多路径并存）
  - `out_of_scope`（超出认知范围）
  - `ontic_unknowable`（原理性不可知）
- 文档已更新：CR-10/CR-11、FR-15~FR-17、NFR-10~NFR-13。

### 阶段 F：时间轴遗忘机制（约 15:57-16:00）

- 问题：遗忘机制需要显式时间轴变量以保证执行效率。
- 共识：遗忘应采用“到期驱动调度”，而非全量扫描。
- 新增时间轴变量基线：
  - `created_at` / `last_accessed_at` / `last_reinforced_at`
  - `last_verified_at` / `review_due_at` / `stale_since`
  - `expires_at` / `uncertainty_ttl` / `next_action_at`
- 文档已更新：CR-12、FR-18~FR-21、NFR-14/NFR-15、2.10 时间轴变量基线。

### 阶段 G：设计文档工程化整理（约 16:00 后）

- 动作：将需求条款映射到 schema 草案目录（`schemas/`）。
- 新增草案：
  - `common-temporal.schema.json`
  - `persona.schema.json`
  - `memory.schema.json`
  - `experience.schema.json`
  - `cognition.schema.json`
- 动作：在主规范新增“数据契约映射”章节（2.11）与文档整理状态（2.12）。
- 动作：新增 `contents-map.md`，明确主规范/讨论/归档/schema 的关系与维护规则。

---

## 3) 当前已达成的稳定共识（可视作“已定原则”）

1. 人格边界是硬约束。
2. 记忆是证据，不是指令。
3. Experience 是记忆到认知的必经层。
4. 认知抽象必须通过人格冲突闸门。
5. 社会认知默认优先，但允许合法例外。
6. 反欺骗与反偏执必须共同优化。
7. 冲动不能绕过闸门直接驱动高风险行动。
8. 认知状态必须支持非二元（含未知态）。
9. 遗忘机制必须时间轴驱动，默认采用到期调度而非全量扫描。

---

## 4) 仍待进一步设计的问题（与主规范 OI 对齐）

- Experience 状态机最小状态数（5 vs 7）。
- 社会认知分层评分是否引入时效衰减。
- 冲动调节阈值标定方式。
- 治理作业自动化与人工职责分工。
- 探索预算分配策略。
- 关键事件显著性评分引擎选择。
- 认知状态迁移阈值。
- `uncertain` 人工升级率阈值。
- 未知态三分法自动判别机制。
- `ontic_unknowable` 的验证上限与退出条件。
- 时间衰减函数参数（`half_life`、`impact_weight`、`reinforcement_count`）定标。
- `next_action_at` 调度器实现方案（优先队列/时间轮/分区扫描）选择。

---

## 5) 文档关系

- 主规范：`docs/01-foundation/requirements-and-architecture.md`
- 历史草案：`archive/requirements-and-architecture.legacy.md`
- 本讨论记录：`docs/05-history/discussion-log.md`

> 维护规则：后续新增讨论优先写入“讨论记录”，定稿后再进入“主规范”。

---

## 6) 增量讨论记录（2026-02-20）

### 6.1 项目更名与仓库对齐

- 决策：项目正式名称统一为 **MindKernel（心智内核）**，仓库目录名统一为 `mindkernel`。
- 动作：
  - 本地目录由 `projects/positronic-brain` 重命名为 `projects/mindkernel`。
  - 文档中项目名与相关描述已批量更新。
  - Git remote 从 `sharkwang/positronic-brain` 切换到 `sharkwang/mindkernel`。
- 结果：远程 `origin/main` 已与本地主线对齐（包含改名提交）。

### 6.2 v0.1 启动文档与最小契约落地

- 决策：采用“先闭环、后扩展”的启动策略，先交付可验证的 v0.1 最小系统定义。
- 新增文档：
  - `docs/01-foundation/mindkernel-v0.1-scope.md`
  - `docs/02-design/rule-table-v0.1.md`
  - `docs/03-validation/e2e-scenarios-v0.1.md`
  - `schemas/decision-trace.schema.json`
- 覆盖内容：
  - v0.1 In/Out Scope 与 Go/No-Go 验收门槛
  - Memory→Experience→Cognition 的可执行规则表
  - uncertain 分流与高风险拦截策略
  - 伪造注入回滚、TTL 分流、reinstate 等 E2E 验收场景
  - DecisionTrace 最小审计契约（风险、闸门、证据、结论）

### 6.3 下一步建议（已转执行）

1. 复核 `rule-table-v0.1` 的阈值参数（TTL/预算/风险阈值）。
2. 将 v0.1 启动文档与主规范做条款映射（补 RTM 子表）。
3. 实现最小调度器原型（基于 `next_action_at` 的到期拉取）。
4. 按 `e2e-scenarios-v0.1` 执行首次可运行验收。

### 6.4 三步执行结果（2026-02-20）

- 已完成 `docs/02-design/rtm-v0.1.md`
  - 将 v0.1 设计与主规范 MR/CR/FR/NFR 做覆盖映射（Full/Partial/Out）。
- 已完成 `docs/02-design/state-machines-v0.1.md`
  - 定义 Memory/Experience/Cognition 最小状态机及不变量，明确与 `epistemic_state` 双轴关系。
- 已完成 `docs/02-design/scheduler-interface-v0.1.md`
  - 给出到期调度器最小接口（enqueue/pull/ack/fail）与幂等、重试、死信策略。
- 同步动作：`docs/contents-map.md` 更新为 v2，并纳入 v0.1 启动包索引。

### 6.5 docs + schemas 联合复核与整理（2026-02-20）

- 目标：对全量 docs 与 schemas 做一致性复核，统一术语与状态语义。
- 发现并处理：
  1. E2E 场景中的 Memory 注入状态与 schema 枚举不一致（`forged/invalidated` -> `rejected_poisoned`）。
  2. Cognition 的 `stale_uncertain` 术语与状态枚举存在层次差异，统一为“概念层术语”，数据层表达为 `status=stale + epistemic_state=uncertain`。
  3. `memory.schema.json` 缺少 `evidence_refs` 约束，与规则表不一致；已补为必填（`minItems=1`）。
  4. schema 索引未纳入 `decision-trace.schema.json`；已补齐。
  5. README 命名来源描述与 `05-history/name-origin.md` 不一致；已统一为引用 `docs/05-history/name-origin.md`。
- 新增整理文档：
  - `docs/02-design/design-consolidation-v0.1.md`（统一口径与维护规则）
- 结果：v0.1 启动包在“规则表 ↔ 状态机 ↔ E2E ↔ schema”四层之间达到当前一致。

### 6.6 审计契约补全（2026-02-20）

- 决策：补齐独立审计事件契约，避免将“状态迁移审计”与“决策快照”混写。
- 新增：`schemas/audit-event.schema.json`
- 字段基线：
  - `actor` / `reason` / `evidence_refs` / `before` / `after` / `timestamp`
  - `event_type`、`object_type`、`object_id`、`correlation_id`
  - 高风险事件要求绑定 `decision_trace_id`
- 同步更新：
  - `schemas/README.md`
  - `docs/01-foundation/requirements-and-architecture.md`（2.11 映射）
  - `docs/contents-map.md`
  - `docs/02-design/design-consolidation-v0.1.md`

### 6.7 关键路径验证资产化（2026-02-20）

- 决策：将 v0.1 验证场景从“文档描述”升级为“fixtures + 可执行校验脚本”。
- 新增：
  - `data/fixtures/critical-paths/01-happy-path.json`
  - `data/fixtures/critical-paths/02-poison-rollback.json`
  - `data/fixtures/critical-paths/03-uncertain-ttl-routing.json`
  - `data/fixtures/critical-paths/04-high-risk-block.json`
  - `data/fixtures/critical-paths/05-reinstate.json`
  - `tools/validation/validate_scenarios_v0_1.py`
  - `docs/03-validation/validation-critical-paths-v0.1.md`
- 覆盖关键路径：
  1. 正常闭环（Memory→Experience→Cognition→Decision）
  2. 注入确认与级联回滚
  3. uncertain 到期分流（TTL + 预算耗尽）
  4. 高风险拦截（禁止 uncertain 直执）
  5. 新证据 reinstate 回升
- 执行结果：本地脚本校验通过（5/5 场景，25 个对象/事件）。

### 6.8 关键路径验证接入 CI（2026-02-20）

- 决策：将关键路径校验接入 GitHub Actions，确保变更自动回归。
- 新增：`.github/workflows/critical-path-validation.yml`
- 触发策略：
  - push 到 `main`（当 `schemas/**`、`docs/**`、`data/fixtures/**`、校验脚本或工作流本身变更时）
  - pull request（同路径过滤）
  - `workflow_dispatch` 手动触发
- 执行命令：`python3 tools/validation/validate_scenarios_v0_1.py`
- 目标：把 v0.1 关键路径从“可手动验证”升级为“默认自动守护”。

### 6.9 最小调度器原型落地（2026-02-20）

- 决策：进入实现前半步，先交付 `next_action_at` 调度器可运行原型（SQLite）。
- 新增：
  - `tools/scheduler/scheduler_v0_1.py`
  - `docs/04-prototypes/scheduler-prototype-v0.1.md`
- 支持能力：
  - `init-db / enqueue / pull / ack / fail / stats`
  - 幂等键去重（`idempotency_key`）
  - 失败重试与死信（`dead_letter`）
  - 到期拉取排序（`run_at ASC + priority DESC`）
- 结果：原型本地命令流已验证可用，可作为后续状态机与审计接入底座。

### 6.10 调度审计接入与韧性路径补全（2026-02-20）

- 决策：将调度器原型直接接入 `audit-event`，并把重试/死信纳入关键路径验证。
- 调度器增强：
  - `tools/scheduler/scheduler_v0_1.py` 新增 `audit_events` 表写入。
  - `enqueue/pull/ack/fail` 自动产出 `event_type=scheduler_job` 审计事件。
  - 新增 `list-audits` 命令用于快速查看审计流。
- 新增验证场景：
  - `data/fixtures/critical-paths/06-scheduler-retry.json`
  - `data/fixtures/critical-paths/07-scheduler-dead-letter.json`
- 校验脚本更新：
  - `tools/validation/validate_scenarios_v0_1.py` 新增 S6/S7 业务断言（retry 回队与 dead_letter 终态）。
- 结果：关键路径覆盖从 5 条扩展到 7 条。

### 6.11 运行时契约校验 + Memory→Experience 先跑通（2026-02-20）

- 决策：在原型层引入“运行时 schema 校验”，避免实现偏离契约定义。
- 调度器增强：
  - 新增 `tools/schema_runtime.py` 作为轻量校验模块。
  - `tools/scheduler/scheduler_v0_1.py` 的审计写入前强制校验 `audit-event.schema.json`。
- 新增前半链路原型：
  - `tools/pipeline/memory_experience_v0_1.py`
  - `docs/04-prototypes/memory-experience-prototype-v0.1.md`
- 关键能力：
  - `ingest-memory`（Memory 入库 + schema 校验）
  - `memory-to-experience`（基于 R-ME-01 生成 Experience candidate）
  - `run-path`（一键跑通 Memory→Experience）
  - 全流程写入并校验 `audit-event`。
- 验证覆盖扩展：
  - 新增 `data/fixtures/critical-paths/08-memory-experience-path.json`
  - `tools/validation/validate_scenarios_v0_1.py` 增加 S8 断言
- 结果：关键路径覆盖从 7 条扩展到 8 条。

### 6.12 Markdown 记忆输入支持（2026-02-20）

- 需求：Memory 输入形式增加 Markdown。
- 实现：
  - `tools/pipeline/memory_experience_v0_1.py` 新增 Markdown 解析路径（`.md/.markdown`）。
  - 支持可选 front matter（`key: value`），正文自动映射到 `content`。
  - 对缺省字段自动补全（`id/source/evidence_refs/时间轴字段` 等），再走 `memory.schema.json` 强校验。
- 新增样例：
  - `data/fixtures/critical-paths/09-memory-markdown.md`
- 校验增强：
  - `tools/validation/validate_scenarios_v0_1.py` 新增 Markdown fixture 校验（S9）。
- 结果：关键路径覆盖从 8 条扩展到 9 条。

### 6.13 Experience→Cognition 最小升格链路（含 Persona Gate）（2026-02-20）

- 决策：推进 Experience→Cognition 最小可运行实现，并引入 Persona Gate 的可解释阻断路径。
- 新增原型：
  - `tools/pipeline/experience_cognition_v0_1.py`
  - `docs/04-prototypes/experience-cognition-prototype-v0.1.md`
- 核心能力：
  - `upsert-persona` / `ingest-experience` / `experience-to-cognition` / `run-path`
  - Persona Gate 最小策略：`boundaries` 关键词与 `episode_summary/outcome/action_taken` 匹配
  - `pass` -> 生成 Cognition candidate（R-EC-01）
  - `block` -> 拒绝升格并记录 gate 事件（R-EC-02）
- 验证覆盖扩展：
  - 新增 `data/fixtures/critical-paths/10-experience-cognition-pass.json`
  - 新增 `data/fixtures/critical-paths/11-experience-cognition-block.json`
  - `tools/validation/validate_scenarios_v0_1.py` 新增 S10/S11 断言
- 结果：关键路径覆盖从 9 条扩展到 11 条。

### 6.14 一体化链路串联（Memory→Experience→Cognition）（2026-02-20）

- 决策：将前两段原型串联为单命令全链路，降低联调成本。
- 新增：
  - `tools/pipeline/full_path_v0_1.py`
  - `docs/04-prototypes/full-path-prototype-v0.1.md`
- 能力：
  - `run-full-path` 一次执行：Memory ingest -> Experience candidate -> Persona gate -> Cognition promotion/block。
- 验证覆盖扩展：
  - `data/fixtures/critical-paths/12-full-path-pass.json`
  - `data/fixtures/critical-paths/13-full-path-block.json`
  - `tools/validation/validate_scenarios_v0_1.py` 新增 S12/S13 断言。
- 结果：关键路径覆盖从 11 条扩展到 13 条。

### 6.15 Cognition→Decision 最小链路（2026-02-20）

- 决策：补齐闭环最后一跳，交付 Cognition→DecisionTrace 原型。
- 新增：
  - `tools/pipeline/cognition_decision_v0_1.py`
  - `docs/04-prototypes/cognition-decision-prototype-v0.1.md`
- 最小策略：
  - supported + low/medium -> normal/executed
  - uncertain + medium -> conservative/limited
  - uncertain + high -> escalate/escalated
  - refuted -> abstain/abstained
- 验证覆盖扩展：
  - `data/fixtures/critical-paths/14-cognition-decision-pass.json`
  - `data/fixtures/critical-paths/15-cognition-decision-high-risk-block.json`
  - `tools/validation/validate_scenarios_v0_1.py` 新增 S14/S15 断言。
- 结果：关键路径覆盖从 13 条扩展到 15 条。

### 6.16 Full Path 升级为 M→E→C→D 闭环（2026-02-20）

- 决策：将 `tools/pipeline/full_path_v0_1.py` 从 M→E→C 升级为 M→E→C→D 一键闭环。
- 关键更新：
  - 引入 `cognition_decision_v0_1` 依赖，`run-full-path` 新增 `--request-ref` 与可选 `--risk-tier`。
  - Gate pass：调用 `cognition_to_decision` 产出 DecisionTrace。
  - Gate block：调用 `gate_block_to_decision` 产出 blocked DecisionTrace（保留 boundary_hits）。
- 对齐调整：
  - `12-full-path-pass.json` 与 `13-full-path-block.json` 增补 `decision_trace` 与决策审计事件。
  - `tools/validation/validate_scenarios_v0_1.py` 同步强化 S12/S13 断言（检查 decision 层行为）。
- 结果：全链路闭环可一键执行，关键路径总覆盖维持 15 条，但校验对象/事件提升到 62。

### 6.17 项目整理（2026-02-20）

- 目标：统一仓库入口、文档索引与运行资产边界，降低后续维护成本。
- 结构整理：
  - 新增 `tools/README.md`（脚本地图）
  - 新增 `data/README.md`（fixtures 与运行产物边界）
  - 新增 `docs/03-validation/system-smoke-report-v0.1.md`（报告产出说明）
  - `docs/contents-map.md` 升级为 v10，并纳入 smoke-report 文档
- 规范对齐：
  - 更新 `README.md` 为“规范 + 原型并行”阶段说明，补齐快速开始
  - 更新 `CONTRIBUTING.md`，修正讨论记录路径并强化“实现必须带验证”原则
- 运行资产清理：
  - 清理 `data/*.sqlite`、`reports/*` 与 `tools/__pycache__`
  - `.gitignore` 增加 `reports/` 忽略规则
- 结果：项目入口更清晰，运行产物与源码边界明确。

### 6.18 docs 分类归档（2026-02-20）

- 需求：按主题对 `docs/` 文件进行分类存储。
- 执行：
  - `docs/01-foundation/`：主规范与章程（requirements/charter/scope）
  - `docs/02-design/`：规则、状态机、调度接口、RTM、设计整合
  - `docs/03-validation/`：E2E、关键路径校验、smoke 报告说明
  - `docs/04-prototypes/`：各链路原型说明（ME/EC/CD/full/scheduler）
  - `docs/05-history/`：discussion-log 与命名历史
- 同步：
  - 全仓引用路径更新（README/CONTRIBUTING/docs/schemas/tools）
  - `docs/contents-map.md` 升级并反映新目录结构
- 校验：
  - 所有 `docs/...` 引用路径存在性检查通过
  - 关键路径验证脚本通过（62 对象/事件）

### 6.19 OpenClaw 记忆研究对比分析（2026-02-20）

- 参考文档：`/opt/homebrew/lib/node_modules/openclaw/docs/zh-CN/experiments/research/memory.md`
- 结论：
  - MindKernel 当前在“治理闭环”更强（M→E→C→D + 审计 + Gate + 回滚）。
  - 研究文档在“离线记忆回忆层”更强（retain/recall/reflect、实体中心检索、时间查询）。
  - 两者应融合为“Markdown 规范源 + 派生索引 + 治理闭环”的统一架构。
- 差距识别：
  1. 缺少 `memory/YYYY-MM-DD.md + bank/*` 的长期记忆分层组织。
  2. 缺少 retain 规范与反思作业（reflect）机制。
  3. 缺少实体中心 recall 与时间窗口检索能力。
  4. opinion 置信度演化机制尚未实现（证据驱动更新）。
- 改进建议（分层）：
  - P0：引入记忆目录分层（daily + bank）与 `## Retain` 规范。
  - P1：实现 `.memory/index.sqlite` 派生索引（FTS 优先，离线可重建）。
  - P2：实现 recall API（lexical/entity/time/opinion）并输出 fact-pack（含 source 引用）。
  - P3：将 reflect 作业接入 scheduler，回写 entities/opinions/core memory。
- 架构落点：
  - `Markdown Source -> Index(reindex) -> Recall(fact-pack) -> M/E/C/D Governance -> Reflect(update bank)`
- 预期收益：
  - 保持可审计与可编辑的 Markdown 优势，同时补齐高召回、实体化记忆与长期演化能力。

### 6.20 记忆层草案启动（2026-02-20）

- 已落地草案文档：
  - `docs/02-design/memory-index-architecture-v0.1.md`
  - `docs/02-design/retain-recall-reflect-spec-v0.1.md`
- 已新增原型骨架：
  - `tools/memory/memory_index_v0_1.py`
- 当前能力（draft）：
  - `init-db`：初始化 `.memory/index.sqlite`
  - `reindex`：扫描 `memory.md`、`memory/*.md`、`bank/**/*.md`，抽取 `## Retain`
  - `recall`：FTS5 + kind/entity/time 过滤，返回 fact-pack（含 `source_ref`）
  - `reflect`：生成实体摘要与观点候选（建议包）
- 说明：
  - 该脚本为草案骨架，重点是接口与数据流闭环；后续再补意见置信度演化与自动回写。

### 6.21 Retain 样例与 Reflect 写回（2026-02-20）

- 新增样例工作区：
  - `data/fixtures/memory-workspace/memory/2026-02-20.md`
  - `data/fixtures/memory-workspace/memory/2026-02-21.md`
  - `data/fixtures/memory-workspace/memory.md`
- `memory_index_v0_1.py` 增强：
  - `reflect` 新增 `--writeback`，可写回：
    - `bank/entities/<slug>.md`
    - `bank/opinions.md`（自动区块）
  - 新增参数：`--max-per-entity`、`--max-opinions`
- 新增原型文档：
  - `docs/04-prototypes/memory-index-prototype-v0.1.md`
- 结果：retain/recall/reflect 从“只输出”推进到“可建议式回写”。

### 6.22 Opinion 置信度演化（2026-02-20）

- 决策：在 memory-index 层先引入可解释、规则化的 opinion confidence 演化机制，不直接改动主闭环决策逻辑。
- `memory_index_v0_1.py` 新增：
  - `opinions_state` 表（`confidence/support_count/contradict_count/evidence_refs`）
  - `list-opinions-state` 命令
  - reflect 写回前执行演化更新（support/contradict）
- v0.1.1 规则：
  - 同向证据：`+0.05`（上限 0.99）
  - 反向证据：`-0.08`（下限 0.05）
- 新增验证资产：
  - `data/fixtures/memory-workspace-evolution/*`
  - `tools/validation/validate_memory_index_v0_1.py`
- 文档同步：
  - `docs/02-design/retain-recall-reflect-spec-v0.1.md`
  - `docs/02-design/memory-index-architecture-v0.1.md`
  - `docs/04-prototypes/memory-index-prototype-v0.1.md`
- 结果：Reflect 从“建议式写回”升级为“建议式写回 + 置信度可追踪演化”。

### 6.23 今日工作总结（2026-02-20）

今日已完成从“规范整理”到“可运行闭环 + 记忆层草案”的一整轮推进，核心结果如下：

1. **项目与文档体系**
   - 项目统一为 `mindkernel`，仓库与文档命名完成对齐。
   - `docs/` 按主题完成分类归档（foundation/design/validation/prototypes/history）。
   - `README / CONTRIBUTING / contents-map` 同步更新，入口更清晰。

2. **v0.1 核心闭环实现**
   - 完成并联通原型链路：
     - `memory_experience_v0_1.py`
     - `experience_cognition_v0_1.py`（含 Persona Gate）
     - `cognition_decision_v0_1.py`
     - `full_path_v0_1.py`（M→E→C→D 一键闭环）
   - Gate pass / Gate block 路径均可执行并产出 DecisionTrace。

3. **验证与工程化**
   - 建立关键路径 fixtures 与统一校验脚本，当前覆盖 **15 条关键路径**。
   - 校验规模达到 **62 objects/events**，全量通过。
   - 接入 GitHub Actions 自动校验，并支持 smoke report 生成。

4. **记忆层（retain/recall/reflect）草案落地**
   - 完成架构与规范草案：
     - `memory-index-architecture-v0.1.md`
     - `retain-recall-reflect-spec-v0.1.md`
   - 落地 `memory_index_v0_1.py`（reindex/recall/reflect）。
   - 增加样例 workspace 与 reflect 写回（entities/opinions）。

5. **opinion 演化能力（v0.1.1）**
   - 引入 `opinions_state` 与可解释置信度更新规则（support/contradict）。
   - 新增 `list-opinions-state` 与独立验证脚本。

**结论**：
- MindKernel 已从“设计规范主导”进入“规范 + 原型并行且可验证”的稳定阶段。
- 主闭环（M→E→C→D）可运行，记忆层（retain/recall/reflect）具备继续演进基础。

### 6.24 可用版执行计划启动（2026-02-21）

- 已创建执行计划：
  - `docs/06-execution/v0.1.0-usable-execution-plan.md`
  - 覆盖 S1~S11，定义 DoD（本地绿 + CI 绿 + 数据入口可复现 + 报告可审计）。
- 已完成 S1（基线固化）：
  - `ef913a6` 文档与 CI 对齐 + 计划落档
  - `3c7ca7b` memory-index 可用性增强（增量 reindex / 幂等 / 失败重试）
  - `2d45476` 新增迁移/会话解析链路
- S2 对齐动作：
  - `TODO.md` 同步为“P0 已完成，下一步转 P1”。
  - 风险从“CI 缺位”切换为“新增 ingest 工具尚未纳入门禁”。
- S3 门禁扩展（已完成）：
  - 新增 `tools/validation/validate_ingest_tools_v0_1.py`（迁移 dry-run + session 解析 + schema 校验）。
  - 新增 fixture：`data/fixtures/session-logs/sample-session.jsonl`。
  - 已并入 `.github/workflows/critical-path-validation.yml`。
  - CI 通过：GitHub Actions runs `22249216541`、`22249230818`、`22249239698`。

### 6.25 外部 LLM 记忆处理核心对象（2026-02-21）

- 新增核心对象：
  - `tools/memory/llm_memory_processor_v0_1.py`
  - 对象名：`LLMMemoryProcessor`（配置对象：`LLMProcessorConfig`）
- 能力：
  1. 调用外部 LLM（OpenAI-compatible）抽取记忆候选；
  2. 自动补齐 `memory.schema` 必需字段；
  3. 逐条 schema 校验；
  4. 稳定 ID + 去重（`sha1(source_ref|content)`）。
- 后端模式：
  - `mock`（本地可测）
  - `openai_compatible`（外部模型调用）
- 新增验证资产：
  - `tools/validation/validate_llm_memory_processor_v0_1.py`
  - `data/fixtures/llm-memory/sample-memory-input.txt`
- 新增原型文档：
  - `docs/04-prototypes/llm-memory-processor-v0.1.md`
- 结果：项目具备“可插拔外部模型记忆处理核心对象”，可作为后续导入链路与 reflect 增强的基础组件。

### 6.26 项目整理与交接冻结（2026-02-21）

- 已完成全项目整理快照：
  - `docs/06-execution/project-consolidation-2026-02-21.md`
- 统一了：
  1. 目录职责分层（foundation/design/validation/prototypes/execution）；
  2. 门禁脚本清单与标准执行命令；
  3. S4 启动输入、动作、输出定义。
- TODO 与风险口径同步：
  - 补充 LLM 核心对象已落地项；
  - 明确新增“外部依赖风险（中）”。

### 6.27 做梦机制 M1 实现完成（2026-04-06）

**背景**：
王大爷晨间完成了两份关键文档：
1. `project_review_full_20260406.md` — MECD 闭环完整度复盘
2. `c_dreaming_design_20260406.md` — C层做梦机制详细设计

**核心发现**：
- M→E 转化率仅 **2.3%**（305条记忆→7条经验），是整个闭环最大瓶颈
- MECD 综合评分 7.0/10（较上期 6.5 提升）
- C层"做梦"机制被提升到 **P0 优先级**

**设计决策**：
- 采用独立 `dreaming_entries` 表（隔离清晰，不污染 cognition_rules）
- 三类 triggered_actions：`ask_human` / `propose_task` / `drive_conversation`
- 做梦复用 cognition_engine 的 epistemic state 推导逻辑
- 人类反馈通过 `queue_id` 异步闭环，7天过期
- 四阶段实现：M1（核心闭环）→ M2（行动分发）→ M3（反馈闭环）→ M4（深度集成）

**M1 实现（今日完成）**：
新增 6 个核心文件：
- `core/dreaming_state.py` — 触发条件管理（01:00-05:00 窗口，≥20h 间隔）
- `core/dreaming_store.py` — `dreaming_entries` 表 + `dreaming_human_queue.jsonl`
- `core/dreaming_preprocessor.py` — 记忆/经验/话题/任务输入整合
- `core/dreaming_prompt.py` — LLM Prompt 模板（系统提示 + 用户模板 + 反馈模板）
- `core/dreaming_worker.py` — 做梦主逻辑（LLM 调用 + 解析 + 写入）
- `core/dreaming_action_router.py` — 三类行动幂等分发（ledger 去重）
- `launchd/com.zhengwang.mindkernel.dreaming-scheduler.plist` — 每日 01:30 定时触发

**M1 端到端验证结果**：
- ✅ GLM-4-flash 调用成功（35秒）
- ✅ 写入 3 条 `dreaming_entries`（association / emotion_action / task_activation 各 1 条）
- ✅ `drive_conversation` 行动已写入 `active_push_buffer`
- ✅ launchd 服务已注册并加载

**M2 规划**：
- `ask_human` → Telegram 主动消息（通过 OpenClaw message 工具）
- `propose_task` → Things / 飞书任务
- `drive_conversation` → active_push_buffer 推送
- 人类回复 → 触发反馈做梦（is_feedback_session=true）
