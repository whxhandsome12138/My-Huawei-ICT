# 「聊愈有方」Skill 包 S1–S5

五个可复用工作流模板，对应 Nexent 的 Skill 机制。目的是把「动作评估」从模型的自由发挥，变成**固定输入、固定步骤、固定输出结构**的流程。

## 一览

| 编号 | 目录 | name | 干什么 | 挂在哪 |
|---|---|---|---|---|
| S1 | `S1_intake` | `intake-sample-select` | 收到模糊请求，收敛成一条合法 `sample_id` | 主控 Agent（对话入口） |
| S2 | `S2_assess_explain` | `assess-and-explain` | 评估 + 解释偏离，输出「结论—依据—边界」 | 评估 Agent |
| S3 | `S3_plan_compare` | `plan-and-compare` | 多条记录同口径对照，先可比性后数字 | 方案 Agent |
| S4 | `S4_followup` | `followup-trend` | 长期随访，分清「人的变化」与「采集的差异」 | 随访 Agent |
| S5 | `S5_override` | `clinician-override` | 治疗师改判 → 结构化修正条目（可进化闭环入口） | 主控 Agent / 治疗师端 |

## 上传

Nexent → 左侧 **Skill 仓库** → 上传。两种方式都支持：

- **单个文件**：直接传对应的 `SKILL.md`
- **打包**：传 `dist\S1.zip` … `S5.zip`（`SKILL.md` 已在压缩包根目录）

上传后技能处于草稿态（`version=0`），可立即在智能体里挂载试用；调试满意后再发布（`version>=1`，参数锁定）。

## 与评分项的对应

| 评分项 | 对应 |
|---|---|
| 能力沉淀（可复用 Skill 工作流模板） | S1–S5 本身就是交付物；每个都有固定输出模板 |
| 智能体编排与 MCP 深度集成 | Skill 通过 `allowed-tools` 显式声明依赖哪几个 MCP 工具，编排关系可读 |
| 决策可溯源 | S2 要求"解释前先取判定口径"，S5 要求"每条修正附支撑证据" |
| 业务价值（沉睡数据激活） | S4 把单次评估扩展成随访链路 |

## 三条贯穿所有 Skill 的红线

1. **数字只能来自工具**。工具没返回就说「未提供」，不推测、不补算。
2. **不诊断、不评疗效、不给处方**。出现「诊断/确诊/疗效/治愈/处方/用药/剂量」即违规。
3. **参照不是常模**。数据集内相对描述 ≠ 临床正常值，任何「偏高/偏低」都要说明相对于谁。

## 需要人工确认的一处

`S2` 与 `S3` 里引用了动作名「Es2 躯干侧倾（双臂上举持杆）」，来自 `query_criteria` 的 `display_name`。需与论文原文核对：若论文未提「持杆」，则应修改工具的 `display_name`，而不是改 Skill。

## 打包

```powershell
cd F:\deepseek-harness\华为ICT\deliver\skills
foreach ($s in 'S1_intake','S2_assess_explain','S3_plan_compare','S4_followup','S5_override') {
  $n = $s.Split('_')[0]
  Compress-Archive -Path "$s\*" -DestinationPath "dist\$n.zip" -Force
}
```
