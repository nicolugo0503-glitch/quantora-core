FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY backend /app/backend
COPY frontend /app/frontend
COPY start.sh /app/start.sh
RUN pip install --no-cache-dir -r /app/backend/requirements.txt && chmod +x /app/start.sh
EXPOSE 8010
CMD ["/app/start.sh"]
