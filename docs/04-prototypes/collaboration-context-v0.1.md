# 协作情境最小约定 v0.1（实验草案）

日期：2026-09-28；2026-09-30 增补来源适配。对应 W1-03 / B06。目的：在自然语言检索之外显式保留与共同任务有关的信息，先排除信息遗漏与过期造成的失败。字段由人工从已授权材料标注，自动提取、生产接口和参数训练尚未实现。

## 1. 比较范围与选择

可选方法包括：继续按文本相似度检索、按类型和时效选择结构化情境、让模型自行总结侧写。2026-09-28 探测采用第二种：普通检索已经漏掉明确预算，固定规则容易追溯遗漏原因；自动侧写又会额外引入提取正确性问题。保留旧基线，不更换模型，不执行模型回放。

这里只选择共同任务的情境，不改写智能体自身 Persona，也不把短期情况变成长期人格。

## 2. 五类信息

| kind | 信息 | 主要边界 |
| --- | --- | --- |
| intent | 当前意愿 | 表达改变时更新；需有结束或复核条件 |
| constraint | 明确约束 | 同一范围有效时必选，不依赖相似度排名 |
| availability | 临时可用性 | 必须有时间范围，保留“可能”等不确定性 |
| task_state | 任务状态观察 | 历史或摘要来源进入待复核，不能等同当前事实 |
| artifact | 产物引用 | 只传入路径、证据和状态，不自动读取目标文件 |

## 3. 一条记录

| 字段 | 含义 |
| --- | --- |
| id / kind / key / value | 唯一标识、信息类型、人工定义的语义键、保留条件与不确定性的表述 |
| scope.project / scope.task | 精确项目和可选任务范围；null task 表示该项目范围 |
| source.ref / source.event_id | 可定位来源及事件 ID；不同载体不自动增加独立样本数 |
| source.authority | user_explicit / artifact_observation / history_summary / assistant_inference |
| source.created_at / source.available_at | 原表达或观察发生时间、来源可获得时间的可核验上界，均需时区；后者不知道准确时刻时采用保守上界并注明依据，不能默认等于事件发生时间 |
| recorded_at | 本轮整理记录的实际时间；历史重建可以晚于回放截止点，须明确标注为事后重建 |
| valid_from / valid_until | 生效范围，右边界排除；临时信息必须有截止时间 |
| recheck_after | 到该时点进入待复核；长期约束可为 null，但仍受新表达覆盖 |
| supersedes | 人工核实的永久取代关系，默认空；不能把一次临时例外标成永久撤销 |

标注 created_at 或 available_at 缺失、无时区、矛盾的记录不进入有效输入。原文不存在精确期限时，约定的复核日期必须标明为实验策略，不能写成用户承诺。recorded_at 只是审计时间，不能伪造在线系统当时已经构造了该记录。

## 4. 选择流程与输出

请求提供 `as_of`、`horizon`、项目和任务。`as_of` 是证据截止点，`horizon` 只用于规划已知的未来安排，不能开放未来证据。`horizon >= as_of`，默认相等。

1. 校验记录与时区。重复字符串记录 ID 在排除无效记录之前报错；无效记录不能隐藏 ID 冲突。引用同一事件不意味着多个独立事件。
2. 仅使用 source.created_at、source.available_at 均不晚于 as_of 的记录。recorded_at 保持实际整理时间，不当作历史可见性证据。
3. 按项目和任务精确匹配。其他项目或其他具体任务的信息排除。
4. 只用当时已知且已生效的明确用户修订处理 supersedes；只允许同类型、同语义键和完全相同范围。被明确永久取代的记录不会因新记录到期而复活。
5. 时间区间采用 `[valid_from, valid_until)`。尚未生效但落入 horizon 的安排进入 upcoming，已过期进入 excluded。不据一次安排产生周期规则。
6. history_summary、assistant_inference 以及未经用户明确确认的人类意愿、约束、可用性进入 needs_recheck。这一分组保留内容和来源，表达待查证，不能当硬约束。任务状态与产物引用必须提供 recheck_after。
7. 对完全相同类型、key 和 scope 的其余候选，以明确用户表达优先；同等级采用最新 created_at。同一最新时点存在不同值时进入 conflicts，不任意选一个。先确定优先关系，再将已到 recheck_after 的胜出记录放入 needs_recheck，不能因此恢复旧约束；有截止时间的临时例外过期后，未被永久取代的原约束仍可恢复。不同范围的记录并列保留，不在本轮发明跨范围覆盖。
8. 输出 current、upcoming、needs_recheck、conflicts、excluded 五组；excluded 保留 ID 与原因，其余保留完整来源。未来安排与当前约束分组解析，使用者不能把 upcoming 直接当成当天不可用。

复核期限可以早于生效日期，例如未来安排需要事先重新确认。落入规划范围且已到复核期限时进入 needs_recheck，保留原生效区间，不当作当前事实；复核期未到时仍进入 upcoming。recheck_after 与 valid_from 不要求按先后排序。

排序仅保证重跑一致，不是置信度或重要性排名。本轮没有输入长度预算；若未来做截断，必须报告约束是否被截断，不能静默丢掉。

## 5. 必检边界

