# 离线回放 MCP（replay_mcp）

## 这是什么

一个与 B 的 `exercise-assessment-kimore` **接口完全一致**的 MCP 服务，数据来自 B 交付包里的 9 个真实响应 JSON（`contracts/examples/`），而不是真实计算。

存在的理由只有一个：**把「等网络通」变成「改一个 endpoint」。**

- 下午就能把 Agent、Skill、提示词、失败话术全部调通；
- 晚上联调时只改 URL，其余不动；
- 万一晚上网络不通，演示照常进行，且文档里可以写「离线回放 + 在线联调双通道」——这不是退路，是工程上正确的做法。

## 快速开始

```powershell
# 1) 启动（默认 9100，避开 VM 里被旧方向 course-audit 占用的 8001）
cd F:\deepseek-harness\华为ICT\deliver\replay_mcp
python server.py --port 9100

# 2) 自测（17 项断言，含 5 类失败路径）
python selfcheck.py --port 9100
```

端点：

- SSE：`http://0.0.0.0:9100/sse`
- Streamable HTTP：`http://0.0.0.0:9100/mcp`

`--fixtures` 可指向任意 examples 目录，默认指向
`..\handoff\kimore_mcp_handoff_2026-11-24\contracts\examples`。

## 五个工具与路由

| 工具 | 路由规则 |
| :-- | :-- |
| `list_samples` | 返回 5 条清单，`total_available=77`，与真实响应一致 |
| `assess_exercise` | `Es2-467acf3acb6a8191d6ef` → 真实 17 特征；`Es2-fbab3ba3e46a4ea94233` → partial（10 特征）；`mode=baseline_prediction` → `MODEL_UNAVAILABLE` |
| `explain_deviation` | 返回 `data.evidence`（3 条）+ `data.not_evidence_of`（3 条），支持 `feature_id` 过滤 |
| `query_criteria` | 仅 Es2；Es1/Es3–Es9 → `UNSUPPORTED_EXERCISE` |
| `plan_session` | 1–5 个 ID，重复 → `INVALID_ARGUMENT` |

ID 校验：`^Es[1-5]-[0-9a-f]{20}$`，不匹配 → `INVALID_ARGUMENT`；合法但不认识 → `SAMPLE_NOT_FOUND`（`retryable=false`）。

## coverage 语义（重要）

每个响应都带 `provenance.replay`：

```json
{
  "mode": "offline_fixture",
  "fixture": "real_assess_success.json",
  "coverage": "exact",
  "note": "..."
}
```

| coverage | 含义 | 使用方式 |
| :-- | :-- | :-- |
| `exact` | 与 B 真实响应逐字节同源 | 可以直接演示 |
| `derived` | 由真实响应裁剪/过滤得到 | 可以演示，需说明 |
| `absent` | fixture 里没有，返回空壳 | 只能演示「无数据」路径 |
| `synthetic` | 编的 | **禁止作为证据引用** |

非 `exact` 会自动追加一条 `warnings`，防止这些数字被当成真实结果写进文档。这条约束是给未来的自己留的。

## 与 B 真服务的差异

| 维度 | 回放服务 | B 的真服务 |
| :-- | :-- | :-- |
| 数据来源 | 9 个 JSON fixture | 真实 Kinect 记录重算 |
| 覆盖样本 | 2 个真实 ID + 5 个空壳 | 77 条清单 |
| 延迟 | < 5 ms | 14–18 ms |
| 协议版本 | 2025-11-25（SDK 声明） | 2025-11-25 |
| 用途 | 打通链路、演示兜底 | 答辩主证据 |

## 今晚 20:00 切换清单

1. 19:30 冷启动 VM（`vmrun start`，**不要点「挂起」恢复**），等 `:3000` 起来。
2. 19:45 在 VM 里 `curl -m 5 http://<B的IP>:8001/sse`。
3. 通 → 把 Agent 的 MCP 地址从 `http://192.168.138.1:9100/sse` 改成 `http://<B的IP>:8001/sse`，重跑 `python selfcheck.py --port 8001`。
4. 不通 → 保持 9100 不动，先按回放跑完全流程，把网络问题单独记录。
5. 无论哪条路，都用 `selfcheck.py` 的输出作为联调记录（它会写 `reports/replay_selfcheck.md`）。

## 已知限制

- 只实现 Es2；`query_criteria` 对其他动作返回 `UNSUPPORTED_EXERCISE`（与 B 一致）。
- `partial` 空壳样本只有 `status` 与 `error`，没有特征值——这是有意的，避免假数据。
- 不实现 SSE 保活帧的时间语义（真实服务约 15 秒一次），长时间挂着可能需要重连。
