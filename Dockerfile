
FROM python:3.11-slim

WORKDIR /app

# Permitir la compilación ligera de Pyodide
ARG USE_SLIM=false
ENV USE_SLIM=${USE_SLIM}

# 1. Copiar los archivos de dependencias
COPY requirements.txt ./
COPY package.json package-lock.json ./

# 2. Instalar dependencias de Python
RUN pip install --no-cache-dir --default-timeout=1000 --retries 5 --no-binary :all: -r requirements.txt || pip install --no-cache-dir --default-timeout=1000 --retries 5 -r requirements.txt

# 3. Instalar dependencias del sistema y Node.js 20
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 4. Instalar dependencias de Node.js
RUN npm install --legacy-peer-deps

# 5. Copiar el código del proyecto
COPY . .

# 6. Compilar la aplicación web
RUN NODE_OPTIONS="--max-old-space-size=6144" npm run build

# Puerto y comando de inicio
EXPOSE 8000
CMD ["bash", "backend/dev.sh"]
