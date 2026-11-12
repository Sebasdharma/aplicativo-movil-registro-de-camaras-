FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Guayaquil \
    PORT=10000 \
    USE_SUPABASE=true \
    ASISTECH_ENABLE_BG_WORKER=1 \
    MALLOC_ARENA_MAX=2 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tzdata \
        libglib2.0-0 \
        libgomp1 \
    && ln -snf /usr/share/zoneinfo/America/Guayaquil /etc/localtime \
    && echo "America/Guayaquil" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app_config.py carchito_voice.py database.py face_engine.py runtime.py server.py supabase_adapter.py ./
COPY models ./models
COPY routes ./routes
COPY templates ./templates

RUN mkdir -p /app/data /app/dataset_estudiantes \
    && chmod -R 777 /app/data /app/dataset_estudiantes

EXPOSE 10000

CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile - server:app"]
