FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY chokepoint ./chokepoint
EXPOSE 8000
# single worker by design: the per-graph cf lock is in-process (ENG-6)
CMD ["sh", "-c", "uvicorn chokepoint.web:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
