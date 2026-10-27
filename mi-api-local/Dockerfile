FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema esenciales para compilar paquetes de Python si lo requieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python con alta tolerancia a la red
COPY requirements.txt ./
RUN pip install --no-cache-dir --default-timeout=1000 --retries 5 -r requirements.txt

# Copiar el resto del código fuente
COPY . .

# Exponer el puerto de la API y comando de arranque
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]