FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema, curl y Node.js 20 para compilar el frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de configuración de dependencias
COPY package.json package-lock.json ./
COPY requirements.txt ./

# Instalar dependencias de Python y Node.js
RUN pip install --no-cache-dir -r requirements.txt
RUN npm install --legacy-peer-deps

# Copiar el resto del código del proyecto
COPY . .

# Compilar la aplicación web
RUN NODE_OPTIONS="--max-old-space-size=4096" npm run build

# Exponer el puerto y definir comando de inicio
EXPOSE 8000
CMD ["bash", "backend/dev.sh"]