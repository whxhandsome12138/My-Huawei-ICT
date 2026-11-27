# 聊愈有方 · KIMORE 动作评估智能体（开源版）

> **聊愈有方**（谐音「疗愈有方」）——
> **聊**：对话式智能体，语音引导、结果解释、随访对话；
> **愈**：愈合进展追踪；
> **有方**：干预有方法。
>
> 把 KIMORE 数据集里五个临床动作，做成**可调用、可溯源、可版本化**的评估工具；
> 让 Nexent 上的智能体在「选动作 → 评动作 → 解释 → 调方案 → 吸收治疗师修正」的闭环里越用越准。
>
> ⚠️ 本项目是**科研与竞赛原型**，不构成医疗器械，不做诊断、不评估疗效、不开处方。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2025--11--25-blue)](https://modelcontextprotocol.io)
[![Nexent](https://img.shields.io/badge/Nexent-v2.5.0-green)](https://github.com/ModelEngine-Group/nexent)

---

## 这是什么

一句话：**给「AI 读得懂动作」配一张能核对的底稿。**

腰痛患者的居家康复动作（如躯干侧倾、单腿站立）做得对不对，传统上靠治疗师看视频打分（EAAQ 量表）。我们把这件事拆成三段可验证的链路：

```
骨架序列 → 17 项运动学特征 → 与 71 人参照分布的偏离 → 结论 + 证据 + 边界
```

其中每一段都能回溯到具体出处：

| 段 | 产物 | 凭什么可信 |
| :-- | :-- | :-- |
| 特征 | 17 个特征（倾角、范围、峰值、重复次数…） | 逐条对应 KIMORE 作者 MATLAB 脚本的行号，见 [`docs/FEATURE_PROVENANCE.md`](docs/FEATURE_PROVENANCE.md) |
| 偏离 | 分位数对照（median / p25 / p75） | 参照分布来自同数据集的**其他 71 名受试者**，不是临床常模 |
| 结论 | 五段式输出 + 置信度 | 由本体（OWL + SHACL）约束「什么特征能下什么结论」 |

---

## 四个部分

| 目录 | 是什么 | 给谁用 |
| :-- | :-- | :-- |
| [`mcp_server/`](mcp_server/) | MCP 服务，5 个工具：`list_samples` / `assess_exercise` / `explain_deviation` / `query_criteria` / `plan_session` | 想让任何一个 MCP 客户端（Nexent、Claude、自研 Agent）接进来的人 |
| [`ontology/`](ontology/) | 本体 `ontology.ttl` + 特征实例 + SHACL 约束，管「不许说什么」 | 关心可解释性与合规的人 |
| [`skills/`](skills/) | 5 个 Nexent 技能（S1–S5），管「应该怎么说」 | 用 Nexent 搭智能体的人 |
| [`demo/`](demo/) | 单文件演示页，双击即开，把一次完整调用链摆出来 | 什么都不想装、只想看一眼的人 |

---

## 三种用起来的方式

### 1. 什么都不装：看演示页

双击 `demo/index.html`。里面有 6 个场景（主路径、历史评分、两条记录对比、三种错误），
每个数值都能点开「查看原始 JSON」核对——**这不是视频，是真实工具返回值的内嵌回放**。

### 2. 只要评估能力：起 MCP 服务

```bash
cd mcp_server
pip install -r requirements.txt
python server.py --port 9100
# SSE: http://127.0.0.1:9100/sse     Streamable HTTP: http://127.0.0.1:9100/mcp
python selfcheck.py --port 9100      # 17 项自检，应全 PASS
```

或 Docker：

```bash
docker compose -f mcp_server/compose.yml up -d --build
```

### 3. 要完整智能体：Nexent + 本仓库

```bash
# ① 先按官方文档部署 Nexent（约 30 分钟，4C8G 起）
git clone https://github.com/ModelEngine-Group/nexent.git
cd nexent && bash deploy.sh docker --image-source mainland

# ② 在 Nexent 里注册 MCP：资源仓库 → MCP 仓库 → 添加 → 远程
#    名称 kimore_eval   URL http://<你的IP>:9100/sse

# ③ 导入智能体：Agent 仓库 → 导入 → 选 agent/liaoyuyoufang-agent.zip
# ④ 上传技能：skills/dist/S1.zip ... S5.zip
```

详细步骤见 [`docs/QUICKSTART.md`](docs/QUICKSTART.md)。

---

## 数据从哪来（重要）

本仓库**不包含** KIMORE 原始数据。原因有两条：数据集体量（186 MB / 1983 文件）不适合进 Git；
它的使用条款也不允许我们二次分发。

请自行前往论文作者提供的渠道下载，并遵守其条款：

> Capecci M, Ceravolo M G, Ferracuti F, et al. **The KIMORE dataset: KInematic assessment of
> MOvements and clinical scores for telerehabilitation of low back pain.** *IEEE Transactions on
> Neural Systems and Rehabilitation Engineering*, 2019, 27(7): 1436–1448.

拿到数据后按 [`docs/DATA.md`](docs/DATA.md) 摆放目录，`mcp_server` 会自动索引。
仓库里带的 `mcp_server/fixtures/` 是**脱敏后的工具返回值**，用于离线演示与自检，不是原始骨架。

---

## 部署到云上（一台机器搞定）

只想要「演示页 + 评估服务」公网可访问，2C2G 就够：

```bash
# 全新的 Ubuntu 22.04/24.04 上，一条命令
curl -fsSL https://raw.githubusercontent.com/<org>/My-Huawei-ICT/main/deploy/bootstrap.sh | bash
```

或者本地已 clone：

```bash
bash deploy/bootstrap.sh
```

脚本会装 Docker、拉代码、起 compose、跑 17 项自检，最后打印访问地址。
详细说明（安全组、HTTPS、SSE 反代为什么必须关缓冲）见 [`deploy/README.md`](deploy/README.md)。

演示页也可以挂 GitHub Pages（`.github/workflows/pages.yml` 已就绪），
评委点个链接就能看，不用任何环境。

---

## 我们刻意没做的事

写在前面，省得误会：

- **不做实时视频姿态估计**。MediaPipe / MMPose 已经把这件事做到工业级，我们用它当输入，不当卖点。
- **不预测临床评分**。数据集只公开了三层汇总分（cTS/cPO/cCF），没有 EAAQ 的 10 个分项；
  拿汇总分去训一个「预测分数」的模型，看起来漂亮但没有解释力，我们没做。
- **不宣称疗效**。参照分布是「同一数据集里其他人」的相对位置，不是临床常模。

---

## 引用

```bibtex
@misc{liaoyuyoufang2026,
  title  = {聊愈有方: 面向腰痛居家康复的可进化动作评估与随访决策智能体},
  author = {Tongji University Liaoyu Youfang Team},
  year   = {2026},
  note   = {Built on Nexent (MIT, Huawei Technologies Co., Ltd.) and the KIMORE dataset}
}
```

## 许可证

本仓库代码以 [MIT](LICENSE) 发布。第三方组件与数据集的授权见 [NOTICE](NOTICE)。
