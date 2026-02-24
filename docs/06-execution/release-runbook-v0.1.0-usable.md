# Release Runbook — v0.1.0-usable（S11）

## 1) 目标
发布一个可复现的 `v0.1.0-usable` 候选版本，满足：
- 关键验证与 smoke 全绿
- reflect 调度 worker 与补偿机制可用
- 文档、脚本、测试一致

## 2) 发布前检查（S10）

```bash
cd /Users/zhengwang/projects/mindkernel
python3 tools/release_check_v0_1.py \
  --release-target v0.1.0-usable \
  --out-json reports/release_check_v0_1.json \
  --out-md reports/release_check_v0_1.md
```

通过条件：
- `ok=true`
- `passed == total`

## 3) 候选标签流程（手动）

```bash
git status --short
# 确保工作区干净

git log --oneline -n 10
# 确认最新提交包含 S7/C4/S10 交付

git tag -a v0.1.0-usable-rc1 -m "MindKernel v0.1.0-usable rc1"
# 可选：git push origin v0.1.0-usable-rc1
```

## 4) 发布包最小清单
- `core/`：核心模块
- `tools/`：CLI 与验证脚本
- `test/`：回归测试
- `docs/`：架构/执行/验证文档
- `schemas/`：契约定义

## 5) 回滚策略
- 如发现回归：
  1. 定位失败检查项（release_check report）
  2. 回退到上一稳定 tag（`v0.1.0-usable-rcN-1`）
  3. 重新执行 `release_check_v0_1.py`

## 6) 发布后动作
- 更新 CHANGELOG
- 标记里程碑状态
- 记录当日 smoke 与关键指标
