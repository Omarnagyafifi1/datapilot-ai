# Stage 1: Build React Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build FastAPI Backend & Run App
FROM python:3.10-slim AS backend-runner

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy python dependencies list and install packages
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend files
COPY backend/ ./backend

# Copy frontend static build files (matches Path(__file__).resolve().parents[2] / "frontend" / "dist")
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose port and start backend
EXPOSE 8000

ENV PYTHONIOENCODING=utf-8
WORKDIR /app/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
