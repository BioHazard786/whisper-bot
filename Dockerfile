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

# Install tzdata for timezone accuracy
RUN apk add --no-cache tzdata

WORKDIR /app

# Install wheels from builder stage
COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/* \
    && rm -rf /tmp/wheels

# Create non-root user for security best practices
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

USER appuser

# Run Psst! Whisper Bot via installed console script or module
ENTRYPOINT ["whisper-bot"]
