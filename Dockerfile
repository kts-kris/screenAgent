FROM alpine:latest
LABEL "language"="binary"

WORKDIR /app

ENV PORT=3188

RUN apk add --no-cache wget ca-certificates

# 下载二进制文件，添加重试机制
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
      BINARY="cursor-api-x86_64-linux"; \
    elif [ "$ARCH" = "aarch64" ]; then \
      BINARY="cursor-api-aarch64-linux"; \
    else \
      BINARY="cursor-api-x86_64-linux"; \
    fi && \
    echo "Downloading $BINARY..." && \
    wget --timeout=30 -O /app/cursor-api "https://github.com/wisdgod/cursor-api/releases/download/v0.4.0-pre.19/$BINARY" && \
    chmod +x /app/cursor-api && \
    echo "Binary downloaded successfully"

# 下载配置文件
RUN echo "Downloading .env..." && \
    wget --timeout=30 -O /app/.env "https://raw.githubusercontent.com/kts-kris/screenAgent/main/.env" && \
    echo ".env downloaded successfully"

# 下载前端资源
RUN echo "Downloading frontend.zip..." && \
    wget --timeout=30 -O /app/frontend.zip "https://github.com/wisdgod/cursor-api/releases/download/v0.4.0-pre.16/frontend.zip" && \
    echo "frontend.zip downloaded successfully"

EXPOSE 3188

CMD ["/app/cursor-api"]
