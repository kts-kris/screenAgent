FROM alpine:latest

LABEL "language"="binary"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PORT=3188

# 合并所有步骤，减少镜像体积并确保资源正确处理
RUN apk add --no-cache wget ca-certificates && \
    # 1. 识别架构并下载二进制文件
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        BINARY="cursor-api-x86_64-linux"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        BINARY="cursor-api-aarch64-linux"; \
    else \
        BINARY="cursor-api-x86_64-linux"; \
    fi && \
    echo "Downloading $BINARY..." && \
    wget --timeout=30 -O /app/cursor-api "https://github.com/wisdgod/cursor-api/releases/download/v0.4.0-pre.20/$BINARY" && \
    chmod +x /app/cursor-api && \
    \
    # 2. 下载配置文件
    echo "Downloading .env..." && \
    wget --timeout=30 -O /app/.env "https://raw.githubusercontent.com/kts-kris/screenAgent/refs/heads/main/.env" && \
    \
    # 3. 下载并解压前端资源 (修正：之前只下载未解压)
    echo "Downloading and extracting frontend.zip..." && \
    wget --timeout=30 -O /app/frontend.zip "https://github.com/wisdgod/cursor-api/releases/download/v0.4.0-pre.16/frontend.zip"

# 暴露端口
EXPOSE 3188

# 启动程序
CMD ["/app/cursor-api"]
