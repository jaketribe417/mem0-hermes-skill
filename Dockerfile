FROM python:3.12-slim
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG MEM0_COMMIT=366945965df43aa7084be98d1b5073b62a20b431
RUN curl -sL "https://github.com/mem0ai/mem0/archive/${MEM0_COMMIT}.tar.gz" | tar xz \
    && mv mem0-${MEM0_COMMIT}/server/* . \
    && rm -rf mem0-${MEM0_COMMIT}

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["/entrypoint.sh"]
