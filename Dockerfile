# syntax=docker/dockerfile:1

# ------------------------------------------------------------------------------
# Stage 1: Build wheels on Python 3.12 Alpine
# ------------------------------------------------------------------------------
FROM python:3.12-alpine AS builder

WORKDIR /build

# Copy project specification and source code
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Build wheel package and download all pre-compiled musllinux dependencies
RUN pip install --no-cache-dir -U pip wheel \
    && pip wheel --no-cache-dir --wheel-dir=/build/wheels .

# ------------------------------------------------------------------------------
# Stage 2: Ultra-lightweight production runtime image
# ------------------------------------------------------------------------------
FROM python:3.12-alpine AS runner

ENV TZ=Asia/Kolkata \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

# Install tzdata for timezone accuracy and su-exec for step-down privileges
RUN apk add --no-cache tzdata su-exec

WORKDIR /app

# Install wheels from builder stage
COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/* \
    && rm -rf /tmp/wheels

# Create non-root user and persistent data directory
RUN addgroup -g 1000 -S appgroup && adduser -u 1000 -S appuser -G appgroup \
    && mkdir -p /app/data && chown -R appuser:appgroup /app/data

# Copy runtime entrypoint script to handle volume permissions and drop privileges
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["whisper-bot"]

