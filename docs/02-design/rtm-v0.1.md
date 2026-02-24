# RTM v0.1（Requirements Traceability Matrix）

> 目的：把 v0.1 启动文档与主规范条款逐条挂钩，避免“写了很多但不落地”。

## 1. 覆盖说明

- 覆盖级别定义：
  - **Full**：v0.1 已有明确规则 + 数据契约 + 验收场景
  - **Partial**：v0.1 有框架/部分实现，仍需补充
  - **Out**：明确不在 v0.1 范围内
- 关联文档：
  - `docs/01-foundation/mindkernel-v0.1-scope.md`
  - `docs/02-design/rule-table-v0.1.md`
  - `docs/03-validation/e2e-scenarios-v0.1.md`
  - `docs/02-design/state-machines-v0.1.md`
  - `docs/02-design/scheduler-interface-v0.1.md`
  - `docs/02-design/retain-recall-reflect-spec-v0.1.md`
  - `docs/02-design/memory-index-architecture-v0.1.md`
  - `docs/04-prototypes/memory-index-prototype-v0.1.md`
  - `schemas/decision-trace.schema.json`
  - `schemas/audit-event.schema.json`
  - `tools/memory_index_v0_1.py`
  - `tools/validate_memory_index_v0_1.py`

## 2. MR 覆盖

| Requirement | Coverage | 设计落点 | 验证落点 |
|---|---|---|---|
| MR-1 人格连续 + 会话可重置 | Partial | rule-table: Persona Gate；state-machines | E2E-1/E2E-4 |
| MR-2 记忆→经验→认知链路 | Full | v0.1-scope + rule-table + state-machines | E2E-1 |
| MR-3 社会认知冲突下可解释决策 | Partial | decision-trace（gates/reason） | E2E-4 |
| MR-4 反欺骗 + 反偏执双治理 | Partial | rule-table 回滚规则 | E2E-2（偏执红队待补） |
| MR-5 可执行闭环 + 周期复盘 | Partial | scheduler-interface + next_action_at | E2E-3/E2E-5 |
| MR-6 有边界自驱学习 | Partial | uncertain 自动验证预算 | E2E-3 |
| MR-7 关键事件反馈更新认知 | Partial | decision-trace + reinstate 路径 | E2E-5 |

## 3. CR 覆盖

| Requirement | Coverage | 设计落点 | 备注 |
|---|---|---|---|
| CR-1 人格边界硬约束 | Partial | Persona Gate + decision trace gates | override 机制需审批策略 |
| CR-2 记忆是证据非指令 | Full | evidence_refs 强制字段 | 已在 rule-table 和 schema 体现 |
| CR-3 未验证记忆不得参与抽象 | Partial | Memory/Experience 候选态 | 验证阈值细节待定 |
| CR-4 冲动不可越闸门高风险执行 | Full | high risk -> block/escalate | E2E-4 覆盖 |
| CR-5 伪造记忆触发级联回滚 | Full | R-RB-01/R-RB-02 | E2E-2 覆盖 |
| CR-6 反偏执与安全同级 | Out | - | 纳入 v0.2 红队治理 |
| CR-7 cognition 发布需时效字段 | Partial | cognition schema 已有关键字段 | active 前联合校验待实现 |
| CR-8 最小探索预算 | Partial | auto_verify_budget | 周期统计与停滞告警待补 |
| CR-9 uncertain 分级自动验证 | Full | R-UN + scheduler | E2E-3 覆盖 |
| CR-10 认知非二元 | Full | epistemic_state 三态 | 已在 cognition/decision-trace |
| CR-11 未知态细分 | Full | unknown_type 三分流 | E2E-3/E2E-4 |
| CR-12 时间轴驱动遗忘 | Full | next_action_at 调度接口 | E2E-3/E2E-5 |

## 4. FR 覆盖

| Requirement | Coverage | 设计落点 |
|---|---|---|
| FR-1 四类主对象 | Full | schemas + v0.1-scope |
| FR-2 对象状态机可审计 | Full | state-machines + decision-trace |
| FR-3 Memory->Experience->Cognition | Full | rule-table + state-machines |
| FR-4 Persona Conflict Gate | Full | rule-table + decision-trace.gates |
| FR-5 快慢回路合流决策 | Partial | decision-trace 结构预留 |
| FR-6 高风险四重调节 | Partial | risk/cognition/persona gates（social gate 部分） |
| FR-7 注入调查流程 | Partial | 回滚规则具备，取证细节待补 |
| FR-8 级联回滚 | Full | R-RB-01/R-RB-02 |
| FR-9 反例红队与偏执监控 | Out | - |
| FR-10 周期治理作业 | Partial | scheduler 最小版 |
| FR-11 事件显著性评分 | Out | - |
| FR-12 关键事件闭环管理 | Partial | decision trace + e2e-5 |
| FR-13 假设生成与微实验 | Partial | uncertain auto_verify 路径 |
| FR-14 自驱调节器 | Partial | budget + cooldown 字段预留 |
| FR-15 cognition 不确定性字段 | Full | cognition schema |
| FR-16 风险分层不确定性策略 | Full | R-UN-01/02/03 |
| FR-17 按未知类型分流 | Full | R-UN-04/05 |
| FR-18 统一时间轴字段 | Full | common-temporal schema |
| FR-19 到期驱动调度器 | Full | scheduler-interface |
| FR-20 可配置衰减函数 | Partial | 字段在 memory schema，执行策略待实现 |
| FR-21 时间条件状态迁移 + reinstate | Full | state-machines + E2E-5 |

