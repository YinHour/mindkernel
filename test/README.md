# Test Suite (v0.1)

本目录存放关键核心能力的回归测试用例。

## 运行方式

```bash
cd /Users/zhengwang/projects/mindkernel
python3 -m unittest discover -s test -p "test_*_v0_1.py" -v
```

## 当前覆盖

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
