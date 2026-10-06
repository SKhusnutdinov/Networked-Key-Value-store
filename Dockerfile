FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install .

CMD ["python", "-m", "kvstore.server", "--host", "0.0.0.0", "--port", "6379", "--data-dir", "/data"]
