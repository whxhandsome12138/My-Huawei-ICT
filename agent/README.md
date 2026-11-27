# 智能体

| 文件 | 说明 |
| :-- | :-- |
| `system-prompt.md` | 完整系统提示词，直接贴进 Nexent「模型与提示词 → 系统提示词」 |
| `build_agent_package.py` | 生成配置包的脚本（见 `../tools/build_agent_package.py`） |
| Release 附件 `liaoyuyoufang-agent-config-1.0.0.zip` | 可导入的配置包：`agent.json` + 五个 `skills/*/SKILL.md` |

## 配置包在哪

> https://github.com/whxhandsome12138/My-Huawei-ICT/releases/download/data-v1.0/liaoyuyoufang-agent-config-1.0.0.zip

`agent.json` 的结构照 Nexent 官方导出格式（`name` / `version` / `model` /
`prompt{role,requirements,examples}` / `tools[]` / `skills[]` / `collaborators[]` / `memory`）。

## 为什么不是「Nexent 原生导出」的

本项目使用的 Nexent v2.5.0 这一版，前端**没有**导出入口：

- 「Agent 仓库 → 我的 Agent」卡片上的 `...` 菜单只有 `申请上架 / 评估 / 调用与分享 / 删除`；
- 配置页（`/zh/agents/<id>?from=agent-space&tab=mine`）的 `...` 里也没有导出。

官方文档（`integration-out/agents-export.html`）描述的字段结构仍然可用，所以按文档结构
从仓库单一真源重建了一份等价配置包——**提示词与技能都取自本仓库**，可逐字核对。

## 自己重建一份

```bash
python tools/build_agent_package.py          # 生成 agent/dist/聊愈有方-agent-配置包.zip
python tools/build_agent_package.py --check  # 只校验真源是否齐全
```

改了 `system-prompt.md` 或任一 `skills/*/SKILL.md` 之后重跑即可，包内文件随之更新。

## 导入到另一套 Nexent

1. **智能体配置** 页 → 导入入口 → 上传 zip（「我的 Agent」页不再提供导入入口）。
2. 系统会做**依赖预检**，五类依赖逐个确认：

| 依赖 | 会怎样 |
| :-- | :-- |
| 模型 | 需选你自己环境里可用的模型 |
| 知识库 | 跟导入者的权限走，可能为空 |
| **MCP 服务** | **不会自动带过来，必须手动加**（见 `docs/QUICKSTART.md` 第 2 步） |
| Skill | 随 ZIP 自动导入 |
| 协作 Agent | 需手动重新指定 |

3. 名称或变量名冲突时，可选「直接导入（自动加后缀）」或「LLM 重新生成名称」。

导完把 MCP 地址改成本机的，点一次工具列表左边的 ⟳ 复验，看到 5 个工具就算接好。
