# Changelog

## Unreleased — 2026-09-28

- 修正 daemon 启动修复日志污染标准输出 JSON 的问题：诊断写入 stderr，并增加独立临时目录的命令输出回归。

- 新增显式文件／任务白名单的 Codex 只读读取器，保留来源、结构化问答和独立时间字段，报告未知格式、重复及修订。
- 新增 22 项合成测试，保留旧 OpenClaw 入口并通过其回归；真实单任务快照回放复现 73 条消息，助手原始创建时间缺失明确标记。
- 建立实验推进、review、瓶颈与恢复记录；首批开发案例和隔离基线已完成，独立学习效果仍待验证。详见 `docs/06-execution/iteration-log.md`。
- 新增五类协作情境约定、离线规则探测器和 17 项合成边界检查；区分当前、未来、待复核、冲突及排除的信息，真实协作数据保留本地。
- 修正最新明确约束到达复核期限后错误恢复旧约束的问题；带截止时间的临时例外仍按有效期处理。
- 修正两个验证脚本对固定历史样例使用滚动 30 天窗口导致的过期失败；运行系统时间过滤规则不变。

## v0.4.1 — 2026-03-23

### Decision 闭环修复（F1）
- `memory_to_experience()` 新增 `decision_info` 参数
- reflect 调用后 decision 自动写入 `decision_traces` 表
- REST API `/reflect` 和 MCP `mindkernel_reflect` 均已修复
- 新增 `_write_decision_trace()` 函数
- `policy_decision=auto_apply` 时，experience **自动从 candidate 升级为 active**
- 升级时写 audit event，记录 `R-ME-AUTO-APPLY` 规则

### Opinion 自动写入路径（F2）
- 新增 `core/opinion_updater.py` — 自动更新 opinions_v0_1.json
- `memory_to_experience()` 成功后自动调用 `_update_opinions_auto()`
- 按 topic keywords 匹配已有 opinions，累加置信度
- 高频实体自动创建新 opinion 条目

### Opinion 面板刷新
- 8 条高质量 opinions 实时更新
- access_count 真实反映触发次数

## v0.4.0 — 2026-03-23（已完成）

### 知识图谱模块（新增）
- `core/knowledge_graph.py` — 实体关系图谱核心
- `POST /api/v1/knowledge/relations` — 手动添加关系三元组
- `GET /api/v1/knowledge/relations?entity=...` — 查询实体关系（支持 depth=1/2）
- `POST /api/v1/knowledge/extract` — 从文本正则抽取关系（v0.5 升级为 LLM）
- `knowledge_relations` 表：subject/predicate/object/confidence/source

### Opinion 可视化面板（新增）
- `tools/inspect_opinions.py` — 生成 HTML 可视化报告
- `GET /api/v1/opinions/panel` — API 返回面板 HTML
- 红/黄/灰三级置信度颜色编码

---

## v0.3.0 — 2026-03-23

### REST API Server（新增）
- `plugins/api_server/` — FastAPI 服务，端口 18793
- `POST /api/v1/retain` — 写入记忆（含双时间戳 document_date/event_date）
- `GET /api/v1/recall?q=...` — 关键词子串匹配（在最近 `top_k × 10` 条记录中检索，尚未接入向量语义检索）
- `POST /api/v1/reflect` — 触发反思流程
- `GET /api/v1/health` — 健康状态
- `POST /api/v1/prune` — TTL 遗忘策略触发
- `POST /api/v1/adapters/poll` — 触发所有适配器
- API Key 认证（`X-MindKernel-Key` header）
- `run_api_server.sh` — 启动脚本
- `~/Library/LaunchAgents/com.zhengwang.mindkernel.api.plist` — launchd 自启

### TTL 遗忘策略（新增）
- `core/ttl_strategy.py` — Score = recency × frequency，grace_period 保护新记忆
- 配置：`~/.mindkernel/config/ttl_policy.json`
- CLI：`python core/ttl_strategy.py [--apply]`

### 数据源适配器（新增）
- `adapters/browser_bookmark_adapter.py` — Chrome/Edge 书签增量同步
- `adapters/filesystem_adapter.py` — 监控文件夹增量文件
- 状态文件：`~/.mindkernel/state/`

### 双时间戳（部分完成）
- retain payload 新增 `document_date` + `event_date` 字段
- `event_date` 由 reflect 阶段 LLM 推断（待落地）

---

## v0.1.1-stabilized

_Date: 2026-02-26 (Asia/Shanghai)_

