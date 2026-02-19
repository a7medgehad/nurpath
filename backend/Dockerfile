FROM python:3.11-slim
WORKDIR /app

COPY backend/pyproject.toml /app/pyproject.toml
COPY backend/app /app/app
COPY data /app/data

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
