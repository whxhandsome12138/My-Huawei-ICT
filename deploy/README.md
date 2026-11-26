# 云上部署：一台机器起「评估服务 + 演示站」

这个 compose 只跑**两件事**：MCP 评估服务、Nginx（静态演示页 + 反代 SSE）。
Nexent 本身不在这里——它按官方 `deploy.sh` 装（见 `docs/QUICKSTART.md` 路线 2），
装好后把 MCP 地址填成 `http://<这台机器>:9100/sse` 或 `http://mcp:9100/sse`。

```bash
cd deploy
docker compose -f docker-compose.prod.yml up -d --build
```

起来后：

| 地址 | 是什么 |
| :-- | :-- |
| `http://<公网IP>/` | 演示页（静态，46 KB，无依赖） |
| `http://<公网IP>/sse` | MCP 的 SSE 端点（Nginx 反代到容器 9100） |
| `http://<公网IP>/mcp` | Streamable HTTP 兜底 |
| `http://<公网IP>:9100/sse` | 直连容器（安全组放行了才通） |

## 为什么要 Nginx 反代

1. **演示页和 MCP 同一个域名**，评委点一个链接就够；
2. 后面挂 HTTPS 只改一处；
3. 9100 可以不对外开放，只暴露 80/443。

## SSE 的三个必备设置（少一个就会「连上就断」）

```nginx
proxy_http_version 1.1;
proxy_set_header Connection '';
proxy_buffering off;          # 关键：不关会把事件攒在缓冲区，客户端永远收不到
proxy_read_timeout 3600s;     # 长连接，默认 60s 会被掐
proxy_cache off;
```

另外 `/messages/` 也必须反代——SSE 建连后客户端要往这个路径 POST。

## 上 HTTPS

有域名就两条命令：

```bash
apt install -y certbot
certbot certonly --standalone -d your.domain.com    # 先把 80 端口让出来：docker compose stop web
# 证书在 /etc/letsencrypt/live/your.domain.com/
```

把证书软链或复制到 `deploy/certs/fullchain.pem`、`deploy/certs/privkey.pem`，
取消 `docker-compose.prod.yml` 里 443 那段注释，`docker compose up -d` 即可。

## 资源与成本

| 跑什么 | 最低配置 | 说明 |
| :-- | :-- | :-- |
| 只跑本 compose（MCP + 演示页） | **2C 2G / 40G** | 够用，MCP 是纯 Python，内存几十 MB |
| 再加 Nexent 全套 | **4C 8G / 100G** | Nexent 官方最低 4C8G40G，推荐 8C16G；加 4G swap 更稳 |

大赛给的是华为云代金券，买 ECS 时选 **Ubuntu 22.04 / 24.04**，系统盘 40G 起。
