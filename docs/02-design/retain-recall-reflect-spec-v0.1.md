# Retain / Recall / Reflect Spec v0.1（草案）

## 1. Retain 语法规范

在 Markdown 中新增：

```markdown
## Retain
- W @Peter: ...
- B @warelay: ...
- O(c=0.95) @Peter: ...
- S @ProjectX: ...
```

字段语义：

- 前缀：
  - `W` = world fact
  - `B` = biographical/experience fact
  - `O` = opinion（可带置信度）
  - `S` = summary/observation
- 实体：`@EntityName`（可多个）
- `O(c=0~1)`：观点置信度（可选，默认 0.7）

解析规则（v0.1）：
- 仅解析 `## Retain` 段落中的 bullet。
- 一行一个 fact。
- source 引用格式：`relative/path.md#L<line>`。

## 2. Recall 输入输出契约

### 输入

```json
{
  "query": "planning preference",
  "kind": "O",
  "entity": "Peter",
  "since_days": 30,
  "limit": 20
}
```

### 输出（fact-pack）

```json
{
  "facts": [
    {
      "id": "fact_xxx",
      "kind": "O",
      "content": "...",
      "entities": ["Peter"],
      "confidence": 0.95,
      "source_ref": "memory/2026-02-20.md#L42",
      "observed_date": "2026-02-20"
    }
  ]
}
```

## 3. Reflect 输出规范（v0.1）

默认模式：产出建议包（不写回文件）。

```json
{
  "entity_summaries": [...],
  "opinion_candidates": [...],
  "opinion_conflict_groups": [...],
  "generated_at": "..."
}
```

可选写回（`--writeback`）：
- `bank/entities/<entity>.md`
- `bank/opinions.md`（自动区块）

写回结果会在响应中返回：

```json
{
  "writeback": {
    "enabled": true,
    "paths": ["bank/entities/...", "bank/opinions.md"]
  }
}
```

## 4. 约束与安全

- 不得返回无 `source_ref` 的事实。
- 置信度仅用于排序与提示，不等于决策放行。
- Recall 层不得绕开 Persona Gate 与风险闸门。

## 5. Opinion 置信度演化规则（v0.1.1）

适用范围：`O(...)` 类型 Retain 事实。

- 归一化：对 opinion 文本做轻量 token 归一化，生成 `signature`。
- 匹配键：`(signature, entities)`。
- 判定：
  - 同向（support）：当前 evidence 与已有 opinion 极性一致。
  - 反向（contradict）：当前 evidence 与已有 opinion 极性相反（基于否定词启发式）。
- 更新：
  - support：`confidence += 0.05`（封顶 `0.99`）
  - contradict：`confidence -= 0.08`（保底 `0.05`）
- 审计字段：`support_count`、`contradict_count`、`last_event`、`evidence_refs`。
- reflect 会生成 `opinion_conflict_groups`（按 `entities + topic_signature` 聚类），
  当同簇出现正负极性并存时标记 `has_conflict=true`，建议 `mandatory_review`。

## 6. 版本计划

- v0.1：规则抽取 + 词法 recall + reflect 建议
- v0.1.1：加入 opinion 置信度演化 + writeback
- v0.1.2：加入冲突聚类与极性判定增强（`opinion_conflict_groups`）
- v0.2：更精细置信度更新 + 自动化 reflect 作业
