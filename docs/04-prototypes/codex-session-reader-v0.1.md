# Codex 单任务只读读取器 v0.1

状态：2026-09-17 完成 W1-01 技术 review。适配本机 Codex desktop `0.154.0-alpha.6.2` 已观察到的 `response_item/message` 格式。当前工作和剩余瓶颈见[推进记录](../06-execution/iteration-log.md)与[瓶颈记录](../06-execution/bottlenecks.md)。

## 使用

Python 3.11+，仅使用标准库。在仓库根目录执行，先用公开合成样例检查：

```bash
python3 tools/memory/read_codex_session_v0_1.py \
  --session-file data/fixtures/codex-session-v0_1/visible-session.jsonl \
  --thread-id synthetic-mindkernel
```

默认只打印来源、统计和质量问题，不落盘、不打印对话正文。需要保存规范化消息时，显式增加 `--out reports/experiments/week-01/reader.json`。报告可能含私人对话，真实材料保留在 Git 已忽略的 `reports/` 下。

真实读取要求同时指定已选定的 transcript 文件和预期任务 ID；两者不匹配会拒绝读取，不扫描其他任务。源文件持续增长时，用上次报告的 `source.snapshot_bytes` 和 `source.snapshot_sha256` 分别作为 `--max-bytes`、`--expected-sha256`，可重复读取同一前缀。

输出替换指定报告，不累加消息。输出不能等于源文件，也不能经符号链接或硬链接指向源文件。严重错误不会替换旧报告；有行级质量错误时可以导出部分结果供人工检查，但退出码为 2。

## 保留与过滤

- 仅取规范来源 `response_item/message`；事件镜像、推理、工具调用及结果、开发者和系统说明计数后排除。
- 用户纯文本须有 `user.text` 来源标记；已知环境注入排除，混合或未知来源进入质量错误。当前不解读图片、音频及其他内容形态，也不只截取多模态消息中的部分文本冒充完整输入。
- 助手只取 `commentary` 与 `final_answer`，保留角色；助手表达不代表用户认可。
- 普通消息保留源正文的空白；结构化回复展开问题及答案，同时在 `raw_text` 中保存原始载体。
- 保留任务／消息／回合 ID、源行号、来源路径、创建时间与写入时间。按源行顺序输出；来源定位属于具体快照。
- 同 ID、相同内容及来源元数据只计一次；写入时间或行号变化不增加独立证据。同 ID 的修订单独保存到 `revisions` 并报错，首个版本不被覆盖。

## 质量和时间边界

`ok=true` 只表示没有阻断解析质量的错误；仍须查看 `summary.warning_count` 与 `issues`。它不代表完整历史、已导入数据库或学习有效。

| 情况 | 处理 |
| --- | --- |
| 已观察到的助手记录缺少 `create_time`，但写入时间有效 | warning；创建时间保留 null，不以写入时间代替 |
| 用户创建时间缺失／无效，助手已有时间字段却无效，或写入时间缺失 | error；缺失值保留 null，退出 2 |
| 未写完的 JSON 或 UTF-8 末行 | `incomplete_tail`；保留此前完整消息，退出 2，下次刷新重读 |
| 完整行损坏、未知形态、修订冲突、无可见消息 | 明确 error，退出 2，不静默作为成功输入 |
| 任务不符、快照摘要不符、非 Codex 头部 | 拒绝导出，退出 2 |

真实快照 `history_mode=paginated`，只保证当前文件所含记录，不推断为完整账户历史。51 条助手回复没有原始创建时间，不能据日志写入时间计算真实响应延迟或推断过去的状态；案例应以明确用户事件和源顺序定位，保留此限制。

## 验证与后续

```bash
python3 -m unittest test.test_codex_session_reader_v0_1 test.test_session_memory_parser_v0_1 -v
```

本轮 22 项 Codex 测试和 1 项既有 OpenClaw 回归通过。真实固定快照复现 73 条消息（用户 22、助手 51，含 2 条结构化回复），源正文逐条一致，重复导出逐字节一致，源前缀校验不变，879 行均可按保留／排除原因核对。报告有 51 条上述已知时间警告、0 条错误。

与旧一次性预检相比，43 条正文只多保留了首尾空白，均与原始来源核对；不能把这种差异算成新证据。私有结果为 `reports/experiments/week-01/codex-reader-snapshot.json` 和 `codex-reader-validation.json`，不随仓库分发。

当前只提供手动快照读取，没有启用 Hooks、后台监听、运行数据库导入或学习模块。后续案例属于同一开发事件组；独立效果评价需要新的事件和隔离基线。格式发生变化时，先按真实样例补回归，再更新适配器，不放宽未知来源的判断。
