# Imagen base oficial de Python con soporte para librerías científicas
FROM python:3.11-slim

# Instalar dependencias de sistema para OpenCV y procesamiento de medios
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    espeak \
    alsa-utils \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requerimientos e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del backend
COPY . .

# Exponer el puerto del servidor API y Dashboard
EXPOSE 5000

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Comando para ejecutar el servidor BúhoPass
CMD ["python", "server.py"]