## 5. NFR 覆盖

| Requirement | Coverage | 设计落点 |
|---|---|---|
| NFR-1 可追溯性 | Full | decision-trace + audit-event schema + audit 规则 |
| NFR-2 可解释性 | Full | reason + gates + evidence_refs |
| NFR-3 安全性（检测/隔离/回滚） | Partial | 回滚已覆盖，检测规则待补 |
| NFR-4 可维护性（schema 演进） | Partial | schema 草案已拆分 |
| NFR-5 冲突高发稳定性 | Partial | 需压测数据支持 |
| NFR-6 安全/有用性平衡 | Partial | 需上线指标观测 |
| NFR-7 反馈闭环率 | Partial | 指标定义待补 |
| NFR-8 认知可塑性 | Partial | reinstate 路径已定义 |
| NFR-9 自驱净收益为正 | Out | - |
| NFR-10 不确定性透明度 | Full | uncertain 时强制 decision_mode |
| NFR-11 人工介入效率 | Partial | 升级规则有，阈值监控待补 |
| NFR-12 未知态分流质量 | Partial | 分流规则有，质量指标待补 |
| NFR-13 防空转性 | Full | TTL + budget + ontic 退出策略 |
| NFR-14 遗忘作业效率 | Full | 到期拉取，不走全量扫描 |
| NFR-15 遗忘质量可逆可解释 | Partial | reinstate 已有，误归档指标待补 |

## 6. 记忆层专项追踪（retain / recall / reflect / opinion evolution）

> 目的：把 memory-index 原型能力显式挂到 MR/CR/FR/NFR，避免“有实现、无追踪”。

| 能力 | 覆盖需求 | Coverage | 设计/实现落点 | 验证证据 |
|---|---|---|---|---|
| Retain（`## Retain` 解析 + 入库） | MR-2, CR-2, FR-3, FR-18, NFR-1 | Full | `retain-recall-reflect-spec-v0.1.md` §1；`tools/memory_index_v0_1.py reindex` | `memory-index-prototype-v0.1.md` 用例 + `validate_memory_index_v0_1.py` |
| Recall（fact-pack + source_ref） | MR-2, CR-2, FR-3, FR-17, NFR-1, NFR-2 | Full | `retain-recall-reflect-spec-v0.1.md` §2；`tools/memory_index_v0_1.py recall` | 原型命令回放（`memory-index-prototype-v0.1.md`）+ `validate_recall_quality_v0_1.py` |
| Reflect（建议包 + 可选 writeback） | MR-5, FR-10, FR-12, FR-21, NFR-8, NFR-15 | Partial | `retain-recall-reflect-spec-v0.1.md` §3；`tools/memory_index_v0_1.py reflect --writeback` | `validate_memory_index_v0_1.py` 校验 entities/opinions 写回 |
| Opinion 置信度演化（support/contradict）+ 冲突聚类 | MR-7, CR-3, FR-12, FR-15, NFR-2, NFR-8 | Partial | `retain-recall-reflect-spec-v0.1.md` §5；`tools/memory_index_v0_1.py` opinions_state 更新 + `opinion_conflict_groups` | `validate_memory_index_v0_1.py` + `validate_opinion_conflicts_v0_1.py` |

专项结论（v0.1）：
- Retain / Recall：可作为“记忆证据层”进入主链路，具备最小可验收能力。
- Reflect / Opinion evolution：原型可运行并可校验，但自动调度、回写治理与质量指标尚未闭环，因此维持 Partial。

## 7. v0.1 剩余缺口（进入下轮）

1. 红队偏执监控（FR-9 / CR-6 / NFR-9）
2. 显著性评分与闭环率指标（FR-11 / NFR-7）
3. 高风险四重闸门中的社会闸门细则（FR-6）
4. 探索预算周期统计与“学习停滞事件”告警（CR-8）
5. 调度器实现层的吞吐与延迟基准（NFR-14）
6. Reflect 自动作业接入 scheduler（默认 dry-run + 人工确认写回）
7. Recall 基线持续回归（阈值漂移告警与样本扩充）

## 8. 维护方式

- 新增规则时：必须同时更新本 RTM 表与对应 E2E 场景。
- 任何条款从 Partial -> Full：需要附带“可执行证据”（脚本/日志/测试报告）。
