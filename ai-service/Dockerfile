FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ai-service/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY ai-service/app ./app

COPY ml ./ml

ENV PYTHONPATH="/app:${PYTHONPATH}"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]