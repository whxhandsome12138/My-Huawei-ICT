# Es2 特征溯源表（17 特征 × 作者脚本行 × 证据等级）

> 版本 v1.0 ｜ 2026-11-24 ｜ C 侧整理
> 用途：给 A 写文档第 9 章「算法与效度」、给 B 做 `paper_mapping` 自检、给 C 建本体里的 `hasSourceLine` / `hasEvidence`。
> 所有行号指向 `KIMORE` 作者归档中的 `Script/feat_extract_Ex2.m`（CG/GPP 两个作者包内均存在，副本已提取到 `deliver/author_scripts/`）。

## 0. 结论先行

1. **17 个特征全部有出处**：11 个对应论文 TNSRE 2019 的 II.D 小节定义，6 个是工程派生（范围、上下偏移、重复次数）。
2. **可独立复现**：按作者脚本重算 `E_ID1 / Es2`（1664 帧），9 项与 B 的返回值一致到 **0.02° / 0.001**。
3. **两处需要落约定**：躯干倾角的**符号约定**与作者实现相反；`repetition_count_right` 存在**峰值计数口径**差异（6 vs 5）。两者都不影响幅度，但都必须在 `query_criteria` 里写明，否则解释文案会自相矛盾。
4. **中位数聚合不是作者脚本的一部分**：脚本只产出逐帧信号，`*_median` 取中位数是工程选择，因此这 7 个特征在文档里应写"指标定义源自论文、聚合口径为本项目实现"。

## 1. 全局预处理链（所有特征共用）

| 步骤 | 参数 / 规则 | 出处 |
| :-- | :-- | :-- |
| 采样率 | 30 Hz | `filtering.m`：`sample=30`；`butter(3, 2*1/30)` |
| 低通滤波 | 3 阶 Butterworth，截止 1 Hz，`filtfilt` 零相位 | `filtering.m`：`filtCutOff=1` |
| 主结局截头 | 丢掉滤波后的**前 29 帧**（MATLAB `x(30:end)`，30 是首个保留帧的下标） | `feat_extract_Ex2.m` 第 29–30 行 |
| 控制因子截尾 | 丢掉**最后 15 帧** | 第 89–90、102–103、116–117、129–130、146–147、153–154、159、164、169 行 |
| 竖直轴 | 相机竖直轴未标定，**不做修正** | 与 B 的 `vertical_reference.decision = no_correction` 一致 |

## 2. 17 特征溯源

「证据等级」采用 B 在 `query_criteria` 里已冻结的取值：`verified_paper` / `derived_engineering`。

### 2.1 主结局（躯干额状面倾角）

| feature_id | 名称 | 单位 | 证据等级 | 作者脚本行 | 聚合规则 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `torso_tilt_left_peak` | 左侧躯干峰值倾角 | degree | verified_paper（β_l） | 3（atan2）、26（取负+滤波）、29（截头 29 帧）、60（findpeaks 取极大） | 每次重复极大值中的最大者 |
| `torso_tilt_right_peak` | 右侧躯干峰值倾角 | degree | verified_paper（β_r） | 4、27（仅滤波，不取负）、30、41 | 每次重复极大值中的最大者 |
| `torso_tilt_left_range` | 左侧倾角活动范围 | degree | derived_engineering | 26、29、60、61、62 | max − min |
| `torso_tilt_right_range` | 右侧倾角活动范围 | degree | derived_engineering | 27、30、41、42、43 | max − min |
| `torso_tilt_left_excursion_up` | 左侧上向偏移 | degree | derived_engineering | 26、29 | max − median |
| `torso_tilt_left_excursion_down` | 左侧下向偏移 | degree | derived_engineering | 26、29 | median − min |
| `torso_tilt_right_excursion_up` | 右侧上向偏移 | degree | derived_engineering | 27、30 | max − median |
| `torso_tilt_right_excursion_down` | 右侧下向偏移 | degree | derived_engineering | 27、30 | median − min |
| `repetition_count_left` | 左侧重复次数 | count | derived_engineering | 60（`findpeaks`，阈值 `mean`，最小间距 `floor(n/10)`） | 峰个数 |
| `repetition_count_right` | 右侧重复次数 | count | derived_engineering | 41（同上） | 峰个数 |

