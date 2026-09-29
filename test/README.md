# Test Suite (v0.1)

本目录存放关键核心能力的回归测试用例。

## 运行方式

```bash
# 在仓库根目录，使用 Python 3.11+
python3 -m unittest discover -s test -p "test_*.py" -v
```

## 当前覆盖

- `test_daemon_json_output_v0_2.py`：启动诊断不污染标准输出 JSON。
- `test_codex_session_reader_v0_1.py`：限定任务读取、来源、去重、异常输入和结构化回复。
- `test_context_probe_v0_1.py`：离线情境组装的合成边界（包括重复 ID、时效与复核期限），不含真实用户数据。

- `test_reflect_gate_v0_1.py`
  - Agent-first 风险分流策略（low/medium/high + hard rules）
- `test_session_memory_parser_v0_1.py`
  - session->memory 解析与 tool_call 事件 ID 唯一性
- `test_memory_experience_core_v0_1.py`
  - Memory->Experience ingest/promote 核心路径
- `test_persona_confirmation_queue_v0_1.py`
  - 人格冲突确认队列（入队、去重、超时关闭、人工决策、apply-plan、apply-exec 幂等）
- `test_validate_recall_quality_v0_1.py`
  - recall 质量基线校验脚本可运行性与核心阈值断言
- `test_validate_opinion_conflicts_v0_1.py`
  - opinion 冲突聚类与极性判定验证脚本可运行性断言
- `test_validate_memory_import_v0_1.py`
  - memory JSONL 导入器回放验证脚本可运行性断言
- `test_validate_scheduler_worker_v0_1.py`
  - reflect scheduler worker 验证脚本可运行性断言
- `test_validate_scheduler_multi_worker_lock_v0_1.py`
  - 多 worker 租约/锁验证脚本可运行性与无重复领取断言
- `test_validate_temporal_governance_worker_v0_1.py`
  - 遗忘执行层 worker（decay/archive/reinstate-check）验证脚本可运行性断言
- `test_validate_scheduler_lease_renew_v0_1.py`
  - scheduler lease renew（heartbeat）验证脚本可运行性断言
- `test_validate_temporal_verify_revalidate_v0_1.py`
  - temporal worker 的 verify/revalidate 扩展验证脚本可运行性断言
- `test_validate_weekly_governance_report_v0_1.py`
  - 周治理报告生成验证脚本可运行性断言
- `test_validate_scheduler_benchmark_v0_1.py`
  - 调度吞吐基线脚本验证可运行性断言
- `test_validate_vector_readiness_v0_1.py`
  - 向量检索就绪度评估脚本验证可运行性断言
- `test_validate_apply_compensation_v0_1.py`
  - apply 失败补偿验证脚本可运行性断言
- `test_release_check_v0_1.py`
  - release_check quick 模式可运行性断言
