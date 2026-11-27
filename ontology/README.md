# 「聊愈有方」评估标准本体 v1.0

## 文件清单

| 文件 | 作用 | 谁改 |
| :-- | :-- | :-- |
| `ontology.ttl` | 类、属性、动作与数据集实例 | 人工 |
| `features.ttl` | Es2 的 17 个特征个体 | **脚本生成，勿手改** |
| `shapes.ttl` | SHACL 约束（把评分表的承诺变成可执行规则） | 人工 |
| `examples_good.ttl` | 一条完整合规链路（评估→证据→偏离→方案→技能） | 人工 |
| `examples_bad.ttl` | 故意违规的对照，用来证明约束真的会拦 | 人工 |
| `validation_report.md` | 校验输出，可直接截图进答辩 PPT | 脚本生成 |

## 为什么用 SHACL 而不是提示词

用提示词写「不要下诊断」，模型可能忘、可能被绕过、无法测试。
用 SHACL 写同一条，它是**可执行、可回归、可截图**的：

- 缺临床评分的样本，本体层面就不允许挂 `Deviation`；
- 方案文本里出现「诊断 / 处方 / 治愈 / 确诊」直接判违规；
- 每个特征必须带 `hasSourceLine`，否则不可进入解释。

`examples_bad.ttl` 就是证据：同一套 shapes，合规实例通过、违规实例被拦下 7 条。

## 校验

```powershell
python -m pip install rdflib pyshacl
python tools\validate_ontology.py
```

期望输出：

```
[PASS] 合规实例通过约束
[PASS] 违规实例被拦下
[PASS] 违规原因不少于 4 条
good conforms=True  bad conforms=False  bad violations=7
```

## 17 个特征是怎么来的（半自动）

```
python tools\gen_ontology_features.py          # 重新生成 features.ttl
python tools\gen_ontology_features.py --check  # 只检查是否与契约同步
```

分工是明确的：

- **机器**：从 MCP 真实响应里读 `feature_id` 与 `unit`，保证本体和工具永不失配；
- **人**：证据等级、作者脚本行号、聚合口径、依赖关节、符号约定。

这就是赛题里「半自动本体构建效率优势」那 25% 想看到的东西——不是让模型凭空生成本体，而是**契约驱动生成 + 人工补证据**，并且生成结果可 diff、可回滚。

## 关键设计决定

1. **符号约定单列成类**。作者脚本左侧取负、右侧不取负（`feat_extract_Ex2.m:26/27`），这不是笔误；本体里把「左负右正」显式建模，解释文案才不会左右颠倒。
2. **角度特征必须声明是否依赖竖直轴**。`verticalReferenceIndependent=false` 的特征只能做相对比较，这条写进 shapes，写文案时绕不过去。
3. **重复次数不建模成精确值**。MATLAB `findpeaks` 与 scipy `find_peaks` 在平台段不等价（同一段 6 vs 5），v1 只用于「是否完成 5 次」的二值判断。
4. **数据集必须声明 `captureMode`**。回放就是回放，`offline_replay` 与 `realtime` 分开，杜绝「暗示实时」。

## 扩展到 Es3–Es5 的三步

1. 找到对应 `feat_extract_Ex3/4/5.m`，按同样方式定位行号；
2. 在 `tools\gen_ontology_features.py` 的 `METADATA` 里加条目，并在 `LABELS` 加中文名；
3. 重跑生成脚本 + `validate_ontology.py`，改 `exercise_Es3` 的 `version` 到 `1.0`。

每加一个动作，只需人写 17 行元数据，其余全自动——这是版本演进能持续的原因。

## 与智能体的衔接

智能体不直接读 ttl，而是通过 MCP：

- `query_criteria(exercise_id)` 返回判定标准时，带上 `has_source_line`（对应 `kimore:hasSourceLine`）；
- `explain_deviation` 返回的 `data.evidence[].reference` 对应 `kimore:ReferenceDistribution` 的分位；
- 治疗师修正落库时，先过一遍 shapes，不合规的修正不进入回归队列。

这样「本体」不是文档里的图，而是**卡在每一步前面的检查**。