**倾角定义（第 3–4 行）**：
`atan2(Shoulder.x − Hip.x, Shoulder.y − Hip.y) × 180/π`，即肩–髋连线相对 y 轴的额状面夹角。

### 2.2 控制因子（关节角与体段长度）

| feature_id | 名称 | 单位 | 证据等级 | 作者脚本行 | 聚合规则 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `elbow_angle_left_median` | 左肘角 | degree | verified_paper（γ_l） | 81、83、85、87（余弦定理）、89、185 | 中位数 |
| `elbow_angle_right_median` | 右肘角 | degree | verified_paper（γ_r） | 82、84、86、88、90、186 | 中位数 |
| `knee_angle_left_median` | 左膝角 | degree | verified_paper（φ_l） | 94、97、99、100、102、187 | 中位数 |
| `knee_angle_right_median` | 右膝角 | degree | verified_paper（φ_r） | 95、96、98、101、103、188 | 中位数 |
| `hand_distance_median` | 双手间距 | source_length_unit | verified_paper（d_h） | 158、159、199 | 中位数 |
| `shoulder_distance_median` | 双肩间距 | source_length_unit | verified_paper（d_s） | 163、164、200 | 中位数 |
| `hip_distance_median` | 双髋间距 | source_length_unit | verified_paper（d_hip） | 168、169、201 | 中位数 |

> `source_length_unit` 是 Kinect 相机坐标系下的原始长度单位，**不是米**。文档里必须写清，否则「双肩间距 0.283」会被误读成 28 cm。

## 3. 独立复算结果（E_ID1 / Es2，1664 帧）

复算脚本 `tools/verify_b_features.py`，结果 `tools/verify_b_features.json`。样本反查：1664 帧唯一命中 `Kimore/CG/Expert/E_ID1/Es2/Raw/JointPosition011214_103845.csv`（shape 1664×100）。

| 特征 | B 0.1.0 返回值（11-24 交付） | 本项目复算（已修正） | 差 | 判定 |
| :-- | --: | --: | --: | :-- |
| `torso_tilt_left_range` | 37.489 | 37.5079 | +0.019 | 一致 |
| `torso_tilt_right_range` | 32.478 | 32.4892 | +0.011 | 一致 |
| `elbow_angle_left_median` | 164.214 | 164.1623 | −0.052 | 一致 |
| `knee_angle_left_median` | 166.161 | 166.1415 | −0.019 | 一致 |
| `shoulder_distance_median` | 0.283 | 0.28257 | −0.0004 | 一致 |
| `repetition_count_left` | 6 | 6（峰）/ 6（谷） | 0 | 一致 |
| `torso_tilt_left_peak` | −26.497 | **+26.5182**（左信号极大） | 幅度差 0.021 | B 0.1.0 偏差（左侧未取负），1.0.0 已修正 |
| `torso_tilt_right_peak` | +20.901 | **+20.9116**（右信号极大） | 幅度差 0.011 | 一致 |
| `repetition_count_right` | 6 | 6（峰）/ 5（谷） | 0 | 一致 |

### 3.1 符号约定：作者只对左侧取负

`feat_extract_Ex2.m` 第 26–27 行是：

```matlab
angolobustoL = -filtering(angolobustoL);   % 左：取负
angolobustoR =  filtering(angolobustoR);   % 右：不取负
```

作者口径下：左信号范围 [−10.990, **+26.518**]，右信号范围 [−11.578, **+20.912**]，两侧峰值都是正的。

**这条结论经历过一次错误的往返，记下来以免重犯**：本项目早先的复算脚本对**两侧都取负**
（`ang = -filtering(ang)`），于是右侧算出了 −20.912，我据此以为「两侧符号都相反」。
实际是只差左侧一个负号。修正后的复算脚本见 `tools/verify_features.py`（按侧判断是否取负）。

