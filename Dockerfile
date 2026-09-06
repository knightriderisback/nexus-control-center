# NEXUS AI Engineering OS // Container Specification
# Optimized for Google Cloud Run ($PORT dynamic binding, non-root user, lightweight footprint)

FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ /app/backend/
COPY data/ /app/data/

# Copy pre-compiled React Cyber-HUD static distribution
COPY frontend/dist/ /app/frontend/dist/

# Create non-root user for security
RUN useradd -m -u 1000 nexususer && \
    chown -R nexususer:nexususer /app
USER nexususer

# Cloud Run dynamic port contract
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Launch uvicorn engine
CMD ["sh", "-c", "exec uvicorn backend.server:app --host 0.0.0.0 --port ${PORT}"]
