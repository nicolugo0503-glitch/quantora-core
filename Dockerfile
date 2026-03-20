FROM python:3.11-slim
WORKDIR /app
COPY backend /app/backend
COPY frontend /app/frontend
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
EXPOSE 8080
CMD sh -c "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
