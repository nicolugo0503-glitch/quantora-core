FROM python:3.11

WORKDIR /app

COPY backend /app/backend

RUN pip install --no-cache-dir -r backend/requirements.txt

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
