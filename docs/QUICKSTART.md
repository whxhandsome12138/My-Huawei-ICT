# 快速开始

三种深度，按需要选一种。全部在 Windows / Linux / macOS 上通用，差异点会单独标注。

---

## 路线 0：只想看一眼（0 分钟，不装任何东西）

双击 `demo/index.html`，或：

```bash
python -m http.server 8080 --directory demo
# 浏览器打开 http://127.0.0.1:8080
```

页面上有 6 个场景，每个场景右侧的「查看原始 JSON」是该次调用的真实返回。
**所有数字都来自 Tools 返回值，不是写死在页面里的文案。**

---

## 路线 1：只要评估能力（5 分钟）

```bash
cd mcp_server
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py --port 9100
```

另开一个终端自检：

```bash
python selfcheck.py --port 9100
# 期望输出 17/17 PASS
```

看到这两个端点就算成功：

| 传输 | 地址 | 说明 |
| :-- | :-- | :-- |
| SSE | `http://127.0.0.1:9100/sse` | 主用，兼容性最好 |
| Streamable HTTP | `http://127.0.0.1:9100/mcp` | 兜底，新版客户端优先 |

Docker 版：

```bash
docker compose -f mcp_server/compose.yml up -d --build
curl -N http://127.0.0.1:9100/sse
```

> **踩坑提醒**：`pip install mcp` 现在默认装 2.x，而 2.x 把 `FastMCP` 改名为 `MCPServer`，
> 会报 `ImportError: cannot import name 'FastMCP'`。请务必按 `requirements.txt` 装 `mcp==1.30.0`。

---

## 路线 2：跑完整智能体（30 分钟，需要 4C8G 起）

### 第 1 步：部署 Nexent

```bash
git clone https://github.com/ModelEngine-Group/nexent.git
cd nexent
bash deploy.sh docker --image-source mainland
```

- 交互式 TUI 会问组件、端口策略、镜像源；想全默认就加 `--defaults`。
- 最低 4C/8G/40G，推荐 8C/16G/100G。
- 起来后访问 `http://<IP>:3000`，默认超管 `suadmin@nexent.com` / `Nexent@123`
  （只能做权限管理，进去后要自己建租户和租户管理员）。
- 国内网络一定要用 `--image-source mainland`，否则拉镜像会卡。

### 第 2 步：把本仓库的 MCP 注册进去

Nexent 左侧 → **资源仓库 → MCP 仓库 → 我的 MCP → 添加 MCP 服务**：

| 字段 | 填什么 |
| :-- | :-- |
| 集成类型 | 远程 |
| 服务名称 | `kimore_eval`（只允许字母数字下划线连字符） |
| 服务 URL | `http://host.docker.internal:9100/sse` |
| Token / 自定义 Header | 留空（内网） |

保存后卡片应显示「**5 个工具**」。状态点显示「未连接」是正常的——SSE 是按需建会话。

> URL 怎么填，取决于 MCP 跑在哪：
> 同机 Docker → `host.docker.internal`；同机宿主 → LAN IP；
> 同一 compose 网络 → 服务名 `mcp-kimore`；**别填 `127.0.0.1`**，那是容器自己。

### 第 3 步：建智能体

新建 Agent，只勾这 5 个工具：
`assess_exercise`、`explain_deviation`、`list_samples`、`plan_session`、`query_criteria`。

把 [`agent/system-prompt.md`](../agent/system-prompt.md) 里的提示词整段贴进「模型与提示词」，
温度 0～0.2，最大步数 8～12，自验证打开。

### 第 4 步：装技能

**资源仓库 → Skill 仓库 → 上传**，依次传 `skills/dist/S1.zip` ～ `S5.zip`。
（每个 zip 里是一个 `SKILL.md` + 可选 `config/`、`scripts/`。）

### 第 5 步：发布 + 冒烟

发布后开一个新会话，问：

> 帮我看看 Es2-467acf3acb6a8191d6ef 这一条，躯干侧倾做得怎么样？

回答里应该出现 `20.901`、`37.489`、`−4.068` 这三个数。
出现过不了，按 [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) 排查。

---

## 常见问题

**Q：必须用 Nexent 吗？**
不必须。任何 MCP 客户端都能接（Claude Desktop、Cline、自研 Agent）。
Nexent 只是我们把「编排 + 技能 + 评测 + 发布」串起来的那一层。

**Q：没有 KIMORE 数据能跑吗？**
能。仓库自带 `mcp_server/fixtures/`（10 个真实工具返回样例），演示与自检都靠它。
接真实数据见 [`DATA.md`](DATA.md)。

**Q：能商用吗？**
代码 MIT，可以。但**不要当作医疗器械宣传**——它不做诊断、不评疗效，
参照分布是数据集内的相对位置，不是临床常模。详见根目录 `NOTICE`。
