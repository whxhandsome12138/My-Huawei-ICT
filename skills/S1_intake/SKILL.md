---
name: intake-sample-select
description: 接待与样本定位。判断用户想评估哪一段动作记录，确认 sample_id 合法且可评估，必要时列出候选样本让用户挑。用于对话开场、用户没给 ID、或 ID 报错需要换样本时。
allowed-tools: [list_samples, assess_exercise, query_criteria]
tags: [kimore, intake, sample-selection]
---

# 用途

把"我想看看我的康复动作"这类模糊请求，收敛成一条确定的 `sample_id`，再交给评估流程。

只做定位，不做评估结论。评估与解释交给 `assess-and-explain`。

# 适用与不适用

适用：

- 用户没给 `sample_id`，或只说"帮我看看最近的记录"
- 用户给的 ID 报错，需要换一条
- 用户问"有哪些记录可以评估"

不适用：

- 已经拿到合法 `sample_id` 且用户明确要评估 → 直接进入 `assess-and-explain`
- 用户要对比多条记录 → 进入 `plan-and-compare`

# 步骤

1. **判断是否已有 ID**
   - 用户给了形如 `Es2-<20 位十六进制>` 的字符串 → 直接进入第 3 步校验。
   - 没给 → 调 `list_samples`（不传 `exercise_id` 时返回全部，`limit` 默认 5）取候选。

2. **呈现候选**
   - 只说 3–5 条，每条给出 `sample_id`、动作编号、帧数、质量位。
   - 不要一次列 20 条，也不要只给一个 ID 让用户猜。

3. **校验合法性**
   - 格式必须是 `^Es[1-5]-[0-9a-f]{20}$`。不符合 → 按 `INVALID_ARGUMENT` 话术回复。
   - 动作编号不是 `Es2` → 按 `UNSUPPORTED_EXERCISE` 话术回复，说明当前只开放 Es2。

4. **试探一次可用性**
   - 用 `assess_exercise(sample_id, mode="kinematics")` 轻探一次。
   - 返回 `status=error` 且 `error.code=SAMPLE_NOT_FOUND` → 回到第 1 步换样本。
   - 返回 `status=ok` 或 `partial` → 定位成功。

5. **移交**
   - 一句话确认："已定位到 `Es2-xxxx`，587 帧，质量 pass。下面做评估。"
   - 随后按 `assess-and-explain` 的流程继续，不要重复消耗一次工具调用。

# 输出模板

```
已找到可评估的记录：

| sample_id | 动作 | 帧数 | 质量 |
|---|---|---|---|
| Es2-467a…d6ef | Es2 躯干侧倾 | 1664 | pass |
| Es2-fbab…4233 | Es2 躯干侧倾 | 587  | pass |

要评哪一条？回复编号或完整 ID 即可。
```

# 失败处理

| 情况 | 回复要点 |
|---|---|
| `SAMPLE_NOT_FOUND` | 这条记录不可用，换一条；不要猜"可能被删了" |
| `INVALID_ARGUMENT` | ID 格式不对，形如 `Es2-` 加 20 位十六进制 |
| `UNSUPPORTED_EXERCISE` | 目前只支持 Es2，其他动作暂未开放 |
| `list_samples` 返回空 | 说明当前没有可评估记录，不要编造 ID |

# 禁止

- 不要推荐不存在的 `sample_id`。所有 ID 必须来自 `list_samples` 的返回。
- 不要用"你这段时间练得不错"这类评价性开场，定位阶段不做任何判断。
- 不要在没调用工具的情况下说"我看到你有 5 条记录"。
