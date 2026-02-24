# Memory Index Prototype v0.1（retain/recall/reflect）

> 目标：在 Markdown 规范源上提供离线索引与回忆能力。

## 1. 脚本

- `tools/memory_index_v0_1.py`

## 2. 支持命令

- `init-db`
- `reindex`
- `recall`
- `reflect`
- `list-opinions-state`

## 3. 示例（使用 fixture 工作区）

```bash
cd /Users/zhengwang/projects/mindkernel

python3 tools/memory_index_v0_1.py \
  --workspace data/fixtures/memory-workspace \
  --db data/memory_index_demo.sqlite \
  reindex

python3 tools/memory_index_v0_1.py \
  --workspace data/fixtures/memory-workspace \
  --db data/memory_index_demo.sqlite \
  recall --query "MindKernel" --limit 10

python3 tools/memory_index_v0_1.py \
  --workspace data/fixtures/memory-workspace \
  --db data/memory_index_demo.sqlite \
  reflect --since-days 30 --writeback
```

`reflect` 输出中新增：
- `opinion_conflict_groups`：按 `entities + topic_signature` 聚类的冲突簇
- 每个簇包含 `polarity_counts`、`has_conflict`、`conflict_score`、`recommended_action`

当 `has_conflict=true` 时，建议动作为 `mandatory_review`，可直接接入确认队列。

## 4. 反思输出与写回行为

当使用 `reflect --writeback`：
- 生成 `bank/entities/<slug>.md`
- 更新 `bank/opinions.md` 的自动区块
- 更新 `opinions_state`（置信度演化）

演化规则（v0.1）：
- 同向证据：`confidence += 0.05`（上限 0.99）
- 反向证据：`confidence -= 0.08`（下限 0.05）

可查看状态：

```bash
python3 tools/memory_index_v0_1.py --db data/memory_index_demo.sqlite list-opinions-state
```

## 5. 验证脚本

```bash
python3 tools/validate_memory_index_v0_1.py
```

> v0.1 仍是可解释规则版本，暂不引入复杂冲突合并。