| 情境 | 预期 |
| --- | --- |
| 相似度检索漏掉已确认预算 | 有效的 constraint 仍进入 current |
| 临时状态刚好到期 | 从 current / upcoming 移除，保留 excluded 原因 |
| 新用户表达修订相同范围 | 选择最新明确表达；更新推测不能覆盖用户表达 |
| 最新明确修订已到复核期限 | 新修订进入 needs_recheck，旧约束不能恢复为 current |
| 历史任务状态未复核 | 进入 needs_recheck，输出不冒充当前状态 |
| 原事件很早但来源后来才出现 | available_at 超过截止点则排除，避免泄漏 |
| 已知未来安排进入规划 | 可进入 upcoming；horizon 不允许带入未来才出现的证据 |
| 被永久取代的旧约束 | 新记录失效后也不恢复旧约束，需新的明确表达 |
| 其他项目、同时间矛盾、来源缺失 | 分别排除、报告冲突、报告无效记录 |

## 6. 评估与接续

合成检查验证规则；历史 C03 / C06 材料只用于开发输入重建。标签和规则由看过旧结果的同一助手设计，所以没有独立留出结论。历史任务摘要仍保留较低证据级别；本轮不重新读取其他任务或计算机历史。

2026-09-28 探测完成条件是五类信息可表达、边界可检查、选择原因和来源可追溯。后续来源适配与同条件开发对照已于 2026-09-30 执行，发现未标注主题的修订遗漏和潜在额外提问，W1-03 整项仍待修正。新自然事件判断与真实反馈尚缺；B06 和 B02 均不能因合成检查通过而关闭。


## 7. 运行合成规则检查

公开的[参考探测器](../../tools/experiments/probe_context_v0_1.py)与[19 项合成检查](../../test/test_context_probe_v0_1.py)不含真实对话，属于离线实验工具，尚未接入运行系统。Python 3.11+ 下在仓库根目录运行：

```bash
python3 -m unittest discover -s test -p 'test_context_probe_v0_1.py' -v
```

真实输入、用户来源和组装结果留在已忽略的 `reports/experiments/`，不随代码公开。原实验冻结副本继续保留，以便核对当时结果。

## 8. 从读取器结果绑定来源

[来源适配器](../../tools/experiments/assemble_context_v0_1.py)提供纯函数接口，无文件发现、网络访问或运行数据库写入：

```python
from tools.experiments.assemble_context_v0_1 import assemble_from_sources

result = assemble_from_sources(
    reader_report, annotations,
    expected_thread_id="synthetic-mindkernel",
    as_of="2026-09-28T00:00:00Z", project="MindKernel",
    observations=observations,  # 默认为空；非用户来源必须显式提供
)
```

- `reader_report` 是成功的 `codex-visible-session/v0.1` 导出；明确任务 ID 必须匹配。调用者负责按保存的校验值冻结并检查输入文件，适配器不重新打开原 transcript。
- `annotations` 是本约定的人工记录列表。用户来源按事件 ID 对应导出消息，并检查任务、角色、完整原文引用、来源位置和时间；结构化回复使用 `raw_text`，普通消息使用 `text`，只忽略引用首尾空白。不会自动推断或改写 `value`、有效期和取代关系。
- 用户记录的 `source.created_at` 必须对应消息创建时间；`available_at` 对应创建时间和源写入时间的较晚者，兼容毫秒写入时间的截断。原始时间未知时排除；人工标注时间独立保留。
- 非用户来源使用 `observations` 列表，每条含 `event_id`、`ref`、`authority`、`created_at`、`available_at`、`content` 和 `sha256`。`content` 是显式传入的完整 UTF-8 文本容器；其 SHA-256 必须同时匹配 observation 和原标注的 `source.sha256`（历史容器也可用 `container_sha256`）。来源元数据与时间须一致。适配器不跟随 `ref` 打开文件。
- 引用无法对应、说话者不符、未知时间或内容校验不符的记录进入 `source_excluded`，并加入情境的 `excluded`；无效导出、任务白名单不符、重复消息／观察／标注 ID 抛出 `ValueError`，不猜测选取哪个来源。

输出包含 `context`（既有五组）、`bindings`（通过来源核对的审计映射）、`source_excluded` 和快照元数据。`bindings` 只说明来源核对通过，可能包含晚于案例截止点的来源；它不是可用事实集合，不应直接送入模型。后续模型输入须从 `context` 的适用分组构造，并将待复核与冲突明确标注；审计项和排除项不作为事实。

内容校验仅证明材料与保存证据一致，不证明人工语义标注正确，也不证明摘要原始发布时间。历史摘要仍进入待复核，旧状态仍按复核期限失效。此接口是离线实验适配，不自动提取侧写。

运行[来源边界检查](../../test/test_context_source_adapter_v0_1.py)：

```bash
python3 -m unittest discover -s test -p 'test_context_source_adapter_v0_1.py' -v
```

## 9. 同条件开发对照后的适用限制（2026-09-30）

来源核对及适用分组只保证已提供的标注经过相应规则处理，不保证候选池里的所有较新修订都已标注。三对新回答中，明确预算的覆盖改善，但用普通检索补足历史时仍可能选入已经需要重估的旧安排，回答再把它提升为当前偏好。

同主题修订链的期望输入与 11 个合成边界现已冻结，区别不同字段及作用范围，见[字段修订约定](context-revision-selection-v0.1.md)。选择前检查已于 2026-10-26 实现并通过工程验证，下一单元进行小规模新回答对照，详见[执行计划第 9 节](../superpowers/plans/2026-09-17-week1-codex-data-experiment-plan.md#9-2026-09-30-同条件对照结果与下一单元)。这是待验证的修正要求，现有适配器没有自动语义识别或完整修订覆盖能力；不能仅因输入引用真实就声明当前理解正确。
