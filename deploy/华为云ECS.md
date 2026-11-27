# 华为云 ECS 部署（手把手）

目标：一台云服务器上跑起「演示页 + MCP 评估服务」，公网可访问。
预计 20 分钟，其中 15 分钟是等开机和装 Docker。

---

## 第 1 步：买机器

控制台 → **弹性云服务器 ECS → 购买**。

| 项 | 选什么 | 为什么 |
| :-- | :-- | :-- |
| 计费模式 | 按需 / 包月 | 答辩期只有几周，按需更省 |
| 规格 | **2 vCPU / 2 GB**（s6.large.1 之类） | 只跑 MCP + Nginx 足够；MCP 是纯 Python，内存几十 MB |
| 要跑 Nexent 的话 | **4 vCPU / 8 GB**，系统盘 100 G | Nexent 官方最低 4C8G40G，再低会 OOM |
| 镜像 | **Ubuntu 22.04 64 位** | `bootstrap.sh` 在 22.04/24.04 上验过 |
| 系统盘 | 40 G 起 | 镜像 + Docker 层占几 G |
| 弹性公网 IP | **买一个，带宽按流量计费 5 Mbps** | 演示页 46 KB，流量计费最便宜 |

大赛给的是代金券，在「费用中心 → 优惠券」里确认已到账再下单。

## 第 2 步：安全组放行

ECS 详情 → 安全组 → **配置规则 → 入方向 → 添加**：

| 端口 | 协议 | 源地址 | 用途 |
| :-- | :-- | :-- | :-- |
| 22 | TCP | 你的出口 IP/32 | SSH（**别开 0.0.0.0/0**） |
| 80 | TCP | 0.0.0.0/0 | 演示页 + MCP 反代 |
| 443 | TCP | 0.0.0.0/0 | 上 HTTPS 后 |
| 9100 | TCP | 0.0.0.0/0 | 可选：Nexent 直连（不反代时才需要） |

> 只走 Nginx 反代的话，9100 不用开，安全面更小。

## 第 3 步：一条命令部署

```bash
ssh root@<公网IP>

# 国内机器建议先换 apt 源（可选）
# sed -i 's|http://archive.ubuntu.com|https://mirrors.huaweicloud.com|g' /etc/apt/sources.list

curl -fsSL https://raw.githubusercontent.com/whxhandsome12138/My-Huawei-ICT/main/deploy/bootstrap.sh -o bootstrap.sh
bash bootstrap.sh
```

脚本做四件事：装 Docker → clone 仓库到 `/opt/My-Huawei-ICT` → `docker compose up -d --build` → 跑 17 项自检并打印地址。

> **仓库是私有的话，`curl` 拉不到 raw 文件**。两种解法：
> ① 把仓库改成 public（开源要求本来也要公开）；
> ② 本地 `scp -r` 传上去：`scp -r .\My-Huawei-ICT root@<IP>:/opt/`，然后 `cd /opt/My-Huawei-ICT && bash deploy/bootstrap.sh`。

## 第 4 步：验收

```bash
curl -s http://127.0.0.1/healthz            # ok
curl -sN http://127.0.0.1/sse | head -3     # 应该立刻出 event: endpoint
```

浏览器打开 `http://<公网IP>/` —— 看到「聊愈有方」演示页就成功了。

在 Nexent 里注册 MCP：

| 字段 | 值 |
| :-- | :-- |
| 集成类型 | 远程 |
| 服务名称 | `kimore_eval` |
| 服务 URL | `http://<公网IP>/sse` |

保存后卡片应显示 5 个工具。**状态点「未连接」是正常的**，SSE 按需建连。

## 第 5 步（可选）：域名 + HTTPS

1. 域名解析 A 记录到公网 IP。
2. **中国大陆节点用 80/443 访问域名需要 ICP 备案**；没备案就先直接用 IP 访问，不影响演示。
3. 备案过了再上证书：

```bash
apt install -y certbot
docker compose -f /opt/My-Huawei-ICT/deploy/docker-compose.prod.yml stop web
certbot certonly --standalone -d your.domain.com
mkdir -p /opt/My-Huawei-ICT/deploy/certs
cp /etc/letsencrypt/live/your.domain.com/{fullchain,privkey}.pem /opt/My-Huawei-ICT/deploy/certs/
# 编辑 compose 放开 443 与证书挂载，编辑 nginx.conf 放开 ssl 段
docker compose -f /opt/My-Huawei-ICT/deploy/docker-compose.prod.yml up -d
```

## 常见问题

**Q：`docker compose` 报 command not found**
旧版是 `docker-compose`（带横杠）。`curl -fsSL https://get.docker.com | sh` 装的是新版插件，用 `docker compose`。

**Q：页面能开，但 Nexent 连 MCP 一直超时**
八成是安全组没放行 80，或者 Nginx 没关 `proxy_buffering`（SSE 会被缓冲住）。看 `docker compose logs web`。

**Q：2G 内存构建镜像时被 OOM kill**
加 swap：`fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`。

**Q：想省事，只部署演示页**
演示页是纯静态的，扔到对象存储（OBS）开静态网站托管更便宜，甚至可以直接用 GitHub Pages。
