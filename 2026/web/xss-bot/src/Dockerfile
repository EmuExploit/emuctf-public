FROM node:22.23.4-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        fonts-liberation \
        ca-certificates \
        dumb-init \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_DOWNLOAD=true \
    CHROMIUM_PATH=/usr/bin/chromium \
    NODE_ENV=production

COPY ./flag.txt /flag.txt

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --omit=dev && npm cache clean --force

COPY index.js ./
COPY public ./public

RUN chown -R node:node /app
USER node

ENV HOME=/tmp

EXPOSE 8080

ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "index.js"]
