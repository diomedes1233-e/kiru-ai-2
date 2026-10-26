# --- Etapa de Compilación Segura en Docker ---
FROM node:20-alpine AS builder
WORKDIR /app

# Limitar el heap de Node para dejar memoria al sistema y al resto del proceso
ENV NODE_OPTIONS="--max-old-space-size=2560"

COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . .
RUN npm run build

# --- Etapa de Producción Final ---
FROM ghcr.io/open-webui/open-webui:main
WORKDIR /app
COPY --from=builder /app/build /app/build
EXPOSE 8080
CMD ["bash", "start.sh"]
