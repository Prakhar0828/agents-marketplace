# ─── Stage 1: Build the Vite frontend ────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ─── Stage 2: Python runtime ─────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# System deps for python-docx (lxml) and general sanity.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache).
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code.
COPY backend/ /app/backend/

# Copy the built frontend from stage 1.
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Copy repo-root files the backend references (config.py does REPO_ROOT = parents[2]).
COPY .env.example /app/.env.example
COPY requirements.txt /app/requirements.txt

# Ensure runtime directories exist (ephemeral — fine for session-scoped data).
RUN mkdir -p /app/backend/uploads /app/backend/downloads

# Fly injects PORT; default to 8080.
ENV PORT=8080
EXPOSE 8080

# Start FastAPI. The app mounts frontend/dist/ at / automatically.
CMD cd /app/backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --ws websockets
