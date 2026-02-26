# MindKernel v0.1.1-stabilized 发布与观测手册

_更新：2026-02-26（Asia/Shanghai）_

## 1) 目标

将 v0.1.1 稳定化能力（R2~R6）以可复现方式发布，并进入周维度治理观测。

## 2) 发布前检查

```bash
cd /Users/zhengwang/projects/mindkernel

# quick gate
python3 tools/release/release_check_v0_1.py --quick --release-target v0.1.1-r2-r6

# full gate
python3 tools/release/release_check_v0_1.py --release-target v0.1.1-r2-r6-full
```

通过线：
- quick: `16/16 PASS`
- full: `19/19 PASS`

## 3) 版本标记（手动）

```bash
git status --short
# 确保工作区干净

git tag -a v0.1.1-stabilized -m "MindKernel v0.1.1-stabilized"
# 可选：git push origin v0.1.1-stabilized
```

## 4) 核心能力核对

- R2：lease renew + heartbeat
  - `tools/scheduler/scheduler_v0_1.py`
  - `tools/validation/validate_scheduler_lease_renew_v0_1.py`
- R3：temporal verify/revalidate 扩展
  - `tools/scheduler/temporal_governance_worker_v0_1.py`
  - `tools/validation/validate_temporal_verify_revalidate_v0_1.py`
- R5：吞吐/延迟 benchmark
  - `tools/validation/benchmark_scheduler_throughput_v0_1.py`
  - `reports/benchmark/scheduler_baseline_2026-02-26.json`
- R6：向量检索评估
  - `tools/validation/evaluate_vector_retrieval_readiness_v0_1.py`
  - `reports/vector/vector_readiness_2026-02-26.json`（当前 `NO_GO_KEEP_FTS`）

## 5) 周期观测（运行态）

```bash
# 生成周报（建议每周固定时段执行）
python3 tools/validation/generate_weekly_governance_report_v0_1.py --since-days 7
```

重点观察指标：
- success_rate / retry_rate / dead_letter_rate
- due_lag_seconds.p95
- learning_yield_proxy
- release gate pass ratio

## 6) 向量检索触发条件（当前不启用）

满足以下任意组合再重启 vector pilot：
1. `memory_items >= 5000` 且 `query_volume_per_day >= 200`
2. recall accuracy / macro_recall 连续两周跌破质量下限

## 7) 回滚策略

如 v0.1.1 稳定化后出现回归：
1. 回退到 `v0.1.0-usable`
2. 执行 full gate 复核基线
3. 按 R2→R3→R5→R6 顺序逐项恢复并定位问题