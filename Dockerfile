
FROM --platform=$BUILDPLATFORM node:20-bookworm-slim AS frontend-build

WORKDIR /app

ARG USE_SLIM=true
ENV USE_SLIM=${USE_SLIM}

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN NODE_OPTIONS="--max-old-space-size=4096" npm run build

FROM python:3.11-slim

WORKDIR /app

# Permitir la compilación ligera de Pyodide
ARG USE_SLIM=true
ENV USE_SLIM_DOCKER=${USE_SLIM} \
    USE_SLIM=${USE_SLIM}

# 1. Copiar los archivos de dependencias
COPY package.json package-lock.json ./
COPY backend/requirements.txt ./backend-requirements-full.txt
COPY backend/requirements-slim.txt ./backend-requirements-slim.txt
COPY --from=frontend-build /app/build ./build

# 2. Instalar dependencias de Python
RUN python -m pip install --upgrade pip && \
    if [ "$USE_SLIM" = "true" ]; then \
        python -m pip install --no-cache-dir --default-timeout=1000 --retries 5 -r backend-requirements-slim.txt; \
    else \
        python -m pip install --no-cache-dir --default-timeout=1000 --retries 5 -r backend-requirements-full.txt; \
    fi

# 3. Copiar el código del proyecto
COPY . .

# Puerto y comando de inicio
EXPOSE 8080
CMD ["bash", "backend/start.sh"]