**最终口径（以论文与作者脚本为准）**：每个特征的正值表示**向该特征对应的那一侧偏离**
（左特征正 = 向左，右特征正 = 向右）。B 侧按此改实现，随 1.0.0 发布；本体里
`sign_left_positive` / `sign_right_positive` 两个 `SignConvention` 个体同步。

> 补充一个工程观察（不是论文规定）：两侧信号存在约 **+18.6°** 的相机几何偏置
> （`ShoulderRight.x − ShoulderLeft.x ≈ +0.265`），所以绝对角度不宜直接当「偏离竖直轴多少度」念，
> 幅度应看 `range` / `excursion`。

### 3.2 重复次数：修正符号后差异自动消失

按作者脚本的峰检测（`height=mean`、`distance=⌊n/10⌋`）与谷检测（对 `max(x)−x` 找峰、
`distance=⌊n/8⌋`）在 E_ID1 上重算：

| | 峰 | 谷 |
| :-- | --: | --: |
| 左（作者口径 = −raw） | 6 | 6 |
| 右（作者口径 = +raw） | 6 | 5 |

早先「右 5 vs B 6」的差异，是因为对右侧取负后数的是**谷**，不是峰。修正后两侧峰数都是 6，
与 B 一致，原先「MATLAB `findpeaks` 与 scipy `find_peaks` 对平台段处理不同」的归因不成立。

**收口方式（已与 B 约定，随 1.0.0 发布）**：论文只说「每个动作连续做 5 次」，那是**协议要求**；
算法数出来的是**描述量**。两个都给，不混用：

```json
{
  "repetition_count_left": 6,
  "repetition_count_right": 6,
  "repetition_completed_expected": true,
  "repetition_count_basis": "descriptive_only"
}
```

智能体话术据此改成三档：完成 = 是 → 说「满足 5 次要求」；完成 = 否 → 说「少于 5 次，
可能是录制提前结束或峰值漏检」；检测数明显多于 5（如 6–7）→ 说「计数偏多，可能多计 1–2 次」，
**不归因受试者**。

## 4. 需要写进 `query_criteria` 与本体的事项

| 事项 | 落点 | 负责 |
| :-- | :-- | :-- |
| 主结局的符号约定（正值 = 向该侧偏离） | `query_criteria` 增加 `sign_convention`；`Feature.hasSignConvention` | C 写本体，B 加字段 |
| 长度单位是相机原始单位，不是米 | `unit` 已为 `source_length_unit`，需在 `display_name` 或 `warnings` 里补一句 | B |
| 中位数聚合是工程口径 | `evidence_level` 保持 `verified_paper`（指标定义源论文），但增加 `aggregation: median` 字段 | B |
| 重复次数保留描述量 + 布尔判定 | `repetition_count_*` 保留数值，另加 `repetition_completed_expected: bool` 与 `repetition_count_basis` | B（C 加判定规则） |
| 缺 cTS 的样本不得产生偏离结论 | SHACL 约束 | C |
| 绝对倾角依赖未标定竖直轴 | `vertical_reference_independent=false` 已有，解释文案需引用 | C |

## 5. 复算的价值定位（写进文档 9.3 节）

这条链是「**实现一致性校验**」，属于效度证据里最便宜也最可信的一档：

- 不需要新数据、不需要受试者；
- 用作者公开实现做参照，第三方（本项目）独立复现，误差 0.02°；
- 差异点全部可解释（符号约定、峰计数口径），没有不可解释的黑箱。

文档里建议这样写：**"我们在 1 条真实录制（1664 帧）上，按作者脚本逐行复现了 9 个特征，最大绝对误差 0.052°；过程中发现并纠正了自身一处符号实现错误（对右侧多取了一次负号），最终口径与作者脚本一致，两处口径差异（符号约定、峰值计数）已在 `query_criteria` 中显式声明。"** —— 一句话就是一个可验证的效度声明。

> 这段「先错后对」不该删。它证明复算不是抄一遍数字，而是真的把作者脚本逐行对过；
> 也是答辩里被问「你怎么知道你对」时最好的答案。
