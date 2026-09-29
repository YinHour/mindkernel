# MindKernel（心智内核）

> 构建可审计、可治理、可演化的 Persona / Memory / Experience / Cognition / Decision 闭环智能体心智系统。

**核心理念**：人脑像一间小阁楼——会遗忘、会降噪、有选择地装入有用的东西。 MindKernel 不是"记忆增强"，而是一套可执行的心智工程。

---

## 架构概览

```
Memory → Experience → Cognition → Decision → Action
   ↓           ↓           ↓           ↓
 记忆层      经验层      认知层      决策层
```

| 模块 | 作用 |
|------|------|
| **Memory** | 长期记忆存储；Markdown 索引采用 SQLite FTS5，REST API 提供关键词匹配 |
| **Experience** | 从记忆晋升的经验条目，含反射与验证 |
| **Cognition** | 认知规则，含 epistemic state 推导与置信度 |
| **Decision** | 可执行的决策轨迹，含 active push 推送 |

## 当前阶段

项目以 **v0.1.1-stabilized** 为历史稳定基线，后续已扩展 daemon、MCP/OpenClaw 集成、REST API、知识图谱、主动推送与做梦行动分发。`CHANGELOG.md` 的版本记录至 v0.4.1，另列 Unreleased 实验改动；历史开发进展见 `TODO.md`，不能仅用 v0.1 概括当前仓库。

运行状态需在实际部署环境验证。历史巡检中的“进程存活/未崩溃”不代表业务零错误；历史测试结果与 launchd 安装记录也不代表新克隆环境已经验收。

检索入口目前各有边界：Markdown 索引使用 FTS5；REST `/api/v1/recall` 在最近 `top_k × 10` 条记录中做关键词子串匹配；MCP `mindkernel_recall` 按表列出近期记录。以上入口尚未接入向量混合检索。

2026-09 的个体协作智能实验采用“推进 → review → 更新”流程；开始或恢复工作先读[推进记录](docs/06-execution/iteration-log.md)和[瓶颈记录](docs/06-execution/bottlenecks.md)。目前已完成[Codex 单任务只读读取器](docs/04-prototypes/codex-session-reader-v0.1.md)、首批开发案例与隔离普通记忆基线，已形成[协作情境约定和离线规则探测](docs/04-prototypes/collaboration-context-v0.1.md)，下一步连接标注入口并比较模型回答。数据与回放通过不代表持续学习有效，也未启用后台采集。

## 快速开始

```bash
# 首次安装（Python 3.11+，在仓库根目录执行）
bash scripts/install.sh

# 激活环境
source .venv/bin/activate

# 关键路径校验
python3 tools/validation/validate_scenarios_v0_1.py

# MECD 全链路
python3 tools/pipeline/full_path_v0_1.py run-full-path \
  --memory-file data/fixtures/critical-paths/12-full-path-pass.json \
  --episode-summary "signal appears stable" \
  --outcome "candidate generated"

# 产出烟测报告
python3 tools/validation/system_smoke_report_v0_1.py
```

## 目录结构

| 目录 | 说明 |
|------|------|
| `core/` | 核心逻辑（M→E→C→D 各层引擎） |
| `tools/` | CLI、worker、pipeline 入口 |
| `schemas/` | 数据契约草案 |
| `docs/` | 规范、原型、讨论记录 |
| `data/fixtures/` | 关键路径样例 |
| `data/governance/` | 治理产出（ledger、buffer、报告） |

## 相关文档

- 规范：`docs/01-foundation/requirements-and-architecture.md`
- 需求追踪：`docs/02-design/rtm-v0.1.md`
- 开发进展：`TODO.md`（含历史巡检，注意记录日期与验证范围）
- 版本记录：`CHANGELOG.md`
- OpenClaw 集成：`docs/openclaw-integration.md`
- 完整索引：`docs/contents-map.md`
