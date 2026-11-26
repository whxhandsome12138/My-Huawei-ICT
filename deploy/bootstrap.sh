#!/usr/bin/env bash
# 一台全新的 Ubuntu（22.04 / 24.04）上，一条命令把「评估服务 + 演示站」跑起来。
#
#   curl -fsSL https://raw.githubusercontent.com/<org>/My-Huawei-ICT/main/deploy/bootstrap.sh | bash
# 或本地已 clone：
#   bash deploy/bootstrap.sh
#
# 做完会打印公网访问地址。重复执行是幂等的（已装就跳过，已起就重建）。
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/whxhandsome12138/My-Huawei-ICT.git}"
APP_DIR="${APP_DIR:-/opt/My-Huawei-ICT}"
PORT_HTTP="${PORT_HTTP:-80}"

log() { printf '\033[1;36m[bootstrap]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[bootstrap] %s\033[0m\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "请用 root 或 sudo 执行"

# ---------- 1. 基础环境 ----------
if ! command -v docker >/dev/null 2>&1; then
  log "安装 Docker（官方脚本，国内可加镜像源）"
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl git
  curl -fsSL https://get.docker.com | sh
else
  log "Docker 已存在：$(docker --version)"
fi
systemctl enable --now docker >/dev/null 2>&1 || true

# ---------- 2. 拉代码 ----------
if [[ -d "$APP_DIR/.git" ]]; then
  log "更新已有代码：$APP_DIR"
  git -C "$APP_DIR" fetch --depth 1 origin main
  git -C "$APP_DIR" reset --hard origin/main
else
  log "克隆到 $APP_DIR"
  git clone --depth 1 "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR/deploy"

# ---------- 3. 起服务 ----------
log "构建并启动（首次约 1–3 分钟）"
docker compose -f docker-compose.prod.yml up -d --build

# ---------- 4. 自检 ----------
log "等待 MCP 就绪"
for i in $(seq 1 40); do
  if curl -fsS -m 3 "http://127.0.0.1:${PORT_HTTP}/healthz" >/dev/null 2>&1; then break; fi
  sleep 2
done

log "容器内自检 17 项"
docker compose -f docker-compose.prod.yml exec -T mcp python selfcheck.py --port 9100 | tail -n 3 || \
  log "自检未全绿，看日志：docker compose -f docker-compose.prod.yml logs -f mcp"

# ---------- 5. 打印地址 ----------
IP="$(curl -fsS -m 5 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"
cat <<EOF

==================== 部署完成 ====================
演示页      http://${IP}/
健康检查    http://${IP}/healthz
MCP (SSE)   http://${IP}/sse
MCP (HTTP)  http://${IP}/mcp
直连        http://${IP}:9100/sse   （需安全组放行 9100）

在 Nexent 里注册 MCP 时填：
  集成类型  远程
  服务名称  kimore_eval
  服务 URL  http://${IP}/sse

别忘了在云控制台安全组放行 ${PORT_HTTP}（和 9100，如果你想直连）。
==================================================
EOF
