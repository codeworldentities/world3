FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user
RUN useradd --create-home --uid 1000 world3 && chown -R world3:world3 /app
USER world3

EXPOSE 5000

ENV PYTHONUNBUFFERED=1 \
    LLM_ENABLED=0 \
    NEO4J_ENABLED=0

CMD ["python", "main.py"]
