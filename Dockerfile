FROM node:22-bookworm-slim AS node
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PAWSEC_DATA_DIR=/data PAWSEC_BIND=0.0.0.0 PORT=8765
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 fonts-noto-cjk tzdata && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=node /build/node_modules ./node_modules
COPY . .
RUN useradd --uid 10001 --create-home pawsec && mkdir /data && chown pawsec:pawsec /data
USER pawsec
EXPOSE 8765
STOPSIGNAL SIGTERM
CMD ["python", "server.py"]
