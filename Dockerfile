FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY frontend/ /app/frontend/
COPY frontend/ /frontend/
EXPOSE 10000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000", "--workers", "1"]


