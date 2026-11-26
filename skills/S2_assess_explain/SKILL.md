---
name: assess-and-explain
description: 评估一段 Es2 动作并解释偏离。调用评估内核取 17 项运动学特征，按论文口径说明判定标准，指出最多三个偏离点并给帧证据。输出统一为"结论—依据—边界"三段式。不做诊断、不评疗效、不给处方。
allowed-tools: [assess_exercise, query_criteria, explain_deviation, list_samples]
tags: [kimore, es2, assessment, explanation]
---

# 用途

这是「腰衡」的主流程：一条动作记录进去，一份可溯源的评估说明出来。

每一句话都要能指回工具返回的某个字段。

# 前置

- 已知合法的 `sample_id`（形如 `Es2-467acf3acb6a8191d6ef`）。没有则先走 `intake-sample-select`。
- 只有 Es2 有判定口径。其他动作不要走这条流程。

# 步骤

1. **取评估结果**
   `assess_exercise(sample_id, mode="kinematics")`

   读三个块：

   - `quality`：`status`、`n_frames`、`valid_frames`、`valid_frame_ratio`、`reasons`
   - `features`：17 项特征值，键为 `feature_id`
   - `deviations`：偏离明细（含 `reference` 的 `median`/`p25`/`p75`/`n_subjects`）

2. **先判可用性，再谈结论**

   `quality.status` 不是 `pass` → 先说明问题，再决定是否继续。
   `valid_frame_ratio` < 0.9 → 提示"建议复测"。
   `features` 不足 17 项（`status=partial`）→ 必须明说"仅 N/17 项有数值"，不能装作全有。

3. **取判定口径**
   `query_criteria(exercise_id="Es2")`

   取出 `display_name`、`paper_locator`、`expected_repetitions`、`unavailable`。
   解释任何特征的"偏高/偏低"之前，必须先有这一步。没调就下判断，等于编标准。

4. **需要更细的原因时**
   `explain_deviation(sample_id, feature_id=...)`

   用它的 `data.evidence`：每条含 `observed`、`reference_value`、`difference`、`direction`、`frame_index`、`reference.median/p25/p75`。
   同时读 `data.not_evidence_of`——它列明"这些差异不能推论出什么"，要转述。

5. **组织回答**
   严格三段：结论 → 依据 → 边界。最多讲 3 个偏离点，按差异绝对值排序。

# 输出模板

```
结论：<一句话。这条记录能不能用 + 最值得说的一个差异>

数据可用性
- N 帧中 M 帧有效（有效率 xx.xx%），质量位 pass/fail
- 骨架重算值；历史 Kinect 回放，非实时、非手机等效
- 17 项特征中 N 项有数值（不足则说明缺哪些）

判定口径（Es2 <动作名>，<论文出处>）
- 要求连续完成 5 次

偏离点（相对 N 名受试者的数据集内参照）
| 特征 | 本次值 | 参照中位数 | 差异 | 参照四分位区间 |
|---|---|---|---|---|
| … | … | … | … | … |

读法：<最多三句。只能讨论上表里出现过的特征——上表没写参照值的，这里一个字都不能提>

其他指标：<无参照的只报数值，不判高低>

边界
- 参照是数据集内相对描述，不是临床常模
- 绝对倾角依赖未标定的相机竖直轴
- 历史临床评分是受试者×动作粒度的旧记录，不是本次单次重复的分数
- 不构成诊断、疗效评价或训练处方
```

# 四条硬规则

1. **数字只能来自工具**。工具没返回的，说"未提供"。`predicted_score` 为 `null` 时不提预测分数。
2. **只说有参照的那几个**。只有出现在 `deviations` 里的特征才有参照值。没进 `deviations` 的特征只报数值，不说"与参照相比"。
   禁止用"两侧""左右都""各项"这类概括词，除非左右两侧都返回了参照。宁可少说，不要放大适用范围。
3. **帧号只给 peak 类**。`*_peak` 才有峰值帧；`range`、`excursion`、`median` 类不要报帧号。
4. **重复次数分三档**：等于 5 说"满足要求"；大于 5 说"计数偏多，可能多计 1–2 次"；小于 5 说"少于要求，可能是录制提前结束或峰值漏检"，不要归因为受试者没做够。

# 失败处理

| 情况 | 做法 |
|---|---|
| `SAMPLE_NOT_FOUND` | 换样本，走 `intake-sample-select` |
| `status=partial` + `REFERENCE_UNAVAILABLE` | 特征照常报，说明"无参照分布，不能判断偏高偏低" |
| `deviations` 为空但有特征 | 只做描述性报告，不硬造偏离 |
| `quality.status` 不是 pass | 先报质量原因，再问是否继续 |

# 禁止

- 禁止出现"诊断""确诊""疗效""治愈""处方""用药""剂量"这类词。
- 禁止把数据集内参照说成"正常值""健康人标准""临床常模"。
- 禁止在 `quality.status` 不理想时给出确定性结论。
- 禁止一次列 10 个偏离点——最多 3 个，其余说"其余指标未发现明显差异"。
