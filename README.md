# MindKernel（心智内核）

> 一个面向智能体的心智系统工程项目：在可审计、可治理前提下，构建 Persona / Cognition / Experience / Memory 闭环。

## 项目定位

> “你要知道，我认为人的脑子本来像一间空空的小阁楼，应该有选择地把一些家具装进去。只有傻瓜才会把他碰到的各种各样的破烂杂碎一古脑儿装进去。这样一来，那些对他有用的知识反而被挤了出来；或者，最多不过是和许多其他的东西掺杂在一起。因此，在取用的时候也就感到困难了。所以一个会工作的人，在他选择要把一些东西装进他的那间小阁楼似的头脑中去的时候，他确实是非常仔细小心的。除了工作中有用的工具以外，他什么也不带进去，而这些工具又样样具备，有条有理。如果认为这间小阁楼的墙壁富有弹性，可以任意伸缩，那就错了。请相信我的话，总有一天，当你增加新知识的时候，你就会把以前所熟习的东西忘了。所以最要紧的是，不要让一些无用的知识把有用的挤出去。” —— 这段话是福尔摩斯大侦探刚出场的时候说的。
> 因此在遇到这种问题的时候，一个明显的认知就是，人类不是靠事无巨细的把所有的信息都记住来获取认知的，心智的主要特点-或者说功能实际上是遗忘，这是一个典型的降噪过程。

`mindkernel` 不只是“记忆增强”，而是一个可执行的心智系统工程：

- **连续性**：人格连续、认知可演化
- **安全性**：防注入、防偏执、防冲动越闸门
- **可解释**：高影响决策可追溯、可复盘
- **可交付**：需求可编号、可验证、可追踪

## 当前阶段（v0.1 / stabilized）

当前已从“纯规范阶段”进入 **规范 + 原型并行**，并完成 `v0.1.1` 稳定化收口：

- 规范层：MR/CR/FR/NFR、RTM、状态机、调度接口
- 契约层：`memory / experience / cognition / decision-trace / audit-event` schema
- 原型层：
  - Memory→Experience
  - Experience→Cognition（含 Persona Gate）
  - Cognition→DecisionTrace
  - M→E→C→D 一键全链路
- 验证层：关键路径 fixtures + 自动化校验 + smoke report
- 稳定化层：R1~R6 全部完成（weekly report、lease renew、temporal verify/revalidate、benchmark、vector readiness 评估）

## 快速开始

```bash
cd ./mindkernel

# 1) 全量关键路径校验
python3 tools/validation/validate_scenarios_v0_1.py

# 1.1) recall 质量基线回放
python3 tools/validation/validate_recall_quality_v0_1.py

# 1.2) memory 导入器回放（幂等 + 错误隔离）
python3 tools/validation/validate_memory_import_v0_1.py

# 1.3) reflect 调度 worker 回放（S7）
python3 tools/validation/validate_scheduler_worker_v0_1.py

# 1.4) 并发与治理执行层验证
python3 tools/validation/validate_scheduler_multi_worker_lock_v0_1.py
python3 tools/validation/validate_temporal_governance_worker_v0_1.py
python3 tools/validation/validate_scheduler_workspace_replay_v0_1.py

# 1.5) 周治理报告（R1）
python3 tools/validation/generate_weekly_governance_report_v0_1.py

# 1.6) 稳定化专项（R5/R6）
python3 tools/validation/benchmark_scheduler_throughput_v0_1.py
python3 tools/validation/evaluate_vector_retrieval_readiness_v0_1.py

# 2) 一键全链路（M→E→C→D）
python3 tools/pipeline/full_path_v0_1.py run-full-path \
  --memory-file data/fixtures/critical-paths/12-full-path-pass.json \
  --persona-file data/fixtures/critical-paths/12-full-path-pass.json \
  --episode-summary "Planning support signal appears stable and useful." \
  --outcome "candidate generated" \
  --request-ref req://demo/full

# 3) 产出烟测报告（JSON + Markdown）
python3 tools/validation/system_smoke_report_v0_1.py

# 4) 发布前总检（S10）
python3 tools/release/release_check_v0_1.py --quick --no-strict
```

## 推荐阅读顺序

1. `docs/01-foundation/requirements-and-architecture.md`（主规范）
2. `docs/02-design/rtm-v0.1.md`（需求追踪）
3. `docs/02-design/state-machines-v0.1.md`（状态机）
4. `docs/04-prototypes/full-path-prototype-v0.1.md`（一体化原型）
5. `docs/03-validation/validation-critical-paths-v0.1.md`（验证覆盖）
6. `docs/contents-map.md`（完整索引）

## 目录结构

- `docs/`：规范、原型说明、讨论记录
- `schemas/`：数据契约草案
- `core/`：验证通过后的核心逻辑模块（可复用，保持干净）
- `tools/`：CLI 与原型入口（尽量薄壳）
- `test/`：关键用例回归测试
- `data/fixtures/`：关键路径样例
- `archive/`：历史草案（只读）

## 贡献指南

请先阅读：`CONTRIBUTING.md`

项目命名说明见：`docs/05-history/name-origin.md`。
