FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend STUDY_MODEL_DIR=/models STUDY_DATA_DIR=/data
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 10001 study && useradd -u 10001 -g study -M study \
    && install -d -o study -g study /data /models
COPY backend/requirements-lock.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY backend/study backend/study
COPY scripts/prepare-models.py scripts/prepare-models.py
USER 10001:10001
RUN python scripts/prepare-models.py && python scripts/prepare-models.py --verify
ENV STUDY_MODELS_OFFLINE=true
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "study.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--forwarded-allow-ips", "*"]
