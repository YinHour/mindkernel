# Contents Map (v15)

本文件用于整理 `mindkernel/docs` 文档结构，避免信息分散。

## 开始与接续工作

- [推进记录与工作流程](06-execution/iteration-log.md)：当前唯一工作项、推进—review—更新规则、实际证据及下一次最小动作。
- [状态、瓶颈与恢复条件](06-execution/bottlenecks.md)：已观察问题、未验证假设、既有尝试及技术更新后的最小重试条件。
- [仓库协作约定](../AGENTS.md)：后续开发任务应遵循的读入、review 与收尾要求。

## 当前方向探索（2026-09-17）

- [个体智能方向讨论纪要](05-history/2026-09-17-individual-intelligence-direction.md)
  - 记录长期人机共同工作、小型个体、教导与好奇心、冲突求证、专业能力成长及多样性等方向。
  - 区分已明确目标、候选路径与待研究问题；纪要记录当时的方案探索阶段，后续只读数据实验见推进记录，不替代下方历史主规范。
- [个体协作智能推进计划（讨论稿）](superpowers/plans/2026-09-17-individual-intelligence-research-plan.md)
  - 按每周 3–5 小时提出六个周迭代，优先验证协作者动态侧写、场景理解、纠正、提问与技能迁移。
  - 明确对照方法、业界经验吸收、资源上限和阶段检查点；已根据后续要求将 Codex 数据入口提前，实际状态以推进记录为准。
- [第一周实验计划：Codex 数据入口与可回放案例](superpowers/plans/2026-09-17-week1-codex-data-experiment-plan.md)
  - 数据入口、首批开发案例和隔离基线已通过工程 review；当前验证情境组装，独立学习效果尚未验证。
- [Dream-RSI 对 MindKernel 的借鉴评估](05-history/2026-09-17-dream-rsi-review.md)
  - 核对原论文、同基座对照和代码发布状态；记录策略回放对当前瓶颈的借鉴及未观察分支不能代替真实反馈的边界。
- [Codex 单任务只读读取器](04-prototypes/codex-session-reader-v0.1.md)
  - 显式任务范围、快照回放、过滤与质量报告；说明助手时间缺失、格式覆盖和真实回放结果。

- [协作情境最小约定与离线探测](04-prototypes/collaboration-context-v0.1.md)
  - 五类情境、证据截止点、时效与冲突规则；公开参考工具和合成检查，真实材料保持本地。

## 核心规范（优先阅读）

阅读当前进展时，请同时查看 `../README.md`、`../CHANGELOG.md` 与 `../TODO.md`。下方 v0.1 文档保留历史基线；其中的“当前阶段”、测试数量与运行状态应按文档日期理解。

1. `01-foundation/requirements-and-architecture.md`
   - 主规范（MR/CR/FR/NFR、V&V、Traceability、Open Issues）
2. `01-foundation/project-charter.md`
   - 项目宪法级方向与阶段目标

## 讨论与追溯

3. `05-history/discussion-log.md`
   - 关键讨论与决策时间线
4. `05-history/name-origin.md`
   - 命名来源与更名说明

## v0.1 启动包（历史设计与验收基线）

5. `01-foundation/mindkernel-v0.1-scope.md`
   - v0.1 交付边界、里程碑、Go/No-Go
6. `02-design/rule-table-v0.1.md`
   - 可执行规则表（IF/THEN）
7. `02-design/state-machines-v0.1.md`
   - Memory / Experience / Cognition 最小状态机
8. `02-design/scheduler-interface-v0.1.md`
   - `next_action_at` 到期调度接口草案
9. `02-design/rtm-v0.1.md`
   - v0.1 需求追踪子表（覆盖主规范条款）
10. `02-design/design-consolidation-v0.1.md`
    - docs + schemas 统一口径与术语整理基线
11. `02-design/memory-index-architecture-v0.1.md`
    - Markdown 规范源 + 派生索引架构草案
12. `02-design/retain-recall-reflect-spec-v0.1.md`
    - retain/recall/reflect 语法与接口规范草案
13. `02-design/ingest-contract-v0.1.md`
    - memory JSONL -> objects 导入契约（S4 冻结）
14. `03-validation/e2e-scenarios-v0.1.md`
    - 端到端验收场景
15. `03-validation/validation-critical-paths-v0.1.md`
    - v0.1 fixtures + 校验脚本的关键路径覆盖说明
16. `03-validation/system-smoke-report-v0.1.md`
    - 系统烟测报告产出与解读方式
17. `04-prototypes/memory-index-prototype-v0.1.md`
    - retain/recall/reflect 索引原型说明
18. `04-prototypes/scheduler-prototype-v0.1.md`
    - 调度器接口的本地可运行原型说明
19. `04-prototypes/memory-experience-prototype-v0.1.md`
    - 记忆到经验路径的本地可运行原型说明
20. `04-prototypes/experience-cognition-prototype-v0.1.md`
    - 经验到认知路径（含 Persona Gate 最小实现）
21. `04-prototypes/cognition-decision-prototype-v0.1.md`
    - Cognition→DecisionTrace 最小链路说明
22. `04-prototypes/full-path-prototype-v0.1.md`
    - Memory→Experience→Cognition→Decision 一体化最小闭环说明
23. `04-prototypes/llm-memory-processor-v0.1.md`
    - 外部 LLM 记忆处理核心对象（抽取为 memory.schema 兼容对象）

## 数据契约草案（与主规范配套）

24. `../schemas/README.md`
    - schema 草案索引与维护说明
25. `../schemas/*.schema.json`
    - `common-temporal` / `persona` / `memory` / `experience` / `cognition` / `decision-trace` / `audit-event`

## 归档文档（只读）

26. `../archive/requirements-and-architecture.legacy.md`
27. `../archive/design.legacy.md`
28. `../archive/memory-entry.schema.legacy.json`

## 执行计划

29. `06-execution/v0.1.0-usable-execution-plan.md`
    - v0.1.0-usable 从原型到可交付版本的执行规划（S1~S11）
30. `06-execution/release-runbook-v0.1.0-usable.md`
    - v0.1.0-usable 发布执行手册（pre-check/tag/rollback）
31. `06-execution/project-consolidation-2026-02-21.md`
    - 项目整理快照（结构、门禁、脚本与 S4 交接点）

## 后续演进与集成入口

- `06-execution/v0.1.1-stabilization-plan.md`：稳定化执行记录。
- `06-execution/release-runbook-v0.1.1-stabilized.md`：历史稳定版发布与观测手册。
- `06-execution/v0.2-daemon-memory-observer-plan.md`：daemon 的职责与边界。
- `06-execution/daemon-runbook-v0.2.md`：feature flag、灰度与回退。
- `06-execution/v0.2-next-action-plan-2026-03-03.md`：原型完成后的观测计划。
- `openclaw-integration.md`：MCP/OpenClaw 集成与验证边界。
- `plans/2026-05-10-m2-action-dispatch.md`：行动分发原计划及实际实现差异。
- `../plugins/mcp_server/README.md`：MCP 工具参数与配置说明。

## 维护规则

- 新决策：先写入 `05-history/discussion-log.md`，达成共识后再写入主规范。
- v0.1 改动：同步更新 `02-design/rtm-v0.1.md` 与 `03-validation/e2e-scenarios-v0.1.md`。
- 归档目录只读，不再追加新条款。
