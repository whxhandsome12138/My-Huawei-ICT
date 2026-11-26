# 腰衡 MCP 服务（回放/契约实现）
# 构建：docker build -t yaoheng/mcp-kimore:0.1.0 .
# 运行：docker run -p 9100:9100 yaoheng/mcp-kimore:0.1.0
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py selfcheck.py ./
COPY fixtures ./fixtures

# 非 root 运行
RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 9100

# 必须监听 0.0.0.0，否则容器外访问不到
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import socket,sys; s=socket.socket(); s.settimeout(3); sys.exit(0 if s.connect_ex(('127.0.0.1',9100))==0 else 1)"

CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "9100"]
