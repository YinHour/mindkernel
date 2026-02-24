# MindKernel（心智内核）

> 一个面向智能体的心智系统工程项目：在可审计、可治理前提下，构建 Persona / Cognition / Experience / Memory 闭环。

## 项目定位

`mindkernel` 不只是“记忆增强”，而是一个可执行的心智系统工程：

- **连续性**：人格连续、认知可演化
- **安全性**：防注入、防偏执、防冲动越闸门
- **可解释**：高影响决策可追溯、可复盘
- **可交付**：需求可编号、可验证、可追踪

## 当前阶段（v0.1）

当前已从“纯规范阶段”进入 **规范 + 原型并行**：

- 规范层：MR/CR/FR/NFR、RTM、状态机、调度接口
- 契约层：`memory / experience / cognition / decision-trace / audit-event` schema
- 原型层：
  - Memory→Experience
  - Experience→Cognition（含 Persona Gate）
  - Cognition→DecisionTrace
  - M→E→C→D 一键全链路
- 验证层：关键路径 fixtures + 自动化校验 + smoke report

## 快速开始

```bash
cd ./mindkernel

# 1) 全量关键路径校验
python3 tools/validate_scenarios_v0_1.py

# 1.1) recall 质量基线回放
python3 tools/validate_recall_quality_v0_1.py

# 1.2) memory 导入器回放（幂等 + 错误隔离）
python3 tools/validate_memory_import_v0_1.py

# 1.3) reflect 调度 worker 回放（S7）
python3 tools/validate_scheduler_worker_v0_1.py

# 2) 一键全链路（M→E→C→D）
python3 tools/full_path_v0_1.py run-full-path \
  --memory-file data/fixtures/critical-paths/12-full-path-pass.json \
  --persona-file data/fixtures/critical-paths/12-full-path-pass.json \
  --episode-summary "Planning support signal appears stable and useful." \
  --outcome "candidate generated" \
  --request-ref req://demo/full

# 3) 产出烟测报告（JSON + Markdown）
python3 tools/system_smoke_report_v0_1.py

# 4) 发布前总检（S10）
python3 tools/release_check_v0_1.py --quick --no-strict
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
