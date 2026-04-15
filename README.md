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
| **Memory** | 长期记忆存储，向量+关键词混合检索 |
| **Experience** | 从记忆晋升的经验条目，含反射与验证 |
| **Cognition** | 认知规则，含 epistemic state 推导与置信度 |
| **Decision** | 可执行的决策轨迹，含 active push 推送 |

## 当前阶段

**v0.1**（stabilized）— MECD 全链路闭环完成，daemon 零错误运行 47+ 天。

## 快速开始

```bash
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
- 完整索引：`docs/contents-map.md`