### Release gate status
- `v0.1.1-r2-r6` quick gate：**16/16 PASS**。
- `v0.1.1-r2-r6-full` full gate：**19/19 PASS**。
- 证据文件：
  - `reports/release_check_v0_1.json`
  - `reports/release_check_v0_1.md`

### Key additions in v0.1.1-stabilized
- R2（lease renew）：
  - `scheduler_v0_1.py` 新增 `renew_lease` + `renew-lease` CLI。
  - reflect/temporal worker 接入 `--lease-renew-sec` heartbeat 续租能力。
  - 验证：`validate_scheduler_lease_renew_v0_1.py`。
- R3（temporal 扩展）：
  - `temporal_governance_worker_v0_1.py` 扩展动作至 `verify/revalidate/decay/archive/reinstate-check`。
  - 验证：`validate_temporal_verify_revalidate_v0_1.py`。
- R5（吞吐基线）：
  - 新增 `benchmark_scheduler_throughput_v0_1.py` + `validate_scheduler_benchmark_v0_1.py`。
  - 首版基线：throughput `160215.847 jobs/min`、lag p95 `0.483s`、retry `0.0%`（synthetic profile）。
- R6（向量检索评估）：
  - 新增 `evaluate_vector_retrieval_readiness_v0_1.py` + `validate_vector_readiness_v0_1.py`。
  - 当前结论：`NO_GO_KEEP_FTS`（规模/流量未达触发阈值）。
- CI 门禁更新：
  - 主 workflow 追加 R2/R3/R5/R6 验证。
  - `critical-path-validation` 超时窗口提升到 20 分钟。

### Compatibility / rollback
- 兼容性：v0.1.1 以治理能力增强与验证覆盖扩展为主，无 schema 破坏性变更。
- 回滚建议：
  1. 优先回退到 `v0.1.0-usable`；
  2. 重新执行 `release_check_v0_1.py` 验证基线；
  3. 逐项恢复 R2~R6 能力，定位风险来源。

## v0.1.0-usable（release prep）

_Date: 2026-02-25 (Asia/Shanghai)_

### Release gate status
- `v0.1.0-usable` 已完成全量发布前总检：**14/14 PASS**。
- 证据文件：
  - `reports/release_check_v0_1.json`
  - `reports/release_check_v0_1.md`

### Key additions in v0.1.0-usable
- Reflect scheduler worker loop（`tools/scheduler/reflect_scheduler_worker_v0_1.py`）与回归验证（`tools/validation/validate_scheduler_worker_v0_1.py`）。
- Scheduler 多 worker 租约/锁机制（`lease_token` / `lease_expires_at` + 过期回收 + action filter）。
- Temporal governance worker（`tools/scheduler/temporal_governance_worker_v0_1.py`）：支持 `decay/archive/reinstate-check` 执行与审计落账。
- 新增治理验证：`validate_scheduler_multi_worker_lock_v0_1.py`、`validate_temporal_governance_worker_v0_1.py`、`validate_scheduler_workspace_replay_v0_1.py`（真实 workspace 回放 + 恢复路径）。
- Opinion conflict clustering + polarity 增强（`memory_index_v0_1.py`）。
- Recall 质量基线回放验证（`tools/validation/validate_recall_quality_v0_1.py`）。
- Memory JSONL 导入器（`tools/memory/import_memory_objects_v0_1.py`、`core/memory_importer_v0_1.py`）与幂等回放验证。
- Apply compensation 失败补偿链路（`reflect_apply_compensations` + 管理命令）。
- 发布前总检聚合器（`tools/release/release_check_v0_1.py`）与发布手册。

### RC delta（rc1 → rc3）
- `rc1 -> rc2`
  - `52e8eca` docs: refresh quickstart path and expand naming origin note
  - `6e2b1c8` fix: stabilize scheduler worker validation timing
  - `aef0e5a` docs: finalize daily plan and mark S10/S11 rc1 completed
- `rc2 -> rc3`
  - `c530efb` refactor: layer tools into pipeline/memory/scheduler/release and fix references
  - `019d899` refactor: organize validation scripts under `tools/validation`

### Compatibility / rollback
- 兼容性：本次以工具分层与验证路径稳定化为主，无 schema 破坏性变更。
- 回滚建议：若正式发布后发现回归，优先回退到 `v0.1.0-usable-rc3` 或 `v0.1.0-usable-rc2`，并重新执行 `release_check_v0_1.py` 确认基线。
