#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}=== [KIRU OS] Despliegue Automatizado Vía Docker ===${NC}"
cd "/Users/usuario/kiru_ai"

# 1. Limpieza local de temporales de Mac
echo -e "${GREEN}1/3. Limpiando archivos temporales locales...${NC}"
rm -rf .svelte-kit build .vite *.log
find . -name ".DS_Store" -type f -delete

# 2. Construcción completa dentro de Docker (Evita el Abort trap de la Mac)
echo -e "${GREEN}2/3. Compilando y empaquetando de forma segura en Docker...${NC}"
docker build -t kiru-custom-ui .

# 3. Despliegue del contenedor
echo -e "${GREEN}3/3. Iniciando contenedor de Kiru OS en el puerto 3000...${NC}"
docker rm -f open-webui 2>/dev/null || true

docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  -e WEBUI_NAME="Kiru" \
  -e WEBUI_URL="http://localhost:3000" \
  --name open-webui \
  --restart always \
  kiru-custom-ui

echo -e "${CYAN}==============================================================${NC}"
echo -e "${GREEN}¡PROCESO FINALIZADO EXITOSAMENTE!${NC}"
echo -e "${CYAN}Entorno activo en:${NC} http://localhost:3000"
echo -e "${CYAN}==============================================================${NC}"
